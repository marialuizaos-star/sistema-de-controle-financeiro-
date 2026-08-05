from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError


class SolicitarRemanejamentoForm(FlaskForm):
    """Pedido de remanejamento de verba entre duas alocações do mesmo projeto.
    As opções de alocação de origem/destino são preenchidas na rota, restritas
    às alocações do projeto em questão."""
    alocacao_origem_id = SelectField("De (alocação de origem)", coerce=int, validators=[DataRequired()])
    alocacao_destino_id = SelectField("Para (alocação de destino)", coerce=int, validators=[DataRequired()])
    valor = DecimalField("Valor a remanejar (R$)", validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    justificativa = TextAreaField(
        "Justificativa", validators=[DataRequired(message="Informe a justificativa do remanejamento."), Length(max=1000)]
    )

    def validate_alocacao_destino_id(self, campo):
        if self.alocacao_origem_id.data is not None and campo.data == self.alocacao_origem_id.data:
            raise ValidationError("A alocação de destino deve ser diferente da de origem.")


class ReprovarRemanejamentoForm(FlaskForm):
    """Usado pelo administrador ao reprovar um pedido de remanejamento."""
    motivo_reprovacao = TextAreaField(
        "Motivo da reprovação (opcional)", validators=[Length(max=1000)]
    )