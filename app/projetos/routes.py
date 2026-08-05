import os
import uuid
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from sqlalchemy import extract

from app.extensions import db
from app.models import Projeto, Alocacao, Despesa, TipoAlocacao
from app.projetos.forms import ProjetoForm, SolicitarProjetoForm, ReprovarProjetoForm, EnviarInstrucoesForm

projetos_bp = Blueprint("projetos", __name__, template_folder="../templates/projetos")


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


def _pode_ver_projeto(projeto_id):
    if current_user.papel == "administrador":
        return True

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is not None and projeto.criado_por_id == current_user.id:
        return True

    return Alocacao.query.filter_by(projeto_id=projeto_id, usuario_id=current_user.id).first() is not None


def _opcoes_tipo_alocacao():
    return [
        (t.id, t.nome)
        for t in TipoAlocacao.query.filter_by(ativo=True).order_by(TipoAlocacao.nome).all()
    ]


def _mapa_categoria_padrao():
    return {
        t.id: t.categoria_padrao
        for t in TipoAlocacao.query.filter_by(ativo=True).all()
        if t.categoria_padrao
    }


def _preencher_opcoes_itens_plano(form, opcoes_tipo_alocacao):
    for item in form.itens_plano.entries:
        item.form.tipo_alocacao_id.choices = opcoes_tipo_alocacao


def _codigo_projeto(projeto):
    ano = projeto.vigencia_inicio.year
    mesmo_ano = (
        Projeto.query.filter(extract("year", Projeto.vigencia_inicio) == ano)
        .order_by(Projeto.id)
        .all()
    )
    numero = next((i + 1 for i, p in enumerate(mesmo_ano) if p.id == projeto.id), 1)
    return f"PRJ-{ano}-{numero:03d}"


@projetos_bp.route("/projetos")
@login_required
def listar_projetos():
    if current_user.papel == "administrador":
        projetos = Projeto.query.order_by(Projeto.nome).all()
    else:
        subquery_alocacoes = db.session.query(Alocacao.projeto_id).filter(
            Alocacao.usuario_id == current_user.id
        )
        projetos = (
            Projeto.query.filter(
                db.or_(
                    Projeto.id.in_(subquery_alocacoes),
                    Projeto.criado_por_id == current_user.id,
                )
            )
            .order_by(Projeto.nome)
            .all()
        )

    codigos = {p.id: _codigo_projeto(p) for p in projetos}
    return render_template("projetos/listar_projetos.html", projetos=projetos, codigos=codigos)


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


@projetos_bp.route("/projetos/solicitar", methods=["GET", "POST"])
@login_required
def solicitar_projeto():
    if current_user.papel == "administrador":
        flash("Administradores cadastram projetos diretamente, sem necessidade de aprovação.", "erro")
        return redirect(url_for("projetos.novo_projeto"))

    opcoes_tipo_alocacao = _opcoes_tipo_alocacao()
    mapa_categoria_padrao = _mapa_categoria_padrao()

    form = SolicitarProjetoForm()
    _preencher_opcoes_itens_plano(form, opcoes_tipo_alocacao)

    if form.validate_on_submit():
        projeto = Projeto(
            nome=form.nome.data,
            valor_total=form.valor_total.data,
            vigencia_inicio=form.vigencia_inicio.data,
            vigencia_fim=form.vigencia_fim.data,
            status="pendente_aprovacao",
            criado_por_id=current_user.id,
        )
        db.session.add(projeto)
        db.session.flush()

        for item in form.itens_plano.entries:
            alocacao = Alocacao(
                projeto_id=projeto.id,
                usuario_id=current_user.id,
                tipo_alocacao_id=item.form.tipo_alocacao_id.data,
                categoria=item.form.categoria.data,
                valor_alocado=item.form.valor_alocado.data,
                papel_projeto=item.form.papel_projeto.data,
            )
            db.session.add(alocacao)

        from app.notificacoes.servicos import notificar_administradores
        notificar_administradores(
            f'Novo projeto solicitado: "{projeto.nome}" por {current_user.nome}.',
            link=url_for("projetos.detalhe_projeto", projeto_id=projeto.id),
        )

        db.session.commit()
        flash("Projeto e plano de trabalho enviados para aprovação do administrador.", "sucesso")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    return render_template(
        "projetos/solicitar_projeto.html", form=form, opcoes_tipo_alocacao=opcoes_tipo_alocacao,
        mapa_categoria_padrao=mapa_categoria_padrao,
    )


@projetos_bp.route("/projetos/pendentes")
@login_required
def projetos_pendentes():
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projetos = Projeto.query.filter_by(status="pendente_aprovacao").order_by(Projeto.id).all()
    return render_template("projetos/projetos_pendentes.html", projetos=projetos)


