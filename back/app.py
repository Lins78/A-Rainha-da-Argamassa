import os

from flask import Flask, jsonify, Response
from werkzeug.exceptions import HTTPException

try:
    from .models import db
    from .config import Config
    from .routes import bp
except ImportError:  # pragma: no cover
    from models import db
    from config import Config
    from routes import bp


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "front"))


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
    )
    app.config.from_object(config_object)
    config_object.validate()
    db.init_app(app)
    app.register_blueprint(bp)

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if app.config.get("ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
        if isinstance(error, HTTPException):
            return jsonify({"msg": error.description}), error.code or 500
        app.logger.exception("Erro interno não tratado", exc_info=error)
        return jsonify({"msg": "Erro interno do servidor."}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=int(os.environ.get("APP_PORT", "5000")),
        debug=False,
    )

