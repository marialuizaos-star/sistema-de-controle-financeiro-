from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

# ---------------------------------------------------------------------------
# NOTA IMPORTANTE (leia antes de mexer neste arquivo):
#
# Os campos abaixo seguem exatamente o Modelo de Dados da Figura 1 do
# documento de requisitos, com UMA adição: Usuario.senha_hash.
#
# O diagrama não tinha campo de senha, mas o RF01 exige "acesso mediante
# e-mail e senha" e o NRF03 exige que a senha seja armazenada com hash.
#
# Por causa do R3 / NRF04 (proibição de exclusão física de registros
# financeiros), nenhum relacionamento aqui usa exclusão em cascata no
# banco. "Remover" um Projeto, Alocação ou Despesa deve sempre significar
# mudar o campo `status`, nunca fazer DELETE.
# ---------------------------------------------------------------------------


def agora_utc():
    return datetime.now(timezone.utc)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    telefone = db.Column(db.String(20), nullable=True)
    papel = db.Column(db.String(20), nullable=False, default="usuario_externo")
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    senha_hash = db.Column(db.String(255), nullable=False)

    alocacoes = db.relationship("Alocacao", back_populates="usuario")

    # Perfis: Administrador (acesso total) e Usuário Externo (lança despesas,
    # anexa comprovantes e consulta relatórios), conforme o diagrama de casos de uso.
    PAPEIS_VALIDOS = ("administrador", "usuario_externo")

    def set_senha(self, senha_texto_puro):
        self.senha_hash = generate_password_hash(senha_texto_puro)

    def checar_senha(self, senha_texto_puro):
        return check_password_hash(self.senha_hash, senha_texto_puro)

    @property
    def is_active(self):
        return self.ativo

    def gerar_token_redefinicao(self):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps(self.email, salt="redefinicao-senha")

    @staticmethod
    def verificar_token_redefinicao(token, expira_em_segundos=3600):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            email = serializer.loads(token, salt="redefinicao-senha", max_age=expira_em_segundos)
        except Exception:
            return None
        return Usuario.query.filter_by(email=email).first()

    def __repr__(self):
        return f"<Usuario {self.id} {self.email}>"


class Projeto(db.Model):
    __tablename__ = "projeto"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False)
    vigencia_inicio = db.Column(db.Date, nullable=False)
    vigencia_fim = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="em_execucao")

    alocacoes = db.relationship("Alocacao", back_populates="projeto")

    STATUS_VALIDOS = ("em_execucao", "encerrado", "cancelado")

    __table_args__ = (
        db.CheckConstraint("valor_total >= 0", name="ck_projeto_valor_total_positivo"),
        db.CheckConstraint(
            "status IN ('em_execucao', 'encerrado', 'cancelado')",
            name="ck_projeto_status_valido",
        ),
    )

    def __repr__(self):
        return f"<Projeto {self.id} {self.nome}>"


class Alocacao(db.Model):
    __tablename__ = "alocacao"

    id = db.Column(db.Integer, primary_key=True)
    projeto_id = db.Column(db.Integer, db.ForeignKey("projeto.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    categoria = db.Column(db.String(10), nullable=False)
    valor_alocado = db.Column(db.Numeric(12, 2), nullable=False)

    projeto = db.relationship("Projeto", back_populates="alocacoes")
    usuario = db.relationship("Usuario", back_populates="alocacoes")
    despesas = db.relationship("Despesa", back_populates="alocacao")

    CATEGORIAS_VALIDAS = ("custeio", "capital")

    __table_args__ = (
        db.CheckConstraint("valor_alocado >= 0", name="ck_alocacao_valor_positivo"),
        db.CheckConstraint(
            "categoria IN ('custeio', 'capital')", name="ck_alocacao_categoria_valida"
        ),
    )

    def __repr__(self):
        return f"<Alocacao {self.id} projeto={self.projeto_id} usuario={self.usuario_id}>"


class Despesa(db.Model):
    __tablename__ = "despesa"

    id = db.Column(db.Integer, primary_key=True)
    alocacao_id = db.Column(db.Integer, db.ForeignKey("alocacao.id"), nullable=False)
    data = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    fornecedor = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="lancada")

    criado_em = db.Column(db.DateTime(timezone=True), default=agora_utc, nullable=False)

    alocacao = db.relationship("Alocacao", back_populates="despesas")
    comprovante = db.relationship(
        "Comprovante", back_populates="despesa", uselist=False
    )

    STATUS_VALIDOS = ("lancada", "estornada")

    __table_args__ = (
        db.CheckConstraint("valor >= 0", name="ck_despesa_valor_positivo"),
        db.CheckConstraint(
            "status IN ('lancada', 'estornada')", name="ck_despesa_status_valido"
        ),
    )

    def __repr__(self):
        return f"<Despesa {self.id} alocacao={self.alocacao_id} valor={self.valor}>"


class Comprovante(db.Model):
    __tablename__ = "comprovante"

    id = db.Column(db.Integer, primary_key=True)
    despesa_id = db.Column(
        db.Integer, db.ForeignKey("despesa.id"), nullable=False, unique=True
    )
    arquivo = db.Column(db.String(255), nullable=False)
    enviado_em = db.Column(db.DateTime(timezone=True), default=agora_utc, nullable=False)

    despesa = db.relationship("Despesa", back_populates="comprovante")

    def __repr__(self):
        return f"<Comprovante {self.id} despesa={self.despesa_id}>"