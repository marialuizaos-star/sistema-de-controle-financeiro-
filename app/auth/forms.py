from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, ValidationError

from app.models import Usuario

PERFIS = [
    ("administrador", "Administrador"),
    ("usuario_externo", "Usuário Externo"),
]


def remover_espacos(valor):
    if valor is not None and hasattr(valor, "strip"):
        return valor.strip()
    return valor


def _limpar_cpf(valor):
    if valor is None:
        return valor
    return "".join(c for c in valor if c.isdigit())


def _validar_cpf(form, campo):
    if not campo.data:
        return
    digitos = _limpar_cpf(campo.data)
    if len(digitos) != 11:
        raise ValidationError("CPF deve ter 11 dígitos.")
    if digitos == digitos[0] * 11:
        raise ValidationError("CPF inválido.")

    soma = sum(int(digitos[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    digito1 = 0 if resto == 10 else resto
    if digito1 != int(digitos[9]):
        raise ValidationError("CPF inválido.")

    soma = sum(int(digitos[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    digito2 = 0 if resto == 10 else resto
    if digito2 != int(digitos[10]):
        raise ValidationError("CPF inválido.")


class LoginForm(FlaskForm):
    email = StringField("E-mail", filters=[remover_espacos], validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])
    lembrar = BooleanField("Manter conectado")


class CadastroUsuarioForm(FlaskForm):
    nome = StringField("Nome completo", filters=[remover_espacos], validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail institucional", filters=[remover_espacos], validators=[DataRequired(), Email(), Length(max=150)])
    telefone = StringField("Telefone", filters=[remover_espacos], validators=[Length(max=20)])
    cpf = StringField("CPF", filters=[remover_espacos], validators=[DataRequired(message="Informe o CPF."), _validar_cpf])
    departamento = StringField("Departamento / Centro", filters=[remover_espacos], validators=[Optional(), Length(max=150)])
    papel = SelectField("Perfil de acesso", choices=PERFIS, validators=[DataRequired()])
    senha = PasswordField("Senha", validators=[DataRequired(), Length(min=8)])
    confirmar_senha = PasswordField(
        "Confirmar senha", validators=[DataRequired(), EqualTo("senha", message="As senhas não coincidem.")]
    )

    def validar_email_unico(self):
        return Usuario.query.filter_by(email=self.email.data).first() is None

    def validar_cpf_unico(self):
        digitos = _limpar_cpf(self.cpf.data)
        existente = Usuario.query.all()
        return not any(_limpar_cpf(u.cpf) == digitos for u in existente if u.cpf)


class SolicitarRecuperacaoForm(FlaskForm):
    email = StringField("E-mail", filters=[remover_espacos], validators=[DataRequired(), Email()])


class RedefinirSenhaForm(FlaskForm):
    senha = PasswordField("Nova senha", validators=[DataRequired(), Length(min=8)])
    confirmar_senha = PasswordField(
        "Confirmar nova senha", validators=[DataRequired(), EqualTo("senha", message="As senhas não coincidem.")]
    )


class TrocarSenhaObrigatoriaForm(FlaskForm):
    """Usado no primeiro acesso, quando o usuário ainda está com a senha
    provisória definida pelo administrador."""
    senha_atual = PasswordField("Senha atual (provisória)", validators=[DataRequired()])
    nova_senha = PasswordField("Nova senha", validators=[DataRequired(), Length(min=8)])
    confirmar_senha = PasswordField(
        "Confirmar nova senha", validators=[DataRequired(), EqualTo("nova_senha", message="As senhas não coincidem.")]
    )


class EditarUsuarioForm(FlaskForm):
    nome = StringField("Nome completo", filters=[remover_espacos], validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail institucional", filters=[remover_espacos], validators=[DataRequired(), Email(), Length(max=150)])
    telefone = StringField("Telefone", filters=[remover_espacos], validators=[Length(max=20)])
    cpf = StringField("CPF", filters=[remover_espacos], validators=[DataRequired(message="Informe o CPF."), _validar_cpf])
    departamento = StringField("Departamento / Centro", filters=[remover_espacos], validators=[Optional(), Length(max=150)])
    papel = SelectField("Perfil de acesso", choices=PERFIS, validators=[DataRequired()])