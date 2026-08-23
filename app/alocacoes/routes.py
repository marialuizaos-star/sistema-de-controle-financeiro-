from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Alocacao, Projeto, Usuario, TipoAlocacao, Despesa, Centro
from app.alocacoes.forms import (
    NovaAlocacaoPrincipalForm, NovaSubAlocacaoForm, EditarAlocacaoForm,
    TipoAlocacaoForm, ReprovarAlocacaoForm, CentroForm
)
from app.projetos.routes import _pode_ver_projeto, _codigo_projeto

alocacoes_bp = Blueprint("alocacoes", __name__, template_folder="../templates/alocacoes")


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


def _saldo_disponivel_projeto(projeto, alocacao_ignorar_id=None):
    query = Alocacao.query.filter_by(projeto_id=projeto.id, alocacao_pai_id=None)
    if alocacao_ignorar_id:
        query = query.filter(Alocacao.id != alocacao_ignorar_id)
    total_alocado = sum((a.valor_alocado for a in query.all()), Decimal("0"))
    return projeto.valor_total - total_alocado


def _saldo_disponivel_alocacao_principal(alocacao_pai, sub_alocacao_ignorar_id=None):
    query = Alocacao.query.filter_by(alocacao_pai_id=alocacao_pai.id)
    if sub_alocacao_ignorar_id:
        query = query.filter(Alocacao.id != sub_alocacao_ignorar_id)
    total_alocado = sum((a.valor_alocado for a in query.all()), Decimal("0"))
    return alocacao_pai.valor_alocado - total_alocado


@alocacoes_bp.route("/projetos/<int:projeto_id>/alocacoes/nova-principal", methods=["GET", "POST"])
@login_required
def nova_alocacao_principal(projeto_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    projeto_exige_categoria = projeto.categoria == "ambos"

    form = NovaAlocacaoPrincipalForm()
    form.usuario_id.choices = [
        (u.id, f"{u.nome} — {u.email}")
        for u in Usuario.query.filter_by(ativo=True).order_by(Usuario.nome).all()
    ]
    form.centro_id.choices = [(0, "— Nenhum —")] + [
        (c.id, c.nome) for c in Centro.query.filter_by(ativo=True).order_by(Centro.nome).all()
    ]

    saldo = _saldo_disponivel_projeto(projeto)

    if form.validate_on_submit():
        if projeto_exige_categoria and not form.categoria.data:
            flash("Este projeto tem verba de Custeio e Capital — escolha a categoria desta alocação.", "erro")
            return render_template(
                "alocacoes/nova_alocacao_principal.html", form=form, projeto=projeto, saldo=saldo,
                projeto_exige_categoria=projeto_exige_categoria,
            )

        if form.valor_alocado.data > saldo:
            flash(
                f"Valor acima do saldo disponível do projeto (R$ {saldo:.2f} restantes).",
                "erro",
            )
            return render_template(
                "alocacoes/nova_alocacao_principal.html", form=form, projeto=projeto, saldo=saldo,
                projeto_exige_categoria=projeto_exige_categoria,
            )

        categoria_alocacao = form.categoria.data if projeto_exige_categoria else projeto.categoria
        centro_escolhido = form.centro_id.data if form.centro_id.data else None
        papel_escolhido = form.papel_projeto.data if form.papel_projeto.data else None

        alocacao = Alocacao(
            projeto_id=projeto.id,
            usuario_id=form.usuario_id.data,
            centro_id=centro_escolhido,
            papel_projeto=papel_escolhido,
            categoria=categoria_alocacao,
            valor_alocado=form.valor_alocado.data,
            status="aprovada"
        )
        db.session.add(alocacao)

        from app.notificacoes.servicos import notificar_usuario
        notificar_usuario(
            alocacao.usuario_id,
            f'Foi destinada uma alocação de verba para você no projeto "{projeto.nome}".',
            link=url_for("alocacoes.detalhe_responsavel", projeto_id=projeto.id, usuario_id=alocacao.usuario_id),
        )

        db.session.commit()
        flash("Alocação cadastrada com sucesso.", "sucesso")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=projeto.id))

    return render_template(
        "alocacoes/nova_alocacao_principal.html", form=form, projeto=projeto, saldo=saldo,
        projeto_exige_categoria=projeto_exige_categoria,
    )


