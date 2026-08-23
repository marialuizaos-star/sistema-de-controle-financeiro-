from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, StringField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

CATEGORIAS = [
    ("custeio", "Custeio"),
    ("capital", "Capital"),
]

PAPEIS_PROJETO = [
    ("coordenador", "Coordenador"),
    ("pesquisador", "Pesquisador"),
    ("bolsista", "Bolsista"),
    ("tecnico", "Técnico"),
    ("colaborador", "Colaborador"),
]

class NovaAlocacaoPrincipalForm(FlaskForm):
    usuario_id = SelectField("Usuário responsável", coerce=int, validators=[DataRequired()])
    # Papel da pessoa dentro deste projeto (Coordenador, Pesquisador, etc.)
    # — é aqui que se pergunta isso, não no cadastro do projeto, já que a
    # mesma pessoa pode ter papéis diferentes em projetos diferentes.
    papel_projeto = SelectField("Papel no projeto (opcional)", choices=[("", "— Não informado —")] + PAPEIS_PROJETO, validators=[Optional()])
    centro_id = SelectField("Centro / Projeto (opcional)", coerce=int, validators=[Optional()])
    categoria = SelectField("Categoria da alocação", choices=CATEGORIAS, validators=[Optional()])
    valor_alocado = DecimalField(
        "Valor bruto destinado (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2
    )

class NovaSubAlocacaoForm(FlaskForm):
    tipo_alocacao_id = SelectField("Tipo de despesa", coerce=int, validators=[DataRequired()])
    valor_alocado = DecimalField(
        "Valor da sub-alocação (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2
    )

class EditarAlocacaoForm(FlaskForm):
    usuario_id = SelectField("Usuário responsável", coerce=int, validators=[Optional()])
    tipo_alocacao_id = SelectField("Tipo de despesa", coerce=int, validators=[Optional()])
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

class ReprovarAlocacaoForm(FlaskForm):
    motivo = TextAreaField(
        "Motivo da reprovação",
        validators=[DataRequired(message="Descreva o motivo da reprovação."), Length(max=500)],
    )

class CentroForm(FlaskForm):
    nome = StringField("Nome do centro / subprojeto", validators=[DataRequired(), Length(max=150)])