@projetos_bp.route("/projetos/<int:projeto_id>/aprovar", methods=["POST"])
@login_required
def aprovar_projeto(projeto_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.projetos_pendentes"))

    if projeto.status != "pendente_aprovacao":
        flash("Este projeto não está aguardando aprovação.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    projeto.status = "ativo"
    projeto.motivo_reprovacao = None

    if projeto.criado_por_id:
        from app.notificacoes.servicos import notificar_usuario
        notificar_usuario(
            projeto.criado_por_id,
            f'Seu projeto "{projeto.nome}" foi aprovado.',
            link=url_for("projetos.detalhe_projeto", projeto_id=projeto.id),
        )

    db.session.commit()
    flash("Projeto aprovado com sucesso.", "sucesso")
    return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))


@projetos_bp.route("/projetos/<int:projeto_id>/reprovar", methods=["GET", "POST"])
@login_required
def reprovar_projeto(projeto_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.projetos_pendentes"))

    if projeto.status != "pendente_aprovacao":
        flash("Este projeto não está aguardando aprovação.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    form = ReprovarProjetoForm()
    if form.validate_on_submit():
        projeto.status = "reprovado"
        projeto.motivo_reprovacao = form.motivo_reprovacao.data

        if projeto.criado_por_id:
            from app.notificacoes.servicos import notificar_usuario
            notificar_usuario(
                projeto.criado_por_id,
                f'Seu projeto "{projeto.nome}" foi reprovado.',
                link=url_for("projetos.detalhe_projeto", projeto_id=projeto.id),
            )

        db.session.commit()
        flash("Projeto reprovado.", "sucesso")
        return redirect(url_for("projetos.projetos_pendentes"))

    return render_template("projetos/reprovar_projeto.html", form=form, projeto=projeto)


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


@projetos_bp.route("/projetos/<int:projeto_id>/instrucoes/enviar", methods=["GET", "POST"])
@login_required
def enviar_instrucoes(projeto_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    form = EnviarInstrucoesForm()
    if form.validate_on_submit():
        arquivo = form.arquivo.data
        extensao = arquivo.filename.rsplit(".", 1)[-1].lower()
        nome_arquivo = f"{uuid.uuid4().hex}.{extensao}"
        pasta = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(pasta, exist_ok=True)
        arquivo.save(os.path.join(pasta, nome_arquivo))

        projeto.arquivo_instrucoes = nome_arquivo
        projeto.instrucoes_nome_original = arquivo.filename
        db.session.commit()
        flash("Documento de instruções enviado.", "sucesso")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    return render_template("projetos/enviar_instrucoes.html", form=form, projeto=projeto)


@projetos_bp.route("/projetos/<int:projeto_id>/instrucoes")
@login_required
def ver_instrucoes(projeto_id):
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None or not projeto.arquivo_instrucoes:
        flash("Documento não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _pode_ver_projeto(projeto_id):
        flash("Você não tem acesso a este projeto.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    pasta = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(pasta, projeto.arquivo_instrucoes, download_name=projeto.instrucoes_nome_original)


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
    saldo_nao_alocado = projeto.valor_total - total_alocado

    total_despesas = (
        db.session.query(db.func.coalesce(db.func.sum(Despesa.valor), 0))
        .join(Alocacao)
        .filter(Alocacao.projeto_id == projeto.id, Despesa.status == "lancada")
        .scalar()
    )
    total_despesas = Decimal(total_despesas)

    saldo_disponivel = projeto.valor_total - total_despesas

    if total_alocado > 0:
        percentual_execucao = min(float((total_despesas / total_alocado) * 100), 100.0)
    else:
        percentual_execucao = 0.0

    grafico = {}
    for a in alocacoes:
        nome_tipo = a.tipo_alocacao.nome if a.tipo_alocacao else "Sem tipo definido"
        grafico[nome_tipo] = grafico.get(nome_tipo, Decimal("0")) + a.valor_alocado

    despesas_query = Despesa.query.join(Alocacao).filter(Alocacao.projeto_id == projeto.id).order_by(Despesa.data.desc())
    if current_user.papel != "administrador":
        despesas_query = despesas_query.filter(Alocacao.usuario_id == current_user.id)
    despesas = despesas_query.all()

    return render_template(
        "projetos/detalhe_projeto.html",
        projeto=projeto,
        codigo_projeto=_codigo_projeto(projeto),
        alocacoes=alocacoes,
        total_alocado=total_alocado,
        saldo_nao_alocado=saldo_nao_alocado,
        total_despesas=total_despesas,
        saldo_disponivel=saldo_disponivel,
        percentual_execucao=percentual_execucao,
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