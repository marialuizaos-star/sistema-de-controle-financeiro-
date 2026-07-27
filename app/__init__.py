from flask import Flask

from app.config import Config
from app.extensions import db, migrate, login_manager, mail


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    from app.models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from app.projetos.routes import projetos_bp
    app.register_blueprint(projetos_bp)

    def formatar_moeda(valor):
        if valor is None:
            return "0,00"
        texto = f"{valor:,.2f}"
        texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
        return texto

    app.jinja_env.filters["moeda"] = formatar_moeda

    return app