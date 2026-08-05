from flask_wtf import FlaskForm
from wtforms import TextAreaField
from wtforms.validators import Optional, Length


class ReprovarPrestacaoContasForm(FlaskForm):
    """Usado pelo administrador ao reprovar a prestação de contas de um
    projeto — o solicitante corrige o necessário e pode reenviar depois."""
    motivo_reprovacao = TextAreaField(
        "Motivo da reprovação", validators=[Optional(), Length(max=1000)]
    )