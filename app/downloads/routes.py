import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user

from app.extensions import db
from app.models import DocumentoModelo
from app.downloads.forms import DocumentoModeloForm

downloads_bp = Blueprint("downloads", __name__, template_folder="../templates/downloads")


def _somente_administrador():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return False
    return True


@downloads_bp.route("/downloads")
@login_required
def listar():
    documentos = DocumentoModelo.query.order_by(DocumentoModelo.titulo).all()
    form = DocumentoModeloForm()
    return render_template("downloads/listar.html", documentos=documentos, form=form)


@downloads_bp.route("/downloads/novo", methods=["POST"])
@login_required
def novo():
    if not _somente_administrador():
        return redirect(url_for("downloads.listar"))

    form = DocumentoModeloForm()
    if form.validate_on_submit():
        arquivo = form.arquivo.data
        extensao = arquivo.filename.rsplit(".", 1)[-1].lower()
        nome_arquivo = f"{uuid.uuid4().hex}.{extensao}"
        pasta = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(pasta, exist_ok=True)
        arquivo.save(os.path.join(pasta, nome_arquivo))

        db.session.add(DocumentoModelo(
            titulo=form.titulo.data,
            descricao=form.descricao.data,
            arquivo=nome_arquivo,
            nome_original=arquivo.filename,
        ))
        db.session.commit()
        flash("Documento adicionado à central de downloads.", "sucesso")
    else:
        for erros in form.errors.values():
            for erro in erros:
                flash(erro, "erro")

    return redirect(url_for("downloads.listar"))


@downloads_bp.route("/downloads/<int:documento_id>/arquivo")
@login_required
def baixar(documento_id):
    documento = db.session.get(DocumentoModelo, documento_id)
    if documento is None:
        flash("Documento não encontrado.", "erro")
        return redirect(url_for("downloads.listar"))

    pasta = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(pasta, documento.arquivo, download_name=documento.nome_original)


@downloads_bp.route("/downloads/<int:documento_id>/excluir", methods=["POST"])
@login_required
def excluir(documento_id):
    if not _somente_administrador():
        return redirect(url_for("downloads.listar"))

    documento = db.session.get(DocumentoModelo, documento_id)
    if documento is None:
        flash("Documento não encontrado.", "erro")
        return redirect(url_for("downloads.listar"))

    db.session.delete(documento)
    db.session.commit()
    flash("Documento removido.", "sucesso")
    return redirect(url_for("downloads.listar"))