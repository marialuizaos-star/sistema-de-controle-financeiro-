from app.extensions import db
from app.models import Notificacao, Usuario


def notificar_usuario(usuario_id, mensagem, link=None):
    """Cria uma notificação pra um usuário específico. Não faz commit —
    quem chama essa função já está dentro de uma operação maior (aprovar
    projeto, criar remanejamento etc.) que faz seu próprio commit em seguida,
    então a notificação entra na mesma transação."""
    notificacao = Notificacao(usuario_id=usuario_id, mensagem=mensagem, link=link)
    db.session.add(notificacao)


def notificar_administradores(mensagem, link=None):
    """Cria uma notificação pra todos os administradores ativos do sistema."""
    admins = Usuario.query.filter_by(papel="administrador", ativo=True).all()
    for admin in admins:
        notificar_usuario(admin.id, mensagem, link)