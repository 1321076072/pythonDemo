import pymysql
from dbutils.pooled_db import PooledDB

from storage import datasources


_pools = {}


def _pool_key(datasource, database):
    return (
        datasource['host'],
        datasource['port'],
        datasource['user'],
        datasource.get('id', ''),
        database or ''
    )


def _get_pool(datasource, database=None):
    key = _pool_key(datasource, database)
    if key not in _pools:
        options = {
            'creator': pymysql,
            'maxconnections': 5,
            'mincached': 1,
            'maxcached': 3,
            'blocking': True,
            'host': datasource['host'],
            'port': int(datasource['port']),
            'user': datasource['user'],
            'password': datasource.get('password', ''),
            'charset': 'utf8mb4'
        }
        if database:
            options['database'] = database
        _pools[key] = PooledDB(**options)
    return _pools[key]


def get_connection(database=None):
    datasource = datasources.get(datasources.current_id())
    if not datasource:
        raise RuntimeError('未连接数据源')
    return _get_pool(datasource, database).connection()


def clear_pool(datasource=None):
    if datasource is None:
        _pools.clear()
        return

    prefix = (
        datasource['host'],
        datasource['port'],
        datasource['user'],
        datasource.get('id', '')
    )
    for key in [key for key in _pools if key[:4] == prefix]:
        del _pools[key]
