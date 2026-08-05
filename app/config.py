import os
import secrets

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Configuração da aplicação. Todos os valores sensíveis vêm de
    variáveis de ambiente (NRF03: credenciais fora do código-fonte versionado)."""

    # Antes, se SECRET_KEY não estivesse no .env, caía num valor fixo e
    # conhecido ("dev-key-nao-usar-em-producao") — qualquer pessoa com acesso
    # ao código-fonte (ex: repositório) saberia esse valor e poderia forjar
    # sessões de login válidas caso essa variável não fosse configurada em
    # produção por engano. Agora, na ausência da variável de ambiente, gera
    # um valor aleatório novo a cada vez que a aplicação inicia — isso invalida
    # sessões antigas a cada reinício (aceitável em desenvolvimento), mas
    # elimina o risco do valor fixo previsível. Configure SECRET_KEY no .env
    # pra manter sessões estáveis entre reinícios.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

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