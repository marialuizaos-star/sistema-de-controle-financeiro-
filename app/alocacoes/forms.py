from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, StringField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

CATEGORIAS = [
    ("custeio", "Custeio"),
    ("capital", "Capital"),
]


class AlocacaoForm(FlaskForm):
    usuario_id = SelectField("Usuário responsável", coerce=int, validators=[DataRequired()])
    tipo_alocacao_id = SelectField("Tipo de alocação", coerce=int, validators=[DataRequired()])
    categoria = SelectField("Categoria", choices=CATEGORIAS, validators=[DataRequired()])
    valor_alocado = DecimalField(
        "Valor alocado (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2
    )


class TipoAlocacaoForm(FlaskForm):
    nome = StringField("Nome do tipo de alocação", validators=[DataRequired(), Length(max=100)])
    categoria_padrao = SelectField("Categoria sugerida", choices=CATEGORIAS, validators=[DataRequired()])
    documentos_obrigatorios = TextAreaField(
        "Documentos obrigatórios (opcional)",
        validators=[Optional(), Length(max=500)],
    )


class MarcarProblemaAlocacaoForm(FlaskForm):
    """Usado pelo admin durante a revisão de um projeto pendente, pra
    sinalizar que uma alocação específica tem algo errado."""
    motivo = TextAreaField(
        "O que está errado nesta alocação",
        validators=[DataRequired(message="Descreva o que está errado."), Length(max=500)],
    )