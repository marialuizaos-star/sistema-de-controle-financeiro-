from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo

from app.models import Usuario

PERFIS = [
    ("administrador", "Administrador"),
    ("usuario_externo", "Usuário Externo"),
]


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])
    lembrar = BooleanField("Manter conectado")


class CadastroUsuarioForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=150)])
    telefone = StringField("Telefone", validators=[Length(max=20)])
    papel = SelectField("Perfil de acesso", choices=PERFIS, validators=[DataRequired()])
    senha = PasswordField("Senha", validators=[DataRequired(), Length(min=8)])
    confirmar_senha = PasswordField(
        "Confirmar senha", validators=[DataRequired(), EqualTo("senha", message="As senhas não coincidem.")]
    )

    def validar_email_unico(self):
        """Chamar manualmente na rota (RF03: e-mail deve ser único)."""
        return Usuario.query.filter_by(email=self.email.data).first() is None


class SolicitarRecuperacaoForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])


class RedefinirSenhaForm(FlaskForm):
    senha = PasswordField("Nova senha", validators=[DataRequired(), Length(min=8)])
    confirmar_senha = PasswordField(
        "Confirmar nova senha", validators=[DataRequired(), EqualTo("senha", message="As senhas não coincidem.")]
    )


class EditarUsuarioForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=150)])
    telefone = StringField("Telefone", validators=[Length(max=20)])
    papel = SelectField("Perfil de acesso", choices=PERFIS, validators=[DataRequired()])