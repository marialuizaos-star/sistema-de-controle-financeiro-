from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField
from wtforms.validators import DataRequired, NumberRange, ValidationError

STATUS_PROJETO = [
    ("em_execucao", "Em execução"),
    ("encerrado", "Encerrado"),
    ("cancelado", "Cancelado"),
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