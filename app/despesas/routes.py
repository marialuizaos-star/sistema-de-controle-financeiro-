import os
import uuid
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Alocacao, Despesa, Comprovante, Projeto
from app.despesas.forms import DespesaForm

despesas_bp = Blueprint("despesas", __name__, template_folder="../templates/despesas")

ROTULOS_CATEGORIA = {
    "custeio": "Custeio",
    "capital": "Capital",
}


def _pode_lancar(alocacao):
    return current_user.papel == "administrador" or current_user.id == alocacao.usuario_id


def _saldo_alocacao(alocacao, despesa_atual_id=None):
    query = Despesa.query.filter_by(alocacao_id=alocacao.id, status="lancada")
    if despesa_atual_id:
        query = query.filter(Despesa.id != despesa_atual_id)
    total_gasto = sum((d.valor for d in query.all()), Decimal("0"))
    return alocacao.valor_alocado - total_gasto


def _saldo_disponivel_projeto(projeto):
    total_despesas = (
        db.session.query(db.func.coalesce(db.func.sum(Despesa.valor), 0))
        .join(Alocacao)
        .filter(Alocacao.projeto_id == projeto.id, Despesa.status == "lancada")
        .scalar()
    )
    return projeto.valor_total - Decimal(total_despesas)


def _rotulo_alocacao(alocacao, incluir_usuario=False):
    tipo = alocacao.tipo_alocacao.nome if alocacao.tipo_alocacao else "Sem tipo definido"
    categoria = ROTULOS_CATEGORIA.get(alocacao.categoria, alocacao.categoria)
    saldo = _saldo_alocacao(alocacao)
    prefixo = f"{alocacao.usuario.nome} — " if incluir_usuario else ""
    return f"{prefixo}{tipo} ({categoria}) — saldo R$ {saldo:.2f}"


def _projeto_permite_despesa(projeto):
    return projeto.status == "ativo"


def _despesas_do_projeto(projeto):
    """Despesas visíveis ao usuário atual no contexto deste projeto: todas,
    se administrador; só as das próprias alocações, se usuário externo."""
    query = Despesa.query.join(Alocacao).filter(Alocacao.projeto_id == projeto.id).order_by(Despesa.data.desc())
    if current_user.papel != "administrador":
        query = query.filter(Alocacao.usuario_id == current_user.id)
    return query.all()


def _salvar_despesa(form, alocacao):
    arquivo = form.comprovante.data
    extensao = arquivo.filename.rsplit(".", 1)[-1].lower()
    nome_arquivo = f"{uuid.uuid4().hex}.{extensao}"
    pasta = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(pasta, exist_ok=True)
    arquivo.save(os.path.join(pasta, nome_arquivo))

    despesa = Despesa(
        alocacao_id=alocacao.id,
        data=form.data.data,
        valor=form.valor.data,
        natureza=form.natureza.data,
        fornecedor=form.fornecedor.data,
        cnpj_favorecido=form.cnpj_favorecido.data,
        numero_comprovante_fiscal=form.numero_comprovante_fiscal.data,
        descricao=form.descricao.data,
        status="lancada",
    )
    db.session.add(despesa)
    db.session.flush()

    comprovante = Comprovante(despesa_id=despesa.id, arquivo=nome_arquivo)
    db.session.add(comprovante)
    db.session.commit()
    return despesa


