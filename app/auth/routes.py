from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message

from app.extensions import db, mail
from app.models import Usuario, Projeto, Alocacao, Despesa
from app.auth.forms import (
    LoginForm,
    CadastroUsuarioForm,
    SolicitarRecuperacaoForm,
    RedefinirSenhaForm,
    EditarUsuarioForm,
)

auth_bp = Blueprint("auth", __name__, template_folder="../templates")


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("auth.painel"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.painel"))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data).first()
        if usuario is None or not usuario.checar_senha(form.senha.data):
            flash("E-mail ou senha inválidos.", "erro")
            return redirect(url_for("auth.login"))
        if not usuario.ativo:
            flash("Este usuário está inativo. Procure o administrador.", "erro")
            return redirect(url_for("auth.login"))

        usuario.ultimo_acesso = datetime.now(timezone.utc)
        db.session.commit()

        login_user(usuario, remember=form.lembrar.data)
        return redirect(url_for("auth.painel"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


def _contagem_projetos_usuario(usuario):
    """Quantidade de projetos em que o usuário está envolvido: onde tem
    alocação, ou que ele mesmo solicitou o cadastro (mesmo sem alocação)."""
    ids_por_alocacao = {
        projeto_id for (projeto_id,) in
        db.session.query(Alocacao.projeto_id).filter(Alocacao.usuario_id == usuario.id).all()
    }
    ids_criados = {
        projeto_id for (projeto_id,) in
        db.session.query(Projeto.id).filter(Projeto.criado_por_id == usuario.id).all()
    }
    return len(ids_por_alocacao | ids_criados)


def _contexto_listar_usuarios(form_cadastro=None, abrir_cadastro=False):
    """Monta todo o contexto usado por auth/listar_usuarios.html. Centralizado
    aqui porque duas rotas precisam renderizar essa mesma tela: a listagem
    normal (GET /usuarios) e o cadastro quando falha a validação (POST
    /cadastro), já que o formulário agora vive embutido nesta página."""
    administradores = Usuario.query.filter_by(papel="administrador").order_by(Usuario.nome).all()
    externos = Usuario.query.filter_by(papel="usuario_externo").order_by(Usuario.nome).all()
    contagem_projetos = {
        u.id: _contagem_projetos_usuario(u) for u in administradores + externos
    }
    total_ativos = sum(1 for u in administradores + externos if u.ativo)

    return {
        "administradores": administradores,
        "externos": externos,
        "contagem_projetos": contagem_projetos,
        "total_ativos": total_ativos,
        "form_cadastro": form_cadastro or CadastroUsuarioForm(),
        "abrir_cadastro": abrir_cadastro,
    }


@auth_bp.route("/cadastro", methods=["GET", "POST"])
@login_required
def cadastro():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para cadastrar usuários.", "erro")
        return redirect(url_for("auth.painel"))

    if request.method == "GET":
        # O formulário de cadastro agora vive embutido em /usuarios; não há
        # mais uma página avulsa pra exibir aqui.
        return redirect(url_for("auth.listar_usuarios"))

    form = CadastroUsuarioForm()
    if form.validate_on_submit():
        if not form.validar_email_unico():
            form.email.errors.append("Já existe um usuário com este e-mail.")
            return render_template(
                "auth/listar_usuarios.html",
                **_contexto_listar_usuarios(form_cadastro=form, abrir_cadastro=True),
            )

        novo_usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            telefone=form.telefone.data,
            departamento=form.departamento.data,
            papel=form.papel.data,
        )
        novo_usuario.set_senha(form.senha.data)
        db.session.add(novo_usuario)
        db.session.commit()
        flash("Usuário cadastrado com sucesso.", "sucesso")
        return redirect(url_for("auth.listar_usuarios"))

    # Validação falhou (ex: senha curta, e-mail inválido): reabre a tela de
    # Usuários com o painel de cadastro já expandido e os erros marcados.
    return render_template(
        "auth/listar_usuarios.html",
        **_contexto_listar_usuarios(form_cadastro=form, abrir_cadastro=True),
    )


def _resumo_painel_geral():
    """Monta o consolidado do painel geral (só projetos com status Ativo):
    total administrado, total gasto, saldo geral e o detalhamento por projeto."""
    from decimal import Decimal

    projetos_ativos = Projeto.query.filter_by(status="ativo").order_by(Projeto.nome).all()

    total_administrado = sum((p.valor_total for p in projetos_ativos), Decimal("0"))
    total_gasto_geral = Decimal("0")
    resumo_projetos = []

    for projeto in projetos_ativos:
        total_gasto_projeto = (
            db.session.query(db.func.coalesce(db.func.sum(Despesa.valor), 0))
            .join(Alocacao)
            .filter(Alocacao.projeto_id == projeto.id, Despesa.status == "lancada")
            .scalar()
        )
        total_gasto_projeto = Decimal(total_gasto_projeto)
        total_gasto_geral += total_gasto_projeto
        resumo_projetos.append({
            "projeto": projeto,
            "valor_total": projeto.valor_total,
            "total_gasto": total_gasto_projeto,
            "saldo": projeto.valor_total - total_gasto_projeto,
        })

    saldo_geral = total_administrado - total_gasto_geral

    return {
        "total_administrado": total_administrado,
        "total_gasto_geral": total_gasto_geral,
        "saldo_geral": saldo_geral,
        "resumo_projetos": resumo_projetos,
    }


@auth_bp.route("/painel")
@login_required
def painel():
    painel_geral = None
    projetos = None

    if current_user.papel == "administrador":
        painel_geral = _resumo_painel_geral()
    else:
        projetos = (
            Projeto.query.join(Alocacao)
            .filter(Alocacao.usuario_id == current_user.id)
            .distinct()
            .order_by(Projeto.id.desc())
            .limit(5)
            .all()
        )

    return render_template("auth/painel.html", projetos=projetos, painel_geral=painel_geral)


@auth_bp.route("/recuperar-senha", methods=["GET", "POST"])
def recuperar_senha():
    form = SolicitarRecuperacaoForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data).first()
        if usuario:
            token = usuario.gerar_token_redefinicao()
            link = url_for("auth.redefinir_senha", token=token, _external=True)
            msg = Message(
                subject="Redefinição de senha — SCF PROPEG",
                recipients=[usuario.email],
                body=f"Olá, {usuario.nome}.\n\nPara redefinir sua senha, acesse o link abaixo (válido por 1 hora):\n{link}\n\nSe você não solicitou isso, ignore este e-mail.",
            )
            mail.send(msg)
        flash("Se o e-mail existir em nosso sistema, um link de redefinição foi enviado.", "sucesso")
        return redirect(url_for("auth.login"))
    return render_template("auth/recuperar_senha.html", form=form)


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    usuario = Usuario.verificar_token_redefinicao(token)
    if usuario is None:
        flash("Link inválido ou expirado. Solicite a redefinição novamente.", "erro")
        return redirect(url_for("auth.recuperar_senha"))

    form = RedefinirSenhaForm()
    if form.validate_on_submit():
        usuario.set_senha(form.senha.data)
        db.session.commit()
        flash("Senha redefinida com sucesso. Faça login com a nova senha.", "sucesso")
        return redirect(url_for("auth.login"))
    return render_template("auth/redefinir_senha.html", form=form)


@auth_bp.route("/usuarios")
@login_required
def listar_usuarios():
    if not _somente_administrador():
        return redirect(url_for("auth.painel"))
    return render_template("auth/listar_usuarios.html", **_contexto_listar_usuarios())


@auth_bp.route("/usuarios/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
def editar_usuario(usuario_id):
    if not _somente_administrador():
        return redirect(url_for("auth.painel"))

    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("auth.listar_usuarios"))

    form = EditarUsuarioForm(obj=usuario)
    if form.validate_on_submit():
        email_existente = Usuario.query.filter(
            Usuario.email == form.email.data, Usuario.id != usuario.id
        ).first()
        if email_existente:
            flash("Já existe outro usuário com este e-mail.", "erro")
            return render_template("auth/editar_usuario.html", form=form, usuario=usuario)

        usuario.nome = form.nome.data
        usuario.email = form.email.data
        usuario.telefone = form.telefone.data
        usuario.departamento = form.departamento.data
        usuario.papel = form.papel.data
        db.session.commit()
        flash("Usuário atualizado com sucesso.", "sucesso")
        return redirect(url_for("auth.listar_usuarios"))

    return render_template("auth/editar_usuario.html", form=form, usuario=usuario)


@auth_bp.route("/usuarios/<int:usuario_id>/alternar-status", methods=["POST"])
@login_required
def alternar_status_usuario(usuario_id):
    if not _somente_administrador():
        return redirect(url_for("auth.painel"))

    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("auth.listar_usuarios"))

    if usuario.id == current_user.id:
        flash("Você não pode inativar o seu próprio usuário.", "erro")
        return redirect(url_for("auth.listar_usuarios"))

    usuario.ativo = not usuario.ativo
    db.session.commit()
    flash(
        f"Usuário {'reativado' if usuario.ativo else 'inativado'} com sucesso.",
        "sucesso",
    )
    return redirect(url_for("auth.listar_usuarios"))


