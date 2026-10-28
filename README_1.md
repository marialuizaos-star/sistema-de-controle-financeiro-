# SCF PROPPI — Sistema de Controle Financeiro

Sistema web para controle financeiro de projetos de pesquisa da PROPPI/UFAC.
Stack: Python + Flask + PostgreSQL (SQLAlchemy/Alembic).

---

## 1. Requisitos do sistema

| Item | Versão |
|---|---|
| Python | **3.11 ou 3.12** (mínimo 3.9; evitar 3.13+ por causa do `psycopg2-binary==2.9.9`) |
| pip | 23+ |
| Git | qualquer versão recente |

### Bibliotecas Python (`requirements.txt`)

| Pacote | Versão | Uso |
|---|---|---|
| Flask | 3.1.3 | Framework web |
| Werkzeug | 3.1.3 | WSGI / hash de senha |
| Flask-SQLAlchemy | 3.1.1 | ORM |
| Flask-Migrate | 4.0.7 | Migrações (Alembic) |
| Flask-Login | 0.6.3 | Autenticação/sessão |
| Flask-WTF | 1.2.2 | Formulários + CSRF |
| email-validator | 2.2.0 | Validação de e-mail nos formulários |
| Flask-Mail | 0.10.0 | Envio de e-mail (recuperação de senha) |
| psycopg2-binary | 2.9.9 | Driver PostgreSQL |
| python-dotenv | 1.0.1 | Leitura do arquivo `.env` |
| reportlab | 4.2.5 | Geração de relatórios em PDF |

Para produção recomenda-se também um servidor WSGI (ex.: `gunicorn`) atrás de um proxy reverso (ex.: Nginx).

---

## 2. Banco de dados

- **SGBD indicado: PostgreSQL 14 ou superior** (desenvolvido e testado com PostgreSQL; versões 15/16 também atendem).
- Não há suporte testado para MySQL/MariaDB — a aplicação usa o driver `psycopg2`.
- Encoding do banco: **UTF8**.
- O esquema é criado/atualizado **exclusivamente via migrações** (`flask db upgrade`), que também populam dados iniciais (tipos de alocação padrão).

---

## 3. Variáveis de ambiente

Configuradas em um arquivo `.env` na raiz (modelo em `.env.example`). **Nunca versionar o `.env`.**

| Variável | Obrigatória | Descrição |
|---|---|---|
| `SECRET_KEY` | **Sim** (produção) | Chave de sessão/CSRF. Se ausente, é gerada aleatoriamente a cada reinício (derruba as sessões). Gerar com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | **Sim** | `postgresql://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO` |
| `FLASK_APP` | Sim (para comandos `flask`) | `run.py` |
| `MAIL_SERVER` | Não* | Servidor SMTP |
| `MAIL_PORT` | Não* | Porta SMTP (padrão `587`) |
| `MAIL_USE_TLS` | Não* | `true`/`false` (padrão `true`) |
| `MAIL_USERNAME` | Não* | Usuário SMTP |
| `MAIL_PASSWORD` | Não* | Senha SMTP |
| `MAIL_DEFAULT_SENDER` | Não* | Remetente dos e-mails |

\* Necessárias apenas para a função **"Recuperar senha"** por e-mail.

### Outras configurações (fixas em `app/config.py`)

- Uploads de comprovantes: gravados em `uploads/comprovantes/` na raiz do projeto — a pasta precisa existir e ter **permissão de escrita** para o usuário que roda a aplicação, e deve entrar na rotina de **backup** junto com o banco.
- Tamanho máximo de upload: 8 MB. Extensões aceitas: `pdf`, `png`, `jpg`, `jpeg`.

---

## 4. Procedimento de primeiro deploy

### 4.1. Banco de dados

```sql
-- no psql, como superusuário
CREATE USER scf_user WITH PASSWORD 'senha_forte';
CREATE DATABASE scf_propeg OWNER scf_user ENCODING 'UTF8';
```

### 4.2. Código e dependências

```bash
git clone https://github.com/marialuizaos-star/sistema-de-controle-financeiro-.git scf
cd scf
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4.3. Configuração

```bash
cp .env.example .env
# editar .env: SECRET_KEY, DATABASE_URL (e MAIL_* se for usar recuperação de senha)
echo "FLASK_APP=run.py" >> .env
mkdir -p uploads/comprovantes
```

### 4.4. Criar as tabelas (migrações)

```bash
flask db upgrade
```

### 4.5. Criar o primeiro administrador

```bash
flask shell
```
```python
from app.extensions import db
from app.models import Usuario
u = Usuario(nome="Administrador", email="admin@ufac.br", papel="administrador")
u.set_senha("TroqueEstaSenha123")
db.session.add(u); db.session.commit()
exit()
```
Trocar a senha no primeiro acesso.

### 4.6. Executar

Desenvolvimento:
```bash
python run.py                     # http://127.0.0.1:5000
```

Produção (Linux):
```bash
pip install gunicorn
gunicorn -w 3 -b 127.0.0.1:8000 run:app
```
Configurar o Nginx como proxy reverso para `127.0.0.1:8000`, com HTTPS e `client_max_body_size 8M;`.
Recomenda-se registrar o gunicorn como serviço `systemd`.

### 4.7. Atualizações futuras

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
# reiniciar o serviço da aplicação
```

---

## Contato

Dúvidas sobre o deploy: Maria Luiza — equipe de desenvolvimento (estágio PROPPI/UFAC).
