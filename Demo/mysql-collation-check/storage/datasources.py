import json

from config import DATASOURCE_FILE


_datasources = []
_current_id = None


def load():
    global _datasources
    if DATASOURCE_FILE.exists():
        with DATASOURCE_FILE.open('r', encoding='utf-8') as file:
            _datasources = json.load(file)
    else:
        _datasources = []


def save():
    with DATASOURCE_FILE.open('w', encoding='utf-8') as file:
        json.dump(_datasources, file, ensure_ascii=False, indent=2)


def all_datasources():
    return _datasources


def get(ds_id):
    return next((ds for ds in _datasources if ds['id'] == ds_id), None)


def add(datasource):
    _datasources.append(datasource)
    save()


def remove(datasource):
    _datasources.remove(datasource)
    save()


def current_id():
    return _current_id


def set_current_id(ds_id):
    global _current_id
    _current_id = ds_id