@auth_bp.route("/usuarios/<int:usuario_id>/excluir", methods=["POST"])
@login_required
def excluir_usuario(usuario_id):
    if not _somente_administrador():
        return redirect(url_for("auth.painel"))

    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("auth.listar_usuarios"))

    if Alocacao.query.filter_by(usuario_id=usuario.id).first():
        flash("Este usuário tem alocações vinculadas e não pode ser excluído. Inative-o em vez disso.", "erro")
        return redirect(url_for("auth.editar_usuario", usuario_id=usuario.id))

    if usuario.papel == "administrador":
        outros_admins = Usuario.query.filter(
            Usuario.papel == "administrador", Usuario.id != usuario.id, Usuario.ativo == True
        ).count()
        if outros_admins == 0:
            flash("Não é possível excluir o único administrador ativo do sistema.", "erro")
            return redirect(url_for("auth.editar_usuario", usuario_id=usuario.id))

    excluindo_a_si_mesmo = usuario.id == current_user.id
    db.session.delete(usuario)
    db.session.commit()

    if excluindo_a_si_mesmo:
        logout_user()
        flash("Sua conta foi excluída.", "sucesso")
        return redirect(url_for("auth.login"))

    flash("Usuário excluído com sucesso.", "sucesso")
    return redirect(url_for("auth.listar_usuarios"))