@alocacoes_bp.route("/alocacoes/<int:alocacao_pai_id>/sub/nova", methods=["GET", "POST"])
@login_required
def nova_sub_alocacao(alocacao_pai_id):
    alocacao_pai = db.session.get(Alocacao, alocacao_pai_id)
    if alocacao_pai is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if alocacao_pai.usuario_id != current_user.id and current_user.papel != "administrador":
        flash("Apenas o responsável por esta alocação pode criar novas alocações dentro dela.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao_pai.projeto_id))

    eh_admin = current_user.papel == "administrador"

    form = NovaSubAlocacaoForm()
    form.tipo_alocacao_id.choices = [
        (t.id, t.nome)
        for t in TipoAlocacao.query.filter_by(ativo=True).order_by(TipoAlocacao.nome).all()
        if t.categoria_padrao in (None, alocacao_pai.categoria)
    ]

    saldo = _saldo_disponivel_alocacao_principal(alocacao_pai)

    if form.validate_on_submit():
        if form.valor_alocado.data > saldo:
            flash(
                f"Valor acima do saldo disponível na alocação (R$ {saldo:.2f} restantes).",
                "erro",
            )
            return render_template(
                "alocacoes/nova_sub_alocacao.html", form=form, alocacao_pai=alocacao_pai, saldo=saldo
            )

        status_inicial = "aprovada" if eh_admin else "pendente"

        sub_alocacao = Alocacao(
            projeto_id=alocacao_pai.projeto_id,
            usuario_id=alocacao_pai.usuario_id,
            alocacao_pai_id=alocacao_pai.id,
            tipo_alocacao_id=form.tipo_alocacao_id.data,
            categoria=alocacao_pai.categoria,
            valor_alocado=form.valor_alocado.data,
            status=status_inicial,
        )
        db.session.add(sub_alocacao)

        if eh_admin:
            from app.notificacoes.servicos import notificar_usuario
            notificar_usuario(
                sub_alocacao.usuario_id,
                f'Foi criada uma nova alocação para você no projeto "{alocacao_pai.projeto.nome}".',
                link=url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao_pai.projeto_id, usuario_id=sub_alocacao.usuario_id),
            )
            flash("Alocação criada e já aprovada.", "sucesso")
        else:
            from app.notificacoes.servicos import notificar_administradores
            notificar_administradores(
                f'Nova alocação pendente no projeto "{alocacao_pai.projeto.nome}".',
                link=url_for("alocacoes.alocacoes_pendentes"),
            )
            flash("Alocação criada e enviada para aprovação do administrador.", "sucesso")

        db.session.commit()

        if eh_admin:
            return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao_pai.projeto_id))
        return redirect(url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao_pai.projeto_id, usuario_id=current_user.id))

    return render_template(
        "alocacoes/nova_sub_alocacao.html", form=form, alocacao_pai=alocacao_pai, saldo=saldo
    )


