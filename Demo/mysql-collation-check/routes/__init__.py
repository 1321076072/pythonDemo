from routes.datasources import blueprint as datasource_blueprint
from routes.fix_columns import blueprint as column_fix_blueprint
from routes.fix_database import blueprint as database_fix_blueprint
from routes.fix_tables import blueprint as table_fix_blueprint
from routes.history import blueprint as history_blueprint
from routes.pages import blueprint as page_blueprint
from routes.schema import blueprint as schema_blueprint


def register_blueprints(app):
    app.register_blueprint(page_blueprint)
    app.register_blueprint(datasource_blueprint)
    app.register_blueprint(schema_blueprint)
    app.register_blueprint(table_fix_blueprint)
    app.register_blueprint(column_fix_blueprint)
    app.register_blueprint(database_fix_blueprint)
    app.register_blueprint(history_blueprint)
