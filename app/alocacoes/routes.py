from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Alocacao, Projeto, Usuario, TipoAlocacao
from app.alocacoes.forms import AlocacaoForm, TipoAlocacaoForm, MarcarProblemaAlocacaoForm
from app.projetos.routes import _pode_ver_projeto

alocacoes_bp = Blueprint("alocacoes", __name__, template_folder="../templates/alocacoes")


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


def _preencher_opcoes(form, eh_admin):
    if eh_admin:
        form.usuario_id.choices = [
            (u.id, f"{u.nome} — {u.email}")
            for u in Usuario.query.filter_by(ativo=True).order_by(Usuario.nome).all()
        ]
    else:
        form.usuario_id.choices = [(current_user.id, f"{current_user.nome} — {current_user.email}")]
        form.usuario_id.data = current_user.id

    form.tipo_alocacao_id.choices = [
        (t.id, t.nome)
        for t in TipoAlocacao.query.filter_by(ativo=True).order_by(TipoAlocacao.nome).all()
    ]


def _mapa_categoria_padrao():
    return {
        t.id: t.categoria_padrao
        for t in TipoAlocacao.query.filter_by(ativo=True).all()
        if t.categoria_padrao
    }


def _saldo_disponivel(projeto, alocacao_atual_id=None):
    query = Alocacao.query.filter_by(projeto_id=projeto.id)
    if alocacao_atual_id:
        query = query.filter(Alocacao.id != alocacao_atual_id)
    total_alocado = sum((a.valor_alocado for a in query.all()), Decimal("0"))
    return projeto.valor_total - total_alocado


def _total_alocado(projeto, alocacao_atual_id=None):
    query = Alocacao.query.filter_by(projeto_id=projeto.id)
    if alocacao_atual_id:
        query = query.filter(Alocacao.id != alocacao_atual_id)
    return sum((a.valor_alocado for a in query.all()), Decimal("0"))


@alocacoes_bp.route("/projetos/<int:projeto_id>/alocacoes/nova", methods=["GET", "POST"])
@login_required
def nova_alocacao(projeto_id):
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _pode_ver_projeto(projeto_id):
        flash("Você não tem acesso a este projeto.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    eh_admin = current_user.papel == "administrador"
    form = AlocacaoForm()
    _preencher_opcoes(form, eh_admin)

    total_alocado = _total_alocado(projeto)
    saldo = projeto.valor_total - total_alocado

    if form.validate_on_submit():
        if form.valor_alocado.data > saldo:
            flash(
                f"Valor acima do saldo disponível do projeto (R$ {saldo:.2f} restantes).",
                "erro",
            )
            return render_template(
                "alocacoes/nova_alocacao.html", form=form, projeto=projeto, eh_admin=eh_admin,
                total_alocado=total_alocado, saldo=saldo, mapa_categoria_padrao=_mapa_categoria_padrao(),
            )

        alocacao = Alocacao(
            projeto_id=projeto.id,
            usuario_id=form.usuario_id.data,
            tipo_alocacao_id=form.tipo_alocacao_id.data,
            categoria=form.categoria.data,
            valor_alocado=form.valor_alocado.data,
        )
        db.session.add(alocacao)
        db.session.commit()
        flash("Alocação cadastrada com sucesso.", "sucesso")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    return render_template(
        "alocacoes/nova_alocacao.html", form=form, projeto=projeto, eh_admin=eh_admin,
        total_alocado=total_alocado, saldo=saldo, mapa_categoria_padrao=_mapa_categoria_padrao(),
    )


@alocacoes_bp.route("/alocacoes/<int:alocacao_id>/editar", methods=["GET", "POST"])
@login_required
def editar_alocacao(alocacao_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    projeto = alocacao.projeto
    form = AlocacaoForm(obj=alocacao)
    _preencher_opcoes(form, eh_admin=True)

    if form.validate_on_submit():
        saldo = _saldo_disponivel(projeto, alocacao_atual_id=alocacao.id)
        if form.valor_alocado.data > saldo:
            flash(
                f"Valor acima do saldo disponível do projeto (R$ {saldo:.2f} restantes).",
                "erro",
            )
            return render_template(
                "alocacoes/editar_alocacao.html", form=form, alocacao=alocacao, projeto=projeto,
                mapa_categoria_padrao=_mapa_categoria_padrao(),
            )

        alocacao.usuario_id = form.usuario_id.data
        alocacao.tipo_alocacao_id = form.tipo_alocacao_id.data
        alocacao.categoria = form.categoria.data
        alocacao.valor_alocado = form.valor_alocado.data
        db.session.commit()
        flash("Alocação atualizada com sucesso.", "sucesso")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    return render_template(
        "alocacoes/editar_alocacao.html", form=form, alocacao=alocacao, projeto=projeto,
        mapa_categoria_padrao=_mapa_categoria_padrao(),
    )


@alocacoes_bp.route("/alocacoes/<int:alocacao_id>/marcar-problema", methods=["GET", "POST"])
@login_required
def marcar_problema(alocacao_id):
    """Admin sinaliza que uma alocação específica de um projeto pendente tem
    algo errado, com motivo — usado durante a revisão, antes de aprovar ou
    reprovar o projeto como um todo (Opção A, decisão de 03/08/2026)."""
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if alocacao.projeto.status != "pendente_aprovacao":
        flash("Só é possível marcar problema em alocação de projeto pendente de aprovação.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))

    form = MarcarProblemaAlocacaoForm()
    if form.validate_on_submit():
        alocacao.motivo_reprovacao = form.motivo.data
        db.session.commit()
        flash("Alocação marcada.", "sucesso")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))

    return render_template("alocacoes/marcar_problema.html", form=form, alocacao=alocacao)


@alocacoes_bp.route("/alocacoes/<int:alocacao_id>/remover-marcacao", methods=["POST"])
@login_required
def remover_marcacao(alocacao_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    alocacao.motivo_reprovacao = None
    db.session.commit()
    flash("Marcação removida.", "sucesso")
    return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))


@alocacoes_bp.route("/tipos-alocacao", methods=["GET", "POST"])
@login_required
def tipos_alocacao():
    form = TipoAlocacaoForm()
    if form.validate_on_submit():
        nome = form.nome.data.strip()
        if TipoAlocacao.query.filter_by(nome=nome).first():
            flash("Esse tipo de alocação já existe.", "erro")
        else:
            db.session.add(TipoAlocacao(
                nome=nome, ativo=True, categoria_padrao=form.categoria_padrao.data,
                documentos_obrigatorios=form.documentos_obrigatorios.data,
            ))
            db.session.commit()
            flash("Tipo de alocação adicionado.", "sucesso")
        return redirect(url_for("alocacoes.tipos_alocacao"))

    tipos = TipoAlocacao.query.order_by(TipoAlocacao.nome).all()
    return render_template("alocacoes/tipos_alocacao.html", form=form, tipos=tipos)


@alocacoes_bp.route("/tipos-alocacao/<int:tipo_id>/alternar-status", methods=["POST"])
@login_required
def alternar_status_tipo_alocacao(tipo_id):
    tipo = db.session.get(TipoAlocacao, tipo_id)
    if tipo is None:
        flash("Tipo de alocação não encontrado.", "erro")
    else:
        tipo.ativo = not tipo.ativo
        db.session.commit()
        flash("Tipo de alocação atualizado.", "sucesso")
    return redirect(url_for("alocacoes.tipos_alocacao"))