@alocacoes_bp.route("/projetos/<int:projeto_id>/responsavel/<int:usuario_id>")
@login_required
def detalhe_responsavel(projeto_id, usuario_id):
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if current_user.papel != "administrador" and current_user.id != usuario_id:
        flash("Você não tem permissão para ver esta página.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    responsavel = db.session.get(Usuario, usuario_id)
    if responsavel is None:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    alocacoes_principais = (
        Alocacao.query.filter_by(projeto_id=projeto.id, usuario_id=usuario_id, alocacao_pai_id=None)
        .order_by(Alocacao.id)
        .all()
    )

    todas_sub = []
    for a in alocacoes_principais:
        todas_sub.extend(a.sub_alocacoes)

    ids_alocacoes = [a.id for a in alocacoes_principais] + [s.id for s in todas_sub]
    despesas = (
        Despesa.query.filter(Despesa.alocacao_id.in_(ids_alocacoes)).order_by(Despesa.data.desc()).all()
        if ids_alocacoes else []
    )

    valor_total = sum((a.valor_alocado for a in alocacoes_principais), Decimal("0"))
    total_alocado = sum((s.valor_alocado for s in todas_sub), Decimal("0"))
    saldo_alocavel = valor_total - total_alocado
    total_empenhado = sum((d.valor for d in despesas if d.status == "lancada"), Decimal("0"))
    saldo_disponivel = valor_total - total_empenhado
    total_devolvido = sum(
        (d.valor for d in despesas if d.status == "lancada" and d.natureza == "devolucao"), Decimal("0")
    )

    total_alocacoes_usuario = len(alocacoes_principais) + len(todas_sub)

    grafico = {}
    for sub in todas_sub:
        if sub.tipo_alocacao:
            grafico[sub.tipo_alocacao.nome] = grafico.get(sub.tipo_alocacao.nome, Decimal("0")) + sub.valor_alocado

    return render_template(
        "alocacoes/detalhe_responsavel.html",
        projeto=projeto,
        codigo_projeto=_codigo_projeto(projeto),
        responsavel=responsavel,
        alocacoes_principais=alocacoes_principais,
        despesas=despesas,
        valor_total=valor_total,
        total_alocado=total_alocado,
        saldo_alocavel=saldo_alocavel,
        total_empenhado=total_empenhado,
        saldo_disponivel=saldo_disponivel,
        total_devolvido=total_devolvido,
        total_alocacoes_usuario=total_alocacoes_usuario,
        grafico_labels=list(grafico.keys()),
        grafico_valores=[float(v) for v in grafico.values()],
    )


@alocacoes_bp.route("/alocacoes/<int:alocacao_id>/editar", methods=["GET", "POST"])
@login_required
def editar_alocacao(alocacao_id):
    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    eh_admin = current_user.papel == "administrador"
    eh_dono = alocacao.usuario_id == current_user.id
    eh_nivel_1 = (alocacao.alocacao_pai_id is None and alocacao.tipo_alocacao_id is None)

    if not eh_admin and not (eh_dono and not eh_nivel_1):
        flash("Sem permissão para editar esta alocação.", "erro")
        return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))

    # Depois de aprovada, o dono não pode mais editar — mudar valor/tipo
    # nesse ponto contornaria a aprovação do administrador. O admin continua
    # podendo corrigir a qualquer momento, se necessário.
    if not eh_admin and alocacao.status == "aprovada":
        flash("Esta alocação já foi aprovada e não pode mais ser editada.", "erro")
        return redirect(url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=current_user.id))

    form = EditarAlocacaoForm(obj=alocacao)
    form.usuario_id.choices = [
        (u.id, f"{u.nome} — {u.email}")
        for u in Usuario.query.filter_by(ativo=True).order_by(Usuario.nome).all()
    ]
    form.tipo_alocacao_id.choices = [
        (t.id, t.nome)
        for t in TipoAlocacao.query.filter_by(ativo=True).order_by(TipoAlocacao.nome).all()
    ]

    if eh_nivel_1:
        saldo = _saldo_disponivel_projeto(alocacao.projeto, alocacao_ignorar_id=alocacao.id)
    else:
        if alocacao.alocacao_pai_id:
            saldo = _saldo_disponivel_alocacao_principal(alocacao.pai, sub_alocacao_ignorar_id=alocacao.id)
        else:
            saldo = _saldo_disponivel_projeto(alocacao.projeto, alocacao_ignorar_id=alocacao.id)

    if form.validate_on_submit():
        if form.valor_alocado.data > saldo:
            flash(
                f"Valor acima do saldo disponível (R$ {saldo:.2f} restantes).",
                "erro",
            )
            return render_template(
                "alocacoes/editar_alocacao.html", form=form, alocacao=alocacao,
                saldo=saldo, eh_nivel_1=eh_nivel_1
            )

        if eh_nivel_1 and eh_admin:
            alocacao.usuario_id = form.usuario_id.data
        elif not eh_nivel_1:
            alocacao.tipo_alocacao_id = form.tipo_alocacao_id.data
            if not eh_admin and alocacao.status == "reprovada":
                alocacao.status = "pendente"

        alocacao.valor_alocado = form.valor_alocado.data
        db.session.commit()
        flash("Alocação atualizada com sucesso.", "sucesso")

        if eh_admin:
            return redirect(url_for("projetos.detalhe_projeto", projeto_id=alocacao.projeto_id))
        return redirect(url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=current_user.id))

    return render_template(
        "alocacoes/editar_alocacao.html", form=form, alocacao=alocacao,
        saldo=saldo, eh_nivel_1=eh_nivel_1
    )


