import uuid

import pymysql
from flask import Blueprint, jsonify, request

from database import clear_pool
from storage import datasources


blueprint = Blueprint('datasources', __name__, url_prefix='/api')


def _without_password(datasource):
    return {key: value for key, value in datasource.items() if key != 'password'}


@blueprint.get('/datasources')
def list_datasources():
    safe = [_without_password(ds) for ds in datasources.all_datasources()]
    return jsonify({
        'success': True,
        'data': safe,
        'current_id': datasources.current_id()
    })


@blueprint.post('/datasources')
def create_datasource():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': '名称不能为空'})

    datasource = {
        'id': uuid.uuid4().hex[:12],
        'name': name,
        'host': data.get('host', 'localhost').strip(),
        'port': int(data.get('port', 3306)),
        'user': data.get('user', 'root').strip(),
        'password': data.get('password', '')
    }
    datasources.add(datasource)
    return jsonify({'success': True, 'data': _without_password(datasource)})


@blueprint.put('/datasources/<ds_id>')
def update_datasource(ds_id):
    datasource = datasources.get(ds_id)
    if not datasource:
        return jsonify({'success': False, 'error': '数据源不存在'})

    data = request.json
    for field in ('name', 'host', 'port', 'user', 'password'):
        if field in data:
            value = data[field]
            datasource[field] = value.strip() if isinstance(value, str) else value
    datasource['port'] = int(datasource['port'])
    datasources.save()
    clear_pool(datasource)
    return jsonify({'success': True, 'data': _without_password(datasource)})


@blueprint.delete('/datasources/<ds_id>')
def delete_datasource(ds_id):
    datasource = datasources.get(ds_id)
    if not datasource:
        return jsonify({'success': False, 'error': '数据源不存在'})

    datasources.remove(datasource)
    clear_pool(datasource)
    if datasources.current_id() == ds_id:
        datasources.set_current_id(None)
        clear_pool()
    return jsonify({'success': True})


@blueprint.post('/datasources/<ds_id>/connect')
def connect_datasource(ds_id):
    datasource = datasources.get(ds_id)
    if not datasource:
        return jsonify({'success': False, 'error': '数据源不存在'})

    try:
        connection = pymysql.connect(
            host=datasource['host'],
            port=int(datasource['port']),
            user=datasource['user'],
            password=datasource.get('password', ''),
            charset='utf8mb4'
        )
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('SELECT VERSION() as version')
            version = cursor.fetchone()
        connection.close()

        old_datasource = datasources.get(datasources.current_id())
        datasources.set_current_id(ds_id)
        if old_datasource and old_datasource['id'] != ds_id:
            clear_pool(old_datasource)

        return jsonify({
            'success': True,
            'message': f'连接成功！MySQL版本：{version["version"]}'
        })
    except Exception as error:
        return jsonify({'success': False, 'error': str(error)})
