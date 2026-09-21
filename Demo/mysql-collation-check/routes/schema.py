import pymysql
from flask import Blueprint, jsonify, request

from database import get_connection
from services.collation import (
    annotate_table,
    column_needs_fix,
    fetch_column_issues
)


blueprint = Blueprint('schema', __name__, url_prefix='/api')


@blueprint.get('/databases')
def get_databases():
    try:
        connection = get_connection()
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('SHOW DATABASES')
            databases = [row['Database'] for row in cursor.fetchall()]
        connection.close()
        return jsonify({'success': True, 'data': databases})
    except Exception as error:
        return jsonify({'success': False, 'error': str(error)})


@blueprint.get('/tables/<database>')
def get_tables(database):
    try:
        connection = get_connection(database)
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_COLLATION, TABLE_ROWS, DATA_LENGTH
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """, (database,))
            tables = cursor.fetchall()
            issues = fetch_column_issues(cursor, database)
            for table in tables:
                annotate_table(table, issues)
        connection.close()
        return jsonify({'success': True, 'data': tables})
    except Exception as error:
        return jsonify({'success': False, 'error': str(error)})


@blueprint.get('/columns/<database>/<table>')
def get_columns(database, table):
    try:
        connection = get_connection(database)
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, CHARACTER_SET_NAME, COLLATION_NAME,
                       IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (database, table))
            columns = cursor.fetchall()
            for column in columns:
                column['need_fix'] = column_needs_fix(column)
        connection.close()
        return jsonify({'success': True, 'data': columns})
    except Exception as error:
        return jsonify({'success': False, 'error': str(error)})


@blueprint.post('/row_counts')
def get_row_counts():
    data = request.json
    database = data.get('database')
    tables = data.get('tables', [])
    if not database or not tables:
        return jsonify({'success': False, 'error': '缺少参数'})

    connection = get_connection(database)
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    results = {}
    try:
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
                results[table] = cursor.fetchone()['cnt']
            except Exception as error:
                results[table] = f'错误: {error}'
    finally:
        cursor.close()
        connection.close()
    return jsonify({'success': True, 'data': results})


@blueprint.get('/column_issues/<database>')
def get_column_issues(database):
    try:
        connection = get_connection(database)
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            issues = fetch_column_issues(cursor, database)
            result = [
                {'table': table, 'columns': columns}
                for table, columns in issues.items()
            ]
        connection.close()
        return jsonify({'success': True, 'data': result, 'total': len(result)})
    except Exception as error:
        return jsonify({'success': False, 'error': str(error)})
