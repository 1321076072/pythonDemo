import logging

from flask import Flask

from routes import register_blueprints
from storage import datasources, history


def create_app():
    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)
    register_blueprints(app)
    datasources.load()
    history.load()
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
