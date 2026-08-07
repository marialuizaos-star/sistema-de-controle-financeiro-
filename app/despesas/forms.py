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


def _limpar_cnpj(valor):
    if valor is None:
        return valor
    return "".join(c for c in valor if c.isdigit())


def _validar_cnpj(form, campo):
    """CNPJ é opcional — só valida se algo foi digitado."""
    if not campo.data:
        return
    digitos = _limpar_cnpj(campo.data)
    if len(digitos) != 14:
        raise ValidationError("CNPJ deve ter 14 dígitos.")
    if digitos == digitos[0] * 14:
        raise ValidationError("CNPJ inválido.")

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(digitos[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if digito1 != int(digitos[12]):
        raise ValidationError("CNPJ inválido.")

    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(digitos[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if digito2 != int(digitos[13]):
        raise ValidationError("CNPJ inválido.")


class DespesaForm(FlaskForm):
    alocacao_id = SelectField("Alocação", coerce=int, validators=[DataRequired()])
    data = DateField("Data da despesa", validators=[DataRequired()])
    natureza = SelectField("Natureza da despesa", choices=NATUREZAS, validators=[DataRequired()])
    valor = DecimalField("Valor (R$)", validators=[DataRequired(), NumberRange(min=0)], places=2)
    fornecedor = StringField("Nome do favorecido", validators=[DataRequired(), Length(max=150)])
    cnpj_favorecido = StringField("CNPJ do favorecido", validators=[Optional(), Length(max=18), _validar_cnpj])
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
    motivo = TextAreaField(
        "Motivo do estorno", validators=[DataRequired(message="Informe o motivo do estorno."), Length(max=1000)]
    )


class ReprovarDespesaForm(FlaskForm):
    motivo = TextAreaField(
        "Motivo da reprovação", validators=[DataRequired(message="Informe o motivo da reprovação."), Length(max=1000)]
    )