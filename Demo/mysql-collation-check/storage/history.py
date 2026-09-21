import datetime
import json

from config import FIX_HISTORY_FILE


_records = []


def load():
    global _records
    if FIX_HISTORY_FILE.exists():
        with FIX_HISTORY_FILE.open('r', encoding='utf-8') as file:
            _records = json.load(file)
    else:
        _records = []


def save():
    with FIX_HISTORY_FILE.open('w', encoding='utf-8') as file:
        json.dump(_records, file, ensure_ascii=False, indent=2)


def all_records():
    return _records


def add(database, results, skipped, total):
    details = [
        {
            'table': result['table'],
            'row_count': result.get('row_count'),
            'status': 'fixed' if result['success'] else 'failed',
            'error': result.get('error', '')
        }
        for result in results
    ]
    details.extend({
        'table': item['name'],
        'row_count': item['row_count'],
        'status': 'skipped',
        'error': '超过阈值'
    } for item in skipped)

    _records.insert(0, {
        'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'database': database,
        'total': total,
        'fixed': sum(result['success'] for result in results),
        'failed': sum(not result['success'] for result in results),
        'skipped': len(skipped),
        'details': details
    })
    del _records[100:]
    save()