@alocacoes_bp.route("/alocacoes/pendentes")
@login_required
def alocacoes_pendentes():
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacoes = Alocacao.query.filter_by(status="pendente").order_by(Alocacao.usuario_id, Alocacao.id).all()

    agrupado = {}
    for a in alocacoes:
        grupo = agrupado.setdefault(a.usuario_id, {"usuario": a.usuario, "alocacoes": [], "total": Decimal("0")})
        grupo["alocacoes"].append(a)
        grupo["total"] += a.valor_alocado

    return render_template("alocacoes/alocacoes_pendentes.html", agrupado=agrupado)


@alocacoes_bp.route("/alocacoes/pendentes/usuario/<int:usuario_id>/aprovar-tudo", methods=["POST"])
@login_required
def aprovar_todas_pendentes(usuario_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    pendentes = Alocacao.query.filter_by(status="pendente", usuario_id=usuario_id).all()
    if pendentes:
        primeiro_projeto_id = pendentes[0].projeto_id
        for alocacao in pendentes:
            alocacao.status = "aprovada"
            alocacao.motivo_reprovacao = None

        from app.notificacoes.servicos import notificar_usuario
        notificar_usuario(
            usuario_id,
            f"{len(pendentes)} alocação(ões) sua(s) foram aprovadas.",
            link=url_for("alocacoes.detalhe_responsavel", projeto_id=primeiro_projeto_id, usuario_id=usuario_id),
        )

        db.session.commit()
        flash(f"{len(pendentes)} alocação(ões) aprovada(s) com sucesso.", "sucesso")

    return redirect(url_for("alocacoes.alocacoes_pendentes"))


@alocacoes_bp.route("/alocacoes/pendentes/usuario/<int:usuario_id>/reprovar-tudo", methods=["GET", "POST"])
@login_required
def reprovar_todas_pendentes(usuario_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    usuario = db.session.get(Usuario, usuario_id)
    pendentes = Alocacao.query.filter_by(status="pendente", usuario_id=usuario_id).order_by(Alocacao.id).all()
    if usuario is None or not pendentes:
        flash("Não há alocações pendentes para este usuário.", "erro")
        return redirect(url_for("alocacoes.alocacoes_pendentes"))

    form = ReprovarAlocacaoForm()
    if form.validate_on_submit():
        primeiro_projeto_id = pendentes[0].projeto_id
        for alocacao in pendentes:
            alocacao.status = "reprovada"
            alocacao.motivo_reprovacao = form.motivo.data

        from app.notificacoes.servicos import notificar_usuario
        notificar_usuario(
            usuario_id,
            f"{len(pendentes)} alocação(ões) sua(s) foram reprovadas: {form.motivo.data}",
            link=url_for("alocacoes.detalhe_responsavel", projeto_id=primeiro_projeto_id, usuario_id=usuario_id),
        )

        db.session.commit()
        flash(f"{len(pendentes)} alocação(ões) reprovada(s).", "sucesso")
        return redirect(url_for("alocacoes.alocacoes_pendentes"))

    return render_template(
        "alocacoes/reprovar_todas_pendentes.html", form=form, usuario=usuario, pendentes=pendentes
    )


@alocacoes_bp.route("/alocacoes/<int:alocacao_id>/aprovar", methods=["POST"])
@login_required
def aprovar_alocacao(alocacao_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao and alocacao.status == "pendente":
        alocacao.status = "aprovada"
        alocacao.motivo_reprovacao = None

        from app.notificacoes.servicos import notificar_usuario
        notificar_usuario(
            alocacao.usuario_id,
            f'Sua alocação em "{alocacao.projeto.nome}" foi aprovada.',
            link=url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=alocacao.usuario_id),
        )

        db.session.commit()
        flash("Alocação aprovada com sucesso.", "sucesso")

    return redirect(url_for("alocacoes.alocacoes_pendentes"))


@alocacoes_bp.route("/alocacoes/<int:alocacao_id>/reprovar", methods=["GET", "POST"])
@login_required
def reprovar_alocacao(alocacao_id):
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None or alocacao.status != "pendente":
        flash("Alocação não encontrada ou não está pendente.", "erro")
        return redirect(url_for("alocacoes.alocacoes_pendentes"))

    form = ReprovarAlocacaoForm()
    if form.validate_on_submit():
        alocacao.status = "reprovada"
        alocacao.motivo_reprovacao = form.motivo.data

        from app.notificacoes.servicos import notificar_usuario
        notificar_usuario(
            alocacao.usuario_id,
            f'Sua alocação em "{alocacao.projeto.nome}" foi reprovada.',
            link=url_for("alocacoes.detalhe_responsavel", projeto_id=alocacao.projeto_id, usuario_id=alocacao.usuario_id),
        )

        db.session.commit()
        flash("Alocação reprovada.", "sucesso")
        return redirect(url_for("alocacoes.alocacoes_pendentes"))

    return render_template("alocacoes/reprovar_alocacao.html", form=form, alocacao=alocacao)


@alocacoes_bp.route("/tipos-alocacao", methods=["GET", "POST"])
@login_required
def tipos_alocacao():
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

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
    if not _somente_administrador():
        return redirect(url_for("alocacoes.tipos_alocacao"))

    tipo = db.session.get(TipoAlocacao, tipo_id)
    if tipo is None:
        flash("Tipo de alocação não encontrado.", "erro")
    else:
        tipo.ativo = not tipo.ativo
        db.session.commit()
        flash("Tipo de alocação atualizado.", "sucesso")
    return redirect(url_for("alocacoes.tipos_alocacao"))


@alocacoes_bp.route("/centros", methods=["GET", "POST"])
@login_required
def gerenciar_centros():
    if not _somente_administrador():
        return redirect(url_for("projetos.listar_projetos"))

    form = CentroForm()
    if form.validate_on_submit():
        nome = form.nome.data.strip()
        if Centro.query.filter_by(nome=nome).first():
            flash("Esse centro já existe.", "erro")
        else:
            db.session.add(Centro(nome=nome, ativo=True))
            db.session.commit()
            flash("Centro adicionado.", "sucesso")
        return redirect(url_for("alocacoes.gerenciar_centros"))

    centros = Centro.query.order_by(Centro.nome).all()
    return render_template("alocacoes/centros.html", form=form, centros=centros)


@alocacoes_bp.route("/centros/<int:centro_id>/alternar-status", methods=["POST"])
@login_required
def alternar_status_centro(centro_id):
    if not _somente_administrador():
        return redirect(url_for("alocacoes.gerenciar_centros"))

    centro = db.session.get(Centro, centro_id)
    if centro is None:
        flash("Centro não encontrado.", "erro")
    else:
        centro.ativo = not centro.ativo
        db.session.commit()
        flash("Centro atualizado.", "sucesso")
    return redirect(url_for("alocacoes.gerenciar_centros"))