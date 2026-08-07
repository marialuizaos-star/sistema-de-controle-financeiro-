from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired, Length, Optional


class DocumentoModeloForm(FlaskForm):
    titulo = StringField("Título do documento", validators=[DataRequired(), Length(max=150)])
    descricao = TextAreaField("Descrição (opcional)", validators=[Optional(), Length(max=500)])
    arquivo = FileField(
        "Arquivo (PDF, DOC ou DOCX)",
        validators=[
            FileRequired(message="Selecione um arquivo."),
            FileAllowed(["pdf", "doc", "docx"], "Envie um arquivo PDF, DOC ou DOCX."),
        ],
    )