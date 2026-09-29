from datetime import datetime, timezone

from flask import Flask, render_template, redirect, url_for, flash
from flask_login import current_user
from flask_wtf.csrf import CSRFError

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
    from app.alocacoes.routes import alocacoes_bp
    app.register_blueprint(alocacoes_bp)
    from app.despesas.routes import despesas_bp
    app.register_blueprint(despesas_bp)
    from app.relatorios.routes import relatorios_bp
    app.register_blueprint(relatorios_bp)
    from app.remanejamentos.routes import remanejamentos_bp
    app.register_blueprint(remanejamentos_bp)
    from app.notificacoes.routes import notificacoes_bp
    app.register_blueprint(notificacoes_bp)
    from app.prestacoes.routes import prestacoes_bp
    app.register_blueprint(prestacoes_bp)
    from app.downloads.routes import downloads_bp
    app.register_blueprint(downloads_bp)

    def formatar_moeda(valor):
        if valor is None:
            return "0,00"
        texto = f"{valor:,.2f}"
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")

    app.jinja_env.filters["moeda"] = formatar_moeda

    ROTULOS = {
        "ativo": "Ativo", "inativo": "Inativo", "encerrado": "Encerrado",
        "pendente_aprovacao": "Pendente de aprovação", "reprovado": "Reprovado",
        "custeio": "Custeio", "capital": "Capital", "devolucao": "Devolução",
        "ambos": "Custeio e Capital",
        "lancada": "Lançada", "estornada": "Estornada", "reprovada": "Reprovada",
        "administrador": "Administrador", "usuario_externo": "Usuário Externo",
        "pendente": "Pendente", "aprovado": "Aprovado",
        "coordenador": "Coordenador", "pesquisador": "Pesquisador", "bolsista": "Bolsista",
        "tecnico": "Técnico", "colaborador": "Colaborador",
        "em_analise": "Em análise", "aceita": "Aceita",
    }

    def rotulo(valor):
        return ROTULOS.get(valor, valor)

    app.jinja_env.filters["rotulo"] = rotulo

    def tempo_relativo(dt):
        """Formato curto tipo 'Há 20 min', 'Ontem', 'Há 5 dias' — cai pra
        data completa (dd/mm/aaaa) depois de uma semana. A data/hora exata
        continua disponível no atributo title do elemento (tooltip)."""
        if dt is None:
            return ""
        agora = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        segundos = (agora - dt).total_seconds()
        if segundos < 60:
            return "Agora"
        minutos = int(segundos // 60)
        if minutos < 60:
            return f"Há {minutos} min"
        horas = int(minutos // 60)
        if horas < 24:
            return f"Há {horas} h"
        dias = int(horas // 24)
        if dias == 1:
            return "Ontem"
        if dias < 7:
            return f"Há {dias} dias"
        return dt.strftime("%d/%m/%Y")

    app.jinja_env.filters["tempo_relativo"] = tempo_relativo

    @app.context_processor
    def injetar_notificacoes():
        from app.models import Notificacao
        if not current_user.is_authenticated:
            return {"total_notificacoes_nao_lidas": 0, "notificacoes_recentes": []}
        total_nao_lidas = Notificacao.query.filter_by(usuario_id=current_user.id, lida=False).count()
        notificacoes_recentes = Notificacao.query.filter_by(usuario_id=current_user.id).order_by(Notificacao.criado_em.desc()).limit(5).all()
        return {"total_notificacoes_nao_lidas": total_nao_lidas, "notificacoes_recentes": notificacoes_recentes}

    @app.errorhandler(404)
    def erro_404(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def erro_403(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(413)
    def erro_413(e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def erro_500(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(CSRFError)
    def erro_csrf(e):
        flash("O formulário expirou (ficou aberto por muito tempo). Tente novamente.", "erro")
        if current_user.is_authenticated:
            return redirect(url_for("auth.painel"))
        return redirect(url_for("auth.login"))

    return app