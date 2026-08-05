from flask_wtf import FlaskForm
from wtforms import DecimalField, DateField, StringField, TextAreaField, SelectField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError

NATUREZAS = [
    ("custeio", "Custeio"),
    ("capital", "Capital"),
    ("devolucao", "Devolução"),
]

ASSINATURAS_ARQUIVO = {
    "pdf": (b"%PDF",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
}


def _validar_conteudo_comprovante(form, campo):
    arquivo = campo.data
    if not arquivo:
        return
    extensao = arquivo.filename.rsplit(".", 1)[-1].lower()
    assinaturas_validas = ASSINATURAS_ARQUIVO.get(extensao)
    if not assinaturas_validas:
        return
    cabecalho = arquivo.stream.read(8)
    arquivo.stream.seek(0)
    if not any(cabecalho.startswith(assinatura) for assinatura in assinaturas_validas):
        raise ValidationError(
            "O conteúdo do arquivo não corresponde a um PDF, PNG ou JPG válido. "
            "Verifique se o arquivo não está corrompido ou com a extensão trocada."
        )


class DespesaForm(FlaskForm):
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
        validators=[
            FileRequired(message="É obrigatório anexar um comprovante."),
            FileAllowed(["pdf", "png", "jpg", "jpeg"], "Envie um arquivo PDF, PNG ou JPG."),
            _validar_conteudo_comprovante,
        ],
    )


class EstornarDespesaForm(FlaskForm):
    """Motivo obrigatório ao estornar (decisão de 02/08/2026 — antes não pedia)."""
    motivo = TextAreaField(
        "Motivo do estorno", validators=[DataRequired(message="Informe o motivo do estorno."), Length(max=1000)]
    )


class ReprovarDespesaForm(FlaskForm):
    """Reprova a despesa (status diferente de estornar), com motivo obrigatório."""
    motivo = TextAreaField(
        "Motivo da reprovação", validators=[DataRequired(message="Informe o motivo da reprovação."), Length(max=1000)]
    )