import pymysql
from flask import Blueprint, jsonify, request

from config import TARGET_CHARSET, TARGET_COLLATION
from database import get_connection


blueprint = Blueprint('database_fixes', __name__, url_prefix='/api')


@blueprint.post('/fix_database_collation')
def fix_database_collation():
    database = request.json.get('database')
    if not database:
        return jsonify({'success': False, 'error': '缺少参数'})

    try:
        connection = get_connection()
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                f'ALTER DATABASE `{database}` CHARACTER SET '
                f'{TARGET_CHARSET} COLLATE {TARGET_COLLATION}'
            )
        connection.close()
        return jsonify({
            'success': True,
            'message': f'数据库 {database} 排序规则已修改为 {TARGET_COLLATION}'
        })
    except Exception as error:
        return jsonify({'success': False, 'error': str(error)})
