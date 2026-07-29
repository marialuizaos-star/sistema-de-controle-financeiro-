from flask_wtf import FlaskForm
from wtforms import DecimalField, DateField, StringField, TextAreaField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired, NumberRange, Length, Optional


class DespesaForm(FlaskForm):
    data = DateField("Data da despesa", validators=[DataRequired()])
    valor = DecimalField("Valor (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2)
    fornecedor = StringField("Fornecedor", validators=[DataRequired(), Length(max=150)])
    descricao = TextAreaField("Descrição", validators=[Optional(), Length(max=1000)])
    comprovante = FileField(
        "Comprovante (PDF, PNG ou JPG)",
        validators=[FileRequired(message="É obrigatório anexar um comprovante."),
                    FileAllowed(["pdf", "png", "jpg", "jpeg"], "Envie um arquivo PDF, PNG ou JPG.")],
    )