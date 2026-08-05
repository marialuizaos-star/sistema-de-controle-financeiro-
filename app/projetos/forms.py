from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField, TextAreaField, FieldList, FormField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired, NumberRange, ValidationError, Optional, Length

STATUS_PROJETO = [
    ("ativo", "Ativo"),
    ("inativo", "Inativo"),
    ("encerrado", "Encerrado"),
]

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


class ProjetoForm(FlaskForm):
    nome = StringField("Nome do projeto", validators=[DataRequired()])
    valor_total = DecimalField(
        "Valor total (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2
    )
    vigencia_inicio = DateField("Início da vigência", validators=[DataRequired()])
    vigencia_fim = DateField("Fim da vigência", validators=[DataRequired()])
    status = SelectField("Status", choices=STATUS_PROJETO, validators=[DataRequired()])

    def validate_vigencia_fim(self, campo):
        if self.vigencia_inicio.data and campo.data and campo.data < self.vigencia_inicio.data:
            raise ValidationError("A data de fim não pode ser anterior à data de início.")


class ItemPlanoTrabalhoForm(FlaskForm):
    class Meta:
        csrf = False

    papel_projeto = SelectField("Papel no projeto", choices=PAPEIS_PROJETO, validators=[DataRequired()])
    tipo_alocacao_id = SelectField("Tipo de alocação", coerce=int, validators=[DataRequired()])
    categoria = SelectField("Categoria", choices=CATEGORIAS, validators=[DataRequired()])
    valor_alocado = DecimalField("Valor (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2)


class SolicitarProjetoForm(FlaskForm):
    nome = StringField("Nome do projeto", validators=[DataRequired()])
    valor_total = DecimalField(
        "Valor total (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2
    )
    vigencia_inicio = DateField("Início da vigência", validators=[DataRequired()])
    vigencia_fim = DateField("Fim da vigência", validators=[DataRequired()])
    itens_plano = FieldList(FormField(ItemPlanoTrabalhoForm), min_entries=1)

    def validate_vigencia_fim(self, campo):
        if self.vigencia_inicio.data and campo.data and campo.data < self.vigencia_inicio.data:
            raise ValidationError("A data de fim não pode ser anterior à data de início.")

    def validate_itens_plano(self, campo):
        if len(campo.entries) == 0:
            raise ValidationError("Inclua ao menos um item no plano de trabalho.")

        total = sum((item.form.valor_alocado.data or 0) for item in campo.entries)
        if self.valor_total.data is not None and total > self.valor_total.data:
            raise ValidationError(
                f"A soma dos itens do plano (R$ {total:.2f}) não pode ultrapassar "
                f"o valor total do projeto (R$ {self.valor_total.data:.2f})."
            )


class ReprovarProjetoForm(FlaskForm):
    motivo_reprovacao = TextAreaField(
        "Motivo da reprovação (opcional)", validators=[Optional(), Length(max=1000)]
    )


class EnviarInstrucoesForm(FlaskForm):
    """Upload do documento de instruções do projeto, feito pelo administrador."""
    arquivo = FileField(
        "Documento de instruções (PDF, DOC ou DOCX)",
        validators=[
            FileRequired(message="Selecione um arquivo."),
            FileAllowed(["pdf", "doc", "docx"], "Envie um arquivo PDF, DOC ou DOCX."),
        ],
    )