from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Notificacao

notificacoes_bp = Blueprint("notificacoes", __name__, template_folder="../templates/notificacoes")


@notificacoes_bp.route("/notificacoes")
@login_required
def listar():
    notificacoes = (
        Notificacao.query.filter_by(usuario_id=current_user.id)
        .order_by(Notificacao.criado_em.desc())
        .all()
    )
    return render_template("notificacoes/listar.html", notificacoes=notificacoes)


@notificacoes_bp.route("/notificacoes/<int:notificacao_id>/abrir")
@login_required
def abrir(notificacao_id):
    """Usado quando a pessoa clica numa notificação (no sino ou na lista
    completa): marca como lida e leva pro link relacionado, se houver."""
    notificacao = db.session.get(Notificacao, notificacao_id)
    if notificacao is None or notificacao.usuario_id != current_user.id:
        flash("Notificação não encontrada.", "erro")
        return redirect(url_for("notificacoes.listar"))

    if not notificacao.lida:
        notificacao.lida = True
        db.session.commit()

    if notificacao.link:
        return redirect(notificacao.link)
    return redirect(url_for("notificacoes.listar"))


@notificacoes_bp.route("/notificacoes/<int:notificacao_id>/marcar-lida", methods=["POST"])
@login_required
def marcar_lida(notificacao_id):
    """Marca como lida sem sair da página atual (botão dedicado na lista
    completa, diferente de clicar na notificação em si)."""
    notificacao = db.session.get(Notificacao, notificacao_id)
    if notificacao is None or notificacao.usuario_id != current_user.id:
        flash("Notificação não encontrada.", "erro")
        return redirect(url_for("notificacoes.listar"))

    notificacao.lida = True
    db.session.commit()
    return redirect(url_for("notificacoes.listar"))


@notificacoes_bp.route("/notificacoes/marcar-todas-lidas", methods=["POST"])
@login_required
def marcar_todas_lidas():
    Notificacao.query.filter_by(usuario_id=current_user.id, lida=False).update({"lida": True})
    db.session.commit()
    flash("Todas as notificações foram marcadas como lidas.", "sucesso")
    return redirect(request.referrer or url_for("auth.painel"))