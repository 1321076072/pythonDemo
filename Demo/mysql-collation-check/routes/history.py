from flask import Blueprint, jsonify

from storage import history


blueprint = Blueprint('history', __name__, url_prefix='/api')


@blueprint.get('/fix_history')
def get_fix_history():
    return jsonify({'success': True, 'data': history.all_records()})
