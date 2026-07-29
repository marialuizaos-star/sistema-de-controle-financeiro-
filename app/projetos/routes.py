from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Projeto, Alocacao, Despesa
from app.projetos.forms import ProjetoForm

projetos_bp = Blueprint("projetos", __name__, template_folder="../templates/projetos")


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


def _pode_ver_projeto(projeto_id):
    if current_user.papel == "administrador":
        return True
    return Alocacao.query.filter_by(projeto_id=projeto_id, usuario_id=current_user.id).first() is not None


@projetos_bp.route("/projetos")
@login_required
def listar_projetos():
    if current_user.papel == "administrador":
        projetos = Projeto.query.order_by(Projeto.nome).all()
    else:
        projetos = (
            Projeto.query.join(Alocacao)
            .filter(Alocacao.usuario_id == current_user.id)
            .distinct()
            .order_by(Projeto.nome)
            .all()
        )
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


@projetos_bp.route("/projetos/<int:projeto_id>")
@login_required
def detalhe_projeto(projeto_id):
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _pode_ver_projeto(projeto_id):
        flash("Você não tem acesso a este projeto.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    alocacoes = Alocacao.query.filter_by(projeto_id=projeto.id).all()
    total_alocado = sum((a.valor_alocado for a in alocacoes), Decimal("0"))
    saldo_disponivel = projeto.valor_total - total_alocado

    grafico = {}
    for a in alocacoes:
        nome_tipo = a.tipo_despesa.nome if a.tipo_despesa else "Sem tipo definido"
        grafico[nome_tipo] = grafico.get(nome_tipo, Decimal("0")) + a.valor_alocado

    despesas_query = Despesa.query.join(Alocacao).filter(Alocacao.projeto_id == projeto.id).order_by(Despesa.data.desc())
    if current_user.papel != "administrador":
        despesas_query = despesas_query.filter(Alocacao.usuario_id == current_user.id)
    despesas = despesas_query.all()

    return render_template(
        "projetos/detalhe_projeto.html",
        projeto=projeto,
        alocacoes=alocacoes,
        total_alocado=total_alocado,
        saldo_disponivel=saldo_disponivel,
        grafico_labels=list(grafico.keys()),
        grafico_valores=[float(v) for v in grafico.values()],
        despesas=despesas,
    )


@projetos_bp.route("/projetos/<int:projeto_id>/excluir", methods=["POST"])
@login_required
def excluir_projeto(projeto_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if Alocacao.query.filter_by(projeto_id=projeto.id).first():
        flash(
            "Este projeto já tem alocações vinculadas e não pode ser excluído. Use o status 'Encerrado' em vez disso.",
            "erro",
        )
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    db.session.delete(projeto)
    db.session.commit()
    flash("Projeto excluído com sucesso.", "sucesso")
    return redirect(url_for("projetos.listar_projetos"))