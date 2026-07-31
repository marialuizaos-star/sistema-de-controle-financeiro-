from flask_wtf import FlaskForm
from wtforms import DecimalField, DateField, StringField, TextAreaField, SelectField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired, NumberRange, Length, Optional

NATUREZAS = [
    ("custeio", "Custeio"),
    ("capital", "Capital"),
    ("devolucao", "Devolução"),
]


class DespesaForm(FlaskForm):
    # Preenchido dinamicamente na rota, com as alocações que o usuário pode
    # lançar despesa (todas do projeto, se administrador; só as próprias, se não).
    alocacao_id = SelectField("Alocação", coerce=int, validators=[DataRequired()])

    data = DateField("Data da despesa", validators=[DataRequired()])
    natureza = SelectField("Natureza da despesa", choices=NATUREZAS, validators=[DataRequired()])
    valor = DecimalField("Valor (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2)
    fornecedor = StringField("Nome do favorecido", validators=[DataRequired(), Length(max=150)])
    cnpj_favorecido = StringField("CNPJ do favorecido", validators=[Optional(), Length(max=18)])
    numero_comprovante_fiscal = StringField("Número do comprovante fiscal", validators=[Optional(), Length(max=50)])
    descricao = TextAreaField("Descrição", validators=[Optional(), Length(max=1000)])
    comprovante = FileField(
        "Comprovante (PDF, PNG ou JPG)",
        validators=[FileRequired(message="É obrigatório anexar um comprovante."),
                    FileAllowed(["pdf", "png", "jpg", "jpeg"], "Envie um arquivo PDF, PNG ou JPG.")],
    )