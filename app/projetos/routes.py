from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Projeto
from app.projetos.forms import ProjetoForm

projetos_bp = Blueprint("projetos", __name__, template_folder="../templates/projetos")


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


@projetos_bp.route("/projetos")
@login_required
def listar_projetos():
    projetos = Projeto.query.order_by(Projeto.nome).all()
    return render_template("projetos/listar_projetos.html", projetos=projetos)


@projetos_bp.route("/projetos/novo", methods=["GET", "POST"])
@login_required
def novo_projeto():
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    form = ProjetoForm()
    if form.validate_on_submit():
        projeto = Projeto(
            nome=form.nome.data,
            valor_total=form.valor_total.data,
            vigencia_inicio=form.vigencia_inicio.data,
            vigencia_fim=form.vigencia_fim.data,
            status=form.status.data,
        )
        db.session.add(projeto)
        db.session.commit()
        flash("Projeto cadastrado com sucesso.", "sucesso")
        return redirect(url_for("projetos.listar_projetos"))

    return render_template("projetos/novo_projeto.html", form=form)


@projetos_bp.route("/projetos/<int:projeto_id>/editar", methods=["GET", "POST"])
@login_required
def editar_projeto(projeto_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    form = ProjetoForm(obj=projeto)
    if form.validate_on_submit():
        projeto.nome = form.nome.data
        projeto.valor_total = form.valor_total.data
        projeto.vigencia_inicio = form.vigencia_inicio.data
        projeto.vigencia_fim = form.vigencia_fim.data
        projeto.status = form.status.data
        db.session.commit()
        flash("Projeto atualizado com sucesso.", "sucesso")
        return redirect(url_for("projetos.listar_projetos"))

    return render_template("projetos/editar_projeto.html", form=form, projeto=projeto)