from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")

    from .routes.stock_routes import stock_blueprint
    app.register_blueprint(stock_blueprint)

    from .sockets.stock_sockets import register_sockets
    register_sockets(socketio)

    return app
