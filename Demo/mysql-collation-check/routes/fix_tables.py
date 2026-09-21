import pymysql
from flask import Blueprint, jsonify, request

from config import MAX_ROWS_THRESHOLD, TARGET_CHARSET, TARGET_COLLATION
from database import get_connection
from services.collation import annotate_table, fetch_column_issues
from storage import history


blueprint = Blueprint('table_fixes', __name__, url_prefix='/api')


@blueprint.post('/fix_table_collation')
def fix_table_collation():
    data = request.json
    database = data.get('database')
    table = data.get('table')
    if not database or not table:
        return jsonify({'success': False, 'error': '缺少参数'})

    try:
        connection = get_connection(database)
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                f'ALTER TABLE `{table}` CONVERT TO CHARACTER SET '
                f'{TARGET_CHARSET} COLLATE {TARGET_COLLATION}'
            )
        connection.close()
        return jsonify({
            'success': True,
            'message': f'表 {table} 排序规则已修改为 {TARGET_COLLATION}'
        })
    except Exception as error:
        return jsonify({'success': False, 'error': str(error)})


@blueprint.post('/fix_all_tables')
def fix_all_tables():
    data = request.json
    database = data.get('database')
    threshold = data.get('threshold', MAX_ROWS_THRESHOLD)
    if not database:
        return jsonify({'success': False, 'error': '缺少参数'})

    connection = get_connection(database)
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    results = []
    skipped = []
    tables = []
    try:
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_COLLATION
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        """, (database,))
        tables = cursor.fetchall()
        issues = fetch_column_issues(cursor, database)
        need_fix = [
            table for table in tables
            if annotate_table(table, issues)['need_fix']
        ]

        if not need_fix:
            return jsonify({
                'success': True,
                'message': '所有表已符合要求',
                'fixed': [],
                'skipped': [],
                'total': len(tables)
            })

        for table in need_fix:
            name = table['TABLE_NAME']
            try:
                cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{name}`")
                row_count = cursor.fetchone()['cnt']
            except Exception:
                row_count = 0

            if row_count > threshold:
                skipped.append({'name': name, 'row_count': row_count})
                continue

            sql = (
                f'ALTER TABLE `{name}` CONVERT TO CHARACTER SET '
                f'{TARGET_CHARSET} COLLATE {TARGET_COLLATION}'
            )
            try:
                cursor.execute(sql)
                results.append({
                    'table': name,
                    'success': True,
                    'row_count': row_count
                })
            except Exception as error:
                results.append({
                    'table': name,
                    'success': False,
                    'error': str(error),
                    'row_count': row_count
                })
    except Exception as error:
        return jsonify({'success': False, 'error': str(error)})
    finally:
        cursor.close()
        connection.close()

    fixed = [result for result in results if result['success']]
    failed = [result for result in results if not result['success']]
    message = f'成功修复 {len(fixed)} 张表'
    if skipped:
        message += f'，跳过 {len(skipped)} 张（超阈值）'
    if failed:
        message += f'，失败 {len(failed)} 张'

    history.add(database, results, skipped, len(tables))
    return jsonify({
        'success': not failed and not skipped,
        'message': message,
        'fixed': fixed,
        'failed': failed,
        'skipped': skipped,
        'total': len(tables),
        'threshold': threshold
    })
