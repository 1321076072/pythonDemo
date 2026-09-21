import pymysql
from flask import Blueprint, current_app, jsonify, request

from config import MAX_ROWS_THRESHOLD, TARGET_COLLATION
from database import get_connection
from services.collation import build_column_definition, column_needs_fix


blueprint = Blueprint('column_fixes', __name__, url_prefix='/api')

COLUMN_METADATA_SQL = """
    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
           EXTRA, COLUMN_COMMENT, CHARACTER_SET_NAME, COLLATION_NAME
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
    ORDER BY ORDINAL_POSITION
"""


def _row_count(cursor, table):
    try:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
        return cursor.fetchone()['cnt']
    except Exception:
        current_app.logger.exception('统计表行数失败：table=%s', table)
        return 0


def _columns(cursor, database, table):
    try:
        cursor.execute(COLUMN_METADATA_SQL, (database, table))
        return cursor.fetchall()
    except Exception:
        current_app.logger.exception(
            '读取字段元数据失败：database=%s table=%s',
            database,
            table
        )
        raise


def _modify_column(cursor, table, column):
    name = column['COLUMN_NAME']
    definition = build_column_definition(column)
    sql = f"ALTER TABLE `{table}` MODIFY COLUMN `{name}` {definition}"
    try:
        cursor.execute(sql)
        current_app.logger.info(
            '字段修复成功：table=%s column=%s original_charset=%s '
            'original_collation=%s',
            table,
            name,
            column['CHARACTER_SET_NAME'],
            column['COLLATION_NAME']
        )
    except Exception:
        current_app.logger.exception(
            '字段修复失败：table=%s column=%s type=%s '
            'original_charset=%s original_collation=%s sql=%s',
            table,
            name,
            column['COLUMN_TYPE'],
            column['CHARACTER_SET_NAME'],
            column['COLLATION_NAME'],
            sql
        )
        raise


@blueprint.post('/fix_column_collation')
def fix_column_collation():
    data = request.json
    database = data.get('database')
    table = data.get('table')
    column_name = data.get('column')
    if not all([database, table, column_name]):
        return jsonify({'success': False, 'error': '缺少参数'})

    current_app.logger.info(
        '开始修复单个字段：database=%s table=%s column=%s',
        database,
        table,
        column_name
    )
    try:
        connection = get_connection(database)
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
                       EXTRA, COLUMN_COMMENT, CHARACTER_SET_NAME, COLLATION_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
            """, (database, table, column_name))
            column = cursor.fetchone()
            if not column:
                connection.close()
                return jsonify({
                    'success': False,
                    'error': f'列 {column_name} 不存在'
                })
            _modify_column(cursor, table, column)
        connection.close()
        return jsonify({
            'success': True,
            'message': f'列 {column_name} 排序规则已修改为 {TARGET_COLLATION}'
        })
    except Exception as error:
        current_app.logger.exception(
            '单字段修复请求失败：database=%s table=%s column=%s',
            database,
            table,
            column_name
        )
        return jsonify({'success': False, 'error': str(error)})


@blueprint.post('/fix_all_columns')
def fix_all_columns():
    data = request.json
    database = data.get('database')
    table = data.get('table')
    threshold = data.get('threshold', MAX_ROWS_THRESHOLD)
    if not all([database, table]):
        return jsonify({'success': False, 'error': '缺少参数'})

    connection = get_connection(database)
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    results = []
    columns = []
    current_app.logger.info(
        '开始修复表字段：database=%s table=%s threshold=%s',
        database,
        table,
        threshold
    )
    try:
        row_count = _row_count(cursor, table)
        if row_count > threshold:
            return jsonify({
                'success': True,
                'message': f'跳过：表 {table} 行数 {row_count:,} 超过阈值 {threshold:,}',
                'fixed': [],
                'skipped': [{'name': table, 'row_count': row_count}],
                'failed': [],
                'total_columns': 0
            })

        columns = _columns(cursor, database, table)
        need_fix = [column for column in columns if column_needs_fix(column)]
        current_app.logger.info(
            '字段扫描完成：database=%s table=%s total=%s need_fix=%s',
            database,
            table,
            len(columns),
            len(need_fix)
        )
        if not need_fix:
            return jsonify({
                'success': True,
                'message': f'表 {table} 所有字段已符合要求',
                'fixed': [],
                'skipped': [],
                'failed': [],
                'total_columns': len(columns)
            })

        for column in need_fix:
            name = column['COLUMN_NAME']
            try:
                _modify_column(cursor, table, column)
                results.append({'column': name, 'success': True})
            except Exception as error:
                results.append({
                    'column': name,
                    'success': False,
                    'error': str(error)
                })
    except Exception as error:
        current_app.logger.exception(
            '整表字段修复请求失败：database=%s table=%s',
            database,
            table
        )
        return jsonify({'success': False, 'error': str(error)})
    finally:
        cursor.close()
        connection.close()

    fixed = [result for result in results if result['success']]
    failed = [result for result in results if not result['success']]
    message = f'表 {table}：修复 {len(fixed)} 个字段'
    if failed:
        message += f'，失败 {len(failed)} 个'

    return jsonify({
        'success': not failed,
        'message': message,
        'fixed': fixed,
        'failed': failed,
        'skipped': [],
        'total_columns': len(columns)
    })


@blueprint.post('/fix_all_columns_batch')
def fix_all_columns_batch():
    data = request.json
    database = data.get('database')
    threshold = data.get('threshold', MAX_ROWS_THRESHOLD)
    if not database:
        return jsonify({'success': False, 'error': '缺少参数'})

    connection = get_connection(database)
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    fixed = []
    failed = []
    skipped = []
    current_app.logger.info(
        '开始批量修复字段：database=%s threshold=%s',
        database,
        threshold
    )
    try:
        cursor.execute("""
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """, (database,))
        tables = cursor.fetchall()
        current_app.logger.info(
            '批量字段扫描开始：database=%s tables=%s',
            database,
            len(tables)
        )

        for table in tables:
            table_name = table['TABLE_NAME']
            row_count = _row_count(cursor, table_name)
            if row_count > threshold:
                current_app.logger.warning(
                    '跳过超阈值表：database=%s table=%s rows=%s threshold=%s',
                    database,
                    table_name,
                    row_count,
                    threshold
                )
                skipped.append({
                    'table': table_name,
                    'row_count': row_count,
                    'reason': '行数超阈值'
                })
                continue

            columns = _columns(cursor, database, table_name)
            need_fix = [column for column in columns if column_needs_fix(column)]
            if need_fix:
                current_app.logger.info(
                    '发现异常字段：database=%s table=%s columns=%s',
                    database,
                    table_name,
                    [column['COLUMN_NAME'] for column in need_fix]
                )
            for column in need_fix:
                column_name = column['COLUMN_NAME']
                try:
                    _modify_column(cursor, table_name, column)
                    fixed.append({
                        'table': table_name,
                        'column': column_name
                    })
                except Exception as error:
                    failed.append({
                        'table': table_name,
                        'column': column_name,
                        'error': str(error)
                    })
    except Exception as error:
        current_app.logger.exception(
            '批量字段修复请求失败：database=%s',
            database
        )
        return jsonify({'success': False, 'error': str(error)})
    finally:
        cursor.close()
        connection.close()

    message = f'修复 {len(fixed)} 个字段'
    if skipped:
        message += f'，跳过 {len(skipped)} 张表'
    if failed:
        message += f'，失败 {len(failed)} 个'

    return jsonify({
        'success': not failed,
        'message': message,
        'fixed': fixed,
        'failed': failed,
        'skipped': skipped
    })
