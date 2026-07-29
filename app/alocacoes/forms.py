from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, StringField
from wtforms.validators import DataRequired, NumberRange, Length

CATEGORIAS = [
    ("custeio", "Custeio"),
    ("capital", "Capital"),
]


class AlocacaoForm(FlaskForm):
    usuario_id = SelectField("Usuário responsável", coerce=int, validators=[DataRequired()])
    tipo_despesa_id = SelectField("Tipo de despesa", coerce=int, validators=[DataRequired()])
    categoria = SelectField("Categoria", choices=CATEGORIAS, validators=[DataRequired()])
    valor_alocado = DecimalField(
        "Valor alocado (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2
    )


class TipoDespesaForm(FlaskForm):
    nome = StringField("Nome do tipo de despesa", validators=[DataRequired(), Length(max=100)])