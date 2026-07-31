from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Alocacao, Projeto, Despesa, SolicitacaoRemanejamento
from app.remanejamentos.forms import SolicitarRemanejamentoForm, ReprovarRemanejamentoForm
from app.projetos.routes import _pode_ver_projeto

remanejamentos_bp = Blueprint("remanejamentos", __name__, template_folder="../templates/remanejamentos")

ROTULOS_CATEGORIA = {
    "custeio": "Custeio",
    "capital": "Capital",
}


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


def _rotulo_alocacao(alocacao, saldo, incluir_usuario=False):
    tipo = alocacao.tipo_alocacao.nome if alocacao.tipo_alocacao else "Sem tipo definido"
    categoria = ROTULOS_CATEGORIA.get(alocacao.categoria, alocacao.categoria)
    prefixo = f"{alocacao.usuario.nome} — " if incluir_usuario else ""
    return f"{prefixo}{tipo} ({categoria}) — saldo R$ {saldo:.2f}"


def _saldo_nao_gasto(alocacao):
    """Parte do valor alocado que ainda não virou despesa lançada — é esse o
    limite do que pode ser remanejado pra outra alocação."""
    total_gasto = (
        db.session.query(db.func.coalesce(db.func.sum(Despesa.valor), 0))
        .filter(Despesa.alocacao_id == alocacao.id, Despesa.status == "lancada")
        .scalar()
    )
    return alocacao.valor_alocado - Decimal(total_gasto)


