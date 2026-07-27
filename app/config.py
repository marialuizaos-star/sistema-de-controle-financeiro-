import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Configuração da aplicação. Todos os valores sensíveis vêm de
    variáveis de ambiente (NRF03: credenciais fora do código versionado)."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-nao-usar-em-producao")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://usuario:senha@localhost:5432/scf_propeg"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pasta onde os comprovantes (imagem/PDF) são gravados em disco.
    # O caminho do arquivo é o que fica salvo em Comprovante.arquivo.
    UPLOAD_FOLDER = os.path.join(basedir, "uploads", "comprovantes")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB — ajustar conforme P08 for confirmado
    EXTENSOES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg"}
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")