@despesas_bp.route("/alocacoes/<int:alocacao_id>/despesas/nova", methods=["GET", "POST"])
@login_required
def nova_despesa(alocacao_id):
    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _pode_lancar(alocacao):
        flash("Você não tem permissão para lançar despesas nesta alocação.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))

    if not _projeto_permite_despesa(alocacao.projeto):
        flash("Este projeto ainda não foi aprovado pelo administrador. Não é possível lançar despesas.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))

    form = DespesaForm()
    form.alocacao_id.choices = [(alocacao.id, _rotulo_alocacao(alocacao))]
    if not form.is_submitted():
        form.alocacao_id.data = alocacao.id
        form.natureza.data = alocacao.categoria

    despesas = Despesa.query.filter_by(alocacao_id=alocacao.id).order_by(Despesa.data.desc()).all()
    saldo = _saldo_alocacao(alocacao)
    total_gasto = alocacao.valor_alocado - saldo

    if form.validate_on_submit():
        if form.valor.data > saldo:
            flash(f"Valor acima do saldo disponível desta alocação (R$ {saldo:.2f} restantes).", "erro")
            return render_template(
                "despesas/nova_despesa.html", form=form, alocacao=alocacao,
                despesas=despesas, saldo=saldo, total_gasto=total_gasto,
            )

        _salvar_despesa(form, alocacao)
        flash("Despesa lançada com sucesso.", "sucesso")
        return redirect(url_for("despesas.nova_despesa", alocacao_id=alocacao.id))

    return render_template(
        "despesas/nova_despesa.html", form=form, alocacao=alocacao,
        despesas=despesas, saldo=saldo, total_gasto=total_gasto,
    )


@despesas_bp.route("/projetos/<int:projeto_id>/despesas/nova", methods=["GET", "POST"])
@login_required
def nova_despesa_projeto(projeto_id):
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _projeto_permite_despesa(projeto):
        flash("Este projeto ainda não foi aprovado pelo administrador. Não é possível lançar despesas.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    query_alocacoes = Alocacao.query.filter_by(projeto_id=projeto.id)
    if current_user.papel != "administrador":
        query_alocacoes = query_alocacoes.filter_by(usuario_id=current_user.id)
    alocacoes_disponiveis = query_alocacoes.order_by(Alocacao.id).all()

    if not alocacoes_disponiveis:
        flash("Não há alocações disponíveis para lançar despesa neste projeto.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    saldo_projeto = _saldo_disponivel_projeto(projeto)
    despesas = _despesas_do_projeto(projeto)

    form = DespesaForm()
    form.alocacao_id.choices = [
        (a.id, _rotulo_alocacao(a, incluir_usuario=(current_user.papel == "administrador")))
        for a in alocacoes_disponiveis
    ]

    if form.validate_on_submit():
        alocacao = next((a for a in alocacoes_disponiveis if a.id == form.alocacao_id.data), None)
        if alocacao is None:
            flash("Alocação inválida.", "erro")
            return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

        saldo = _saldo_alocacao(alocacao)
        if form.valor.data > saldo:
            flash(f"Valor acima do saldo disponível desta alocação (R$ {saldo:.2f} restantes).", "erro")
            return render_template(
                "despesas/nova_despesa_projeto.html", form=form, projeto=projeto,
                saldo_projeto=saldo_projeto, despesas=despesas,
            )

        _salvar_despesa(form, alocacao)
        flash("Despesa lançada com sucesso.", "sucesso")
        return redirect(url_for("despesas.nova_despesa_projeto", projeto_id=projeto.id))

    return render_template(
        "despesas/nova_despesa_projeto.html", form=form, projeto=projeto,
        saldo_projeto=saldo_projeto, despesas=despesas,
    )


@despesas_bp.route("/despesas/<int:despesa_id>/comprovante")
@login_required
def ver_comprovante(despesa_id):
    despesa = db.session.get(Despesa, despesa_id)
    if despesa is None or despesa.comprovante is None:
        flash("Comprovante não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    pasta = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(pasta, despesa.comprovante.arquivo)


@despesas_bp.route("/despesas/<int:despesa_id>/estornar", methods=["POST"])
@login_required
def estornar_despesa(despesa_id):
    despesa = db.session.get(Despesa, despesa_id)
    if despesa is None:
        flash("Despesa não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = despesa.alocacao
    if current_user.papel != "administrador":
        flash("Somente o administrador pode estornar uma despesa.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))

    despesa.status = "estornada"
    db.session.commit()
    flash("Despesa estornada com sucesso.", "sucesso")
    return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))


@despesas_bp.route("/projetos/<int:projeto_id>/despesas")
@login_required
def listar_despesas(projeto_id):
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    despesas = _despesas_do_projeto(projeto)
    return render_template("despesas/listar_despesas.html", despesas=despesas, projeto=projeto)