@remanejamentos_bp.route("/projetos/<int:projeto_id>/remanejamentos/solicitar", methods=["GET", "POST"])
@login_required
def solicitar_remanejamento(projeto_id):
    """Pedido de remanejamento entre duas alocações do mesmo projeto. Quando
    solicitado por administrador, é executado na hora (o admin é quem também
    aprovaria); quando solicitado por usuário externo, fica pendente até o
    administrador aprovar ou reprovar."""
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _pode_ver_projeto(projeto_id):
        flash("Você não tem acesso a este projeto.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    eh_admin = current_user.papel == "administrador"
    query_alocacoes = Alocacao.query.filter_by(projeto_id=projeto.id)
    if not eh_admin:
        query_alocacoes = query_alocacoes.filter_by(usuario_id=current_user.id)
    alocacoes_disponiveis = query_alocacoes.order_by(Alocacao.id).all()

    if len(alocacoes_disponiveis) < 2:
        flash("É preciso ao menos duas alocações neste projeto para solicitar um remanejamento.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    # Saldo de cada alocação, calculado uma vez e reaproveitado no rótulo do
    # dropdown e na tabela de referência do template.
    saldos = {a.id: _saldo_nao_gasto(a) for a in alocacoes_disponiveis}

    form = SolicitarRemanejamentoForm()
    opcoes = [
        (a.id, _rotulo_alocacao(a, saldos[a.id], incluir_usuario=eh_admin))
        for a in alocacoes_disponiveis
    ]
    form.alocacao_origem_id.choices = opcoes
    form.alocacao_destino_id.choices = opcoes

    if form.validate_on_submit():
        origem = next((a for a in alocacoes_disponiveis if a.id == form.alocacao_origem_id.data), None)
        destino = next((a for a in alocacoes_disponiveis if a.id == form.alocacao_destino_id.data), None)
        if origem is None or destino is None:
            flash("Alocação inválida.", "erro")
            return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

        saldo_origem = _saldo_nao_gasto(origem)
        if form.valor.data > saldo_origem:
            flash(
                f"Valor acima do saldo ainda não gasto da alocação de origem "
                f"(R$ {saldo_origem:.2f} disponíveis para remanejar).",
                "erro",
            )
            return render_template(
                "remanejamentos/solicitar_remanejamento.html", form=form, projeto=projeto,
                alocacoes_disponiveis=alocacoes_disponiveis, saldos=saldos,
            )

        if eh_admin:
            origem.valor_alocado -= form.valor.data
            destino.valor_alocado += form.valor.data
            remanejamento = SolicitacaoRemanejamento(
                projeto_id=projeto.id,
                alocacao_origem_id=origem.id,
                alocacao_destino_id=destino.id,
                valor=form.valor.data,
                status="aprovado",
                justificativa=form.justificativa.data,
                solicitado_por_id=current_user.id,
            )
            db.session.add(remanejamento)
            db.session.commit()
            flash("Remanejamento executado com sucesso.", "sucesso")
        else:
            remanejamento = SolicitacaoRemanejamento(
                projeto_id=projeto.id,
                alocacao_origem_id=origem.id,
                alocacao_destino_id=destino.id,
                valor=form.valor.data,
                status="pendente",
                justificativa=form.justificativa.data,
                solicitado_por_id=current_user.id,
            )
            db.session.add(remanejamento)
            db.session.commit()
            flash("Pedido de remanejamento enviado para aprovação do administrador.", "sucesso")

        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    return render_template(
        "remanejamentos/solicitar_remanejamento.html", form=form, projeto=projeto,
        alocacoes_disponiveis=alocacoes_disponiveis, saldos=saldos,
    )


@remanejamentos_bp.route("/remanejamentos/pendentes")
@login_required
def remanejamentos_pendentes():
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    remanejamentos = (
        SolicitacaoRemanejamento.query.filter_by(status="pendente")
        .order_by(SolicitacaoRemanejamento.id)
        .all()
    )
    return render_template("remanejamentos/remanejamentos_pendentes.html", remanejamentos=remanejamentos)


@remanejamentos_bp.route("/remanejamentos/<int:remanejamento_id>/aprovar", methods=["POST"])
@login_required
def aprovar_remanejamento(remanejamento_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    remanejamento = db.session.get(SolicitacaoRemanejamento, remanejamento_id)
    if remanejamento is None:
        flash("Solicitação não encontrada.", "erro")
        return redirect(url_for("remanejamentos.remanejamentos_pendentes"))

    if remanejamento.status != "pendente":
        flash("Esta solicitação já foi analisada.", "erro")
        return redirect(url_for("remanejamentos.remanejamentos_pendentes"))

    origem = remanejamento.alocacao_origem
    saldo_origem = _saldo_nao_gasto(origem)
    if remanejamento.valor > saldo_origem:
        flash(
            f"Não é possível aprovar: a alocação de origem só tem R$ {saldo_origem:.2f} ainda não gastos "
            f"(o pedido é de R$ {remanejamento.valor:.2f}). Considere reprovar o pedido.",
            "erro",
        )
        return redirect(url_for("remanejamentos.remanejamentos_pendentes"))

    origem.valor_alocado -= remanejamento.valor
    remanejamento.alocacao_destino.valor_alocado += remanejamento.valor
    remanejamento.status = "aprovado"
    remanejamento.motivo_reprovacao = None
    db.session.commit()
    flash("Remanejamento aprovado e executado com sucesso.", "sucesso")
    return redirect(url_for("remanejamentos.remanejamentos_pendentes"))


@remanejamentos_bp.route("/remanejamentos/<int:remanejamento_id>/reprovar", methods=["GET", "POST"])
@login_required
def reprovar_remanejamento(remanejamento_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    remanejamento = db.session.get(SolicitacaoRemanejamento, remanejamento_id)
    if remanejamento is None:
        flash("Solicitação não encontrada.", "erro")
        return redirect(url_for("remanejamentos.remanejamentos_pendentes"))

    if remanejamento.status != "pendente":
        flash("Esta solicitação já foi analisada.", "erro")
        return redirect(url_for("remanejamentos.remanejamentos_pendentes"))

    form = ReprovarRemanejamentoForm()
    if form.validate_on_submit():
        remanejamento.status = "reprovado"
        remanejamento.motivo_reprovacao = form.motivo_reprovacao.data
        db.session.commit()
        flash("Pedido de remanejamento reprovado.", "sucesso")
        return redirect(url_for("remanejamentos.remanejamentos_pendentes"))

    return render_template("remanejamentos/reprovar_remanejamento.html", form=form, remanejamento=remanejamento)