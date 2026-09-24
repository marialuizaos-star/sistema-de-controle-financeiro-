from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Alocacao, Projeto, Despesa
from app.prestacoes.forms import ReprovarPrestacaoContasForm
from app.notificacoes.servicos import notificar_usuario, notificar_administradores

prestacoes_bp = Blueprint("prestacoes", __name__, template_folder="../templates/prestacoes")


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


def _eh_alocacao_principal(alocacao):
    return alocacao.alocacao_pai_id is None


def _pode_enviar_prestacao(alocacao):
    return _eh_alocacao_principal(alocacao) and current_user.id == alocacao.usuario_id


def _resumo_alocacao(alocacao):
    """Valor prestado, saldo a restituir e nº de comprovantes desta
    alocação principal — usado tanto na lista de pendentes quanto na
    tela de auditoria, pra dar contexto financeiro antes da decisão."""
    ids_alocacoes = [alocacao.id] + [s.id for s in alocacao.sub_alocacoes]
    despesas = Despesa.query.filter(Despesa.alocacao_id.in_(ids_alocacoes)).all()
    total_prestado = sum((d.valor for d in despesas if d.status == "lancada"), Decimal("0"))
    saldo_restituir = alocacao.valor_alocado - total_prestado
    total_comprovantes = sum(1 for d in despesas if d.comprovante)
    return despesas, total_prestado, saldo_restituir, total_comprovantes


@prestacoes_bp.route("/alocacoes/<int:alocacao_id>/prestacao/enviar", methods=["POST"])
@login_required
def enviar(alocacao_id):
    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _pode_enviar_prestacao(alocacao):
        flash("Você não tem permissão para enviar esta prestação de contas.", "erro")
        return redirect(url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=current_user.id))

    if alocacao.projeto.status != "ativo":
        flash("Só é possível enviar a prestação de contas de um projeto ativo.", "erro")
        return redirect(url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=current_user.id))

    if alocacao.status_prestacao_contas == "em_analise":
        flash("Sua prestação de contas já está em análise.", "erro")
        return redirect(url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=current_user.id))

    alocacao.status_prestacao_contas = "em_analise"
    alocacao.motivo_reprovacao_prestacao = None
    alocacao.enviada_em_prestacao = datetime.now(timezone.utc)

    notificar_administradores(
        f'Prestação de contas enviada para análise por {current_user.nome} no projeto "{alocacao.projeto.nome}".',
        link=url_for("prestacoes.pendentes"),
    )

    db.session.commit()
    flash("Prestação de contas enviada para análise do administrador.", "sucesso")
    return redirect(url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=current_user.id))


@prestacoes_bp.route("/prestacoes/pendentes")
@login_required
def pendentes():
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacoes = (
        Alocacao.query.filter_by(status_prestacao_contas="em_analise")
        .order_by(Alocacao.enviada_em_prestacao)
        .all()
    )

    resumos = {}
    for a in alocacoes:
        _despesas, total_prestado, saldo_restituir, total_comprovantes = _resumo_alocacao(a)
        resumos[a.id] = {
            "total_prestado": total_prestado,
            "saldo_restituir": saldo_restituir,
            "total_comprovantes": total_comprovantes,
        }

    return render_template("prestacoes/pendentes.html", alocacoes=alocacoes, resumos=resumos)


@prestacoes_bp.route("/alocacoes/<int:alocacao_id>/prestacao/auditar")
@login_required
def auditar(alocacao_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("prestacoes.pendentes"))

    despesas, total_prestado, saldo_restituir, total_comprovantes = _resumo_alocacao(alocacao)

    return render_template(
        "prestacoes/auditar.html", alocacao=alocacao, despesas=despesas,
        total_prestado=total_prestado, saldo_restituir=saldo_restituir,
        total_comprovantes=total_comprovantes,
    )


@prestacoes_bp.route("/alocacoes/<int:alocacao_id>/prestacao/aprovar", methods=["POST"])
@login_required
def aprovar(alocacao_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("prestacoes.pendentes"))

    if alocacao.status_prestacao_contas != "em_analise":
        flash("Esta prestação de contas não está aguardando análise.", "erro")
        return redirect(url_for("prestacoes.pendentes"))

    alocacao.status_prestacao_contas = "aceita"
    alocacao.motivo_reprovacao_prestacao = None

    notificar_usuario(
        alocacao.usuario_id,
        f'Sua prestação de contas no projeto "{alocacao.projeto.nome}" foi aprovada.',
        link=url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=alocacao.usuario_id),
    )

    db.session.commit()
    flash("Prestação de contas aprovada.", "sucesso")
    return redirect(url_for("prestacoes.pendentes"))


@prestacoes_bp.route("/alocacoes/<int:alocacao_id>/prestacao/reprovar", methods=["GET", "POST"])
@login_required
def reprovar(alocacao_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("prestacoes.pendentes"))

    if alocacao.status_prestacao_contas != "em_analise":
        flash("Esta prestação de contas não está aguardando análise.", "erro")
        return redirect(url_for("prestacoes.pendentes"))

    form = ReprovarPrestacaoContasForm()
    if form.validate_on_submit():
        alocacao.status_prestacao_contas = "reprovada"
        alocacao.motivo_reprovacao_prestacao = form.motivo_reprovacao.data

        notificar_usuario(
            alocacao.usuario_id,
            f'Sua prestação de contas no projeto "{alocacao.projeto.nome}" foi reprovada. Corrija e reenvie.',
            link=url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=alocacao.usuario_id),
        )

        db.session.commit()
        flash("Prestação de contas reprovada.", "sucesso")
        return redirect(url_for("prestacoes.pendentes"))

    return render_template("prestacoes/reprovar.html", form=form, alocacao=alocacao)