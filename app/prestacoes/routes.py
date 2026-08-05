from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Projeto
from app.prestacoes.forms import ReprovarPrestacaoContasForm
from app.notificacoes.servicos import notificar_usuario, notificar_administradores

prestacoes_bp = Blueprint("prestacoes", __name__, template_folder="../templates/prestacoes")


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


def _pode_enviar_prestacao(projeto):
    """Só quem solicitou o cadastro do projeto pode enviar a prestação de
    contas. Projetos cadastrados diretamente pelo administrador (sem
    solicitante) não passam por esse fluxo — o admin já controla o status
    desse tipo de projeto diretamente, pela edição do projeto."""
    return projeto.criado_por_id is not None and current_user.id == projeto.criado_por_id


@prestacoes_bp.route("/projetos/<int:projeto_id>/prestacao/enviar", methods=["POST"])
@login_required
def enviar(projeto_id):
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _pode_enviar_prestacao(projeto):
        flash("Você não tem permissão para enviar a prestação de contas deste projeto.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    if projeto.status != "ativo":
        flash("Só é possível enviar a prestação de contas de um projeto ativo.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    if projeto.status_prestacao_contas == "em_analise":
        flash("A prestação de contas deste projeto já está em análise.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    projeto.status_prestacao_contas = "em_analise"
    projeto.motivo_reprovacao_prestacao = None
    projeto.enviada_em_prestacao = datetime.now(timezone.utc)

    notificar_administradores(
        f'Prestação de contas enviada para análise: "{projeto.nome}".',
        link=url_for("projetos.detalhe_projeto", projeto_id=projeto.id),
    )

    db.session.commit()
    flash("Prestação de contas enviada para análise do administrador.", "sucesso")
    return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))


@prestacoes_bp.route("/prestacoes/pendentes")
@login_required
def pendentes():
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projetos = (
        Projeto.query.filter_by(status_prestacao_contas="em_analise")
        .order_by(Projeto.enviada_em_prestacao)
        .all()
    )
    return render_template("prestacoes/pendentes.html", projetos=projetos)


@prestacoes_bp.route("/projetos/<int:projeto_id>/prestacao/aprovar", methods=["POST"])
@login_required
def aprovar(projeto_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("prestacoes.pendentes"))

    if projeto.status_prestacao_contas != "em_analise":
        flash("Esta prestação de contas não está aguardando análise.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    projeto.status_prestacao_contas = "aceita"
    projeto.motivo_reprovacao_prestacao = None
    projeto.status = "encerrado"

    if projeto.criado_por_id:
        notificar_usuario(
            projeto.criado_por_id,
            f'A prestação de contas do projeto "{projeto.nome}" foi aceita. Projeto encerrado.',
            link=url_for("projetos.detalhe_projeto", projeto_id=projeto.id),
        )

    db.session.commit()
    flash("Prestação de contas aceita. Projeto encerrado com sucesso.", "sucesso")
    return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))


@prestacoes_bp.route("/projetos/<int:projeto_id>/prestacao/reprovar", methods=["GET", "POST"])
@login_required
def reprovar(projeto_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("prestacoes.pendentes"))

    if projeto.status_prestacao_contas != "em_analise":
        flash("Esta prestação de contas não está aguardando análise.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    form = ReprovarPrestacaoContasForm()
    if form.validate_on_submit():
        projeto.status_prestacao_contas = "reprovada"
        projeto.motivo_reprovacao_prestacao = form.motivo_reprovacao.data

        if projeto.criado_por_id:
            notificar_usuario(
                projeto.criado_por_id,
                f'A prestação de contas do projeto "{projeto.nome}" foi reprovada. Corrija e reenvie.',
                link=url_for("projetos.detalhe_projeto", projeto_id=projeto.id),
            )

        db.session.commit()
        flash("Prestação de contas reprovada.", "sucesso")
        return redirect(url_for("prestacoes.pendentes"))

    return render_template("prestacoes/reprovar.html", form=form, projeto=projeto)