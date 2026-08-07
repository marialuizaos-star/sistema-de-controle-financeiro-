from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


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
    departamento = db.Column(db.String(150), nullable=True)
    cpf = db.Column(db.String(14), nullable=True)
    ultimo_acesso = db.Column(db.DateTime(timezone=True), nullable=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    senha_provisoria = db.Column(db.Boolean, nullable=False, default=False)

    alocacoes = db.relationship("Alocacao", back_populates="usuario")

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
    status = db.Column(db.String(20), nullable=False, default="ativo")

    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    motivo_reprovacao = db.Column(db.Text, nullable=True)

    status_prestacao_contas = db.Column(db.String(20), nullable=True)
    motivo_reprovacao_prestacao = db.Column(db.Text, nullable=True)
    enviada_em_prestacao = db.Column(db.DateTime(timezone=True), nullable=True)
    arquivo_instrucoes = db.Column(db.String(255), nullable=True)
    instrucoes_nome_original = db.Column(db.String(255), nullable=True)

    alocacoes = db.relationship("Alocacao", back_populates="projeto")
    criado_por = db.relationship("Usuario")

    STATUS_VALIDOS = ("ativo", "inativo", "encerrado", "pendente_aprovacao", "reprovado")
    STATUS_PRESTACAO_VALIDOS = ("em_analise", "aceita", "reprovada")

    __table_args__ = (
        db.CheckConstraint("valor_total >= 0", name="ck_projeto_valor_total_positivo"),
        db.CheckConstraint(
            "status IN ('ativo', 'inativo', 'encerrado', 'pendente_aprovacao', 'reprovado')",
            name="ck_projeto_status_valido",
        ),
        db.CheckConstraint(
            "status_prestacao_contas IS NULL OR status_prestacao_contas IN "
            "('em_analise', 'aceita', 'reprovada')",
            name="ck_projeto_status_prestacao_contas_valido",
        ),
    )

    def __repr__(self):
        return f"<Projeto {self.id} {self.nome}>"


class TipoAlocacao(db.Model):
    __tablename__ = "tipo_alocacao"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    categoria_padrao = db.Column(db.String(10), nullable=True)

    # Texto livre exibido como alerta ao lançar despesa desse tipo — ex:
    # "Obrigatório anexar Relatório de Viagem ou Declaração de Diárias."
    # (novo RF — reunião de 02/08/2026). Opcional: se em branco, nenhum
    # aviso extra aparece além do upload de comprovante padrão.
    documentos_obrigatorios = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<TipoAlocacao {self.id} {self.nome}>"


class Alocacao(db.Model):
    __tablename__ = "alocacao"

    id = db.Column(db.Integer, primary_key=True)
    projeto_id = db.Column(db.Integer, db.ForeignKey("projeto.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    tipo_alocacao_id = db.Column(db.Integer, db.ForeignKey("tipo_alocacao.id"), nullable=True)
    categoria = db.Column(db.String(10), nullable=False)
    valor_alocado = db.Column(db.Numeric(12, 2), nullable=False)

    papel_projeto = db.Column(db.String(20), nullable=True)
    motivo_reprovacao = db.Column(db.Text, nullable=True)

    projeto = db.relationship("Projeto", back_populates="alocacoes")
    usuario = db.relationship("Usuario", back_populates="alocacoes")
    tipo_alocacao = db.relationship("TipoAlocacao")
    despesas = db.relationship("Despesa", back_populates="alocacao")

    CATEGORIAS_VALIDAS = ("custeio", "capital")
    PAPEIS_PROJETO_VALIDOS = ("coordenador", "pesquisador", "bolsista", "tecnico", "colaborador")

    __table_args__ = (
        db.CheckConstraint("valor_alocado >= 0", name="ck_alocacao_valor_positivo"),
        db.CheckConstraint(
            "categoria IN ('custeio', 'capital')", name="ck_alocacao_categoria_valida"
        ),
        db.CheckConstraint(
            "papel_projeto IS NULL OR papel_projeto IN "
            "('coordenador', 'pesquisador', 'bolsista', 'tecnico', 'colaborador')",
            name="ck_alocacao_papel_projeto_valido",
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

    natureza = db.Column(db.String(12), nullable=False, default="custeio")

    cnpj_favorecido = db.Column(db.String(18), nullable=True)
    numero_comprovante_fiscal = db.Column(db.String(50), nullable=True)

    motivo_status = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime(timezone=True), default=agora_utc, nullable=False)

    alocacao = db.relationship("Alocacao", back_populates="despesas")
    comprovante = db.relationship(
        "Comprovante", back_populates="despesa", uselist=False
    )

    STATUS_VALIDOS = ("lancada", "estornada", "reprovada")
    NATUREZAS_VALIDAS = ("custeio", "capital", "devolucao")

    __table_args__ = (
        db.CheckConstraint("valor >= 0", name="ck_despesa_valor_positivo"),
        db.CheckConstraint(
            "status IN ('lancada', 'estornada', 'reprovada')", name="ck_despesa_status_valido"
        ),
        db.CheckConstraint(
            "natureza IN ('custeio', 'capital', 'devolucao')", name="ck_despesa_natureza_valida"
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


class SolicitacaoRemanejamento(db.Model):
    __tablename__ = "solicitacao_remanejamento"

    id = db.Column(db.Integer, primary_key=True)
    projeto_id = db.Column(db.Integer, db.ForeignKey("projeto.id"), nullable=False)
    alocacao_origem_id = db.Column(db.Integer, db.ForeignKey("alocacao.id"), nullable=False)
    alocacao_destino_id = db.Column(db.Integer, db.ForeignKey("alocacao.id"), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendente")

    justificativa = db.Column(db.Text, nullable=True)
    motivo_reprovacao = db.Column(db.Text, nullable=True)

    solicitado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=agora_utc, nullable=False)

    projeto = db.relationship("Projeto")
    alocacao_origem = db.relationship("Alocacao", foreign_keys=[alocacao_origem_id])
    alocacao_destino = db.relationship("Alocacao", foreign_keys=[alocacao_destino_id])
    solicitado_por = db.relationship("Usuario")

    STATUS_VALIDOS = ("pendente", "aprovado", "reprovado")

    __table_args__ = (
        db.CheckConstraint("valor >= 0", name="ck_remanejamento_valor_positivo"),
        db.CheckConstraint(
            "status IN ('pendente', 'aprovado', 'reprovado')",
            name="ck_remanejamento_status_valido",
        ),
        db.CheckConstraint(
            "alocacao_origem_id != alocacao_destino_id",
            name="ck_remanejamento_origem_destino_diferentes",
        ),
    )

    def __repr__(self):
        return f"<SolicitacaoRemanejamento {self.id} projeto={self.projeto_id}>"


class Notificacao(db.Model):
    __tablename__ = "notificacao"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    mensagem = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=True)
    lida = db.Column(db.Boolean, nullable=False, default=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=agora_utc, nullable=False)

    usuario = db.relationship("Usuario")

    def __repr__(self):
        return f"<Notificacao {self.id} usuario={self.usuario_id} lida={self.lida}>"

class DocumentoModelo(db.Model):
    __tablename__ = "documento_modelo"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    arquivo = db.Column(db.String(255), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=agora_utc, nullable=False)

    def __repr__(self):
        return f"<DocumentoModelo {self.id} {self.titulo}>"