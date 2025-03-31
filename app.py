import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import pytz
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)


# Configurações básicas e sessão
app.secret_key = os.urandom(24)  # Usando uma chave secreta gerada aleatoriamente
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modelos do banco de dados
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    senha = db.Column(db.String(120), nullable=False)
    permissao = db.Column(db.String(50), nullable=False, default='user')


class Solicitacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setor = db.Column(db.String(50))
    qra = db.Column(db.String(50))
    solicitacao = db.Column(db.Text)
    prioridade = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Pendente')
    imagem = db.Column(db.String(200))
    datahora = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone("America/Sao_Paulo")))
    horario_inicio = db.Column(db.DateTime, nullable=True)





# Criar as tabelas no banco de dados
with app.app_context():
    db.create_all()

    # Verificar se o usuário 'raphael' já existe
    if not Usuario.query.filter_by(usuario='raphael').first():
        senha_hash = generate_password_hash('123')  # Senha padrão
        novo_usuario = Usuario(usuario='raphael', senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()

    # Verificar se o usuário 'admin' já existe, caso contrário, criar
    if not Usuario.query.filter_by(usuario='admin').first():
        senha_hash = generate_password_hash('admin123')  # Senha do admin
        novo_usuario = Usuario(usuario='admin', senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()

# Rota inicial para login
@app.route("/", methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        if session.get('usuario') == 'admin':  # Se for admin, redireciona para solicitações
            return redirect(url_for('solicitacoes'))
        return redirect(url_for('formulario'))  # Se for usuário comum, vai para o formulário

    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        # Verificar se o usuário existe
        usuario_cadastrado = Usuario.query.filter_by(usuario=usuario).first()

        if usuario_cadastrado and check_password_hash(usuario_cadastrado.senha, senha):
            session['logged_in'] = True
            session['usuario'] = usuario

            session['permissao'] = 'admin' if (
            usuario == 'admin') else 'user'

            if usuario == 'admin':
                return redirect(url_for('solicitacoes'))  # Redireciona para a página de solicitações
            return redirect(url_for('formulario'))  # Para outros usuários, vai para o formulário

        flash('Usuário ou senha incorretos!')
        return redirect(url_for('login'))

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Página protegida - Formulário de solicitação
@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # Se não estiver logado, redireciona para o login

    if request.method == "POST":
        arquivo = request.files['imagem']
        nome_arquivo = None

        if arquivo and arquivo.filename != "":  # Verificar se o arquivo não é vazio
            if arquivo.mimetype.startswith('image/'):  # Verificar se o arquivo é uma imagem
                nome_arquivo = secure_filename(arquivo.filename)
                arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            else:
                flash('O arquivo enviado não é uma imagem válida!')
                return redirect(url_for('formulario'))

        nova_solicitacao = Solicitacao(
            setor=request.form['setor'],
            qra=request.form['qra'],
            solicitacao=request.form['solicitacao'],
            prioridade=request.form['prioridade'],
            status=request.form['status'],
            imagem=nome_arquivo,
            datahora=datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
        )
        db.session.add(nova_solicitacao)
        db.session.commit()
        return redirect(url_for("solicitacoes"))

    return render_template("formulario.html")

# Página protegida - Listagem de solicitações

@app.route("/solicitacoes")
def solicitacoes():
    if not session.get('logged_in') or session.get('usuario') != 'admin':
        return redirect(url_for('login'))  # Se não for admin, redireciona para o login

    lista = Solicitacao.query.order_by(Solicitacao.id.desc()).all()
    usuarios_cadastrados = Usuario.query.all()  # enviar usuários para a view
    return render_template("solicitacoes.html", solicitacoes=lista, usuarios=usuarios_cadastrados)


# Alteração de status de uma solicitação
@app.route('/alterar_status/<int:solicitacao_id>')
def alterar_status(solicitacao_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    solicitacao = Solicitacao.query.get_or_404(solicitacao_id)

    if solicitacao.status == 'Pendente':
        solicitacao.status = 'Em andamento'
    elif solicitacao.status == 'Em andamento':
        solicitacao.status = 'Concluído'
    elif solicitacao.status == 'Concluído':
        solicitacao.status = 'Pendente'

    db.session.commit()
    return redirect(url_for('solicitacoes'))

# Página de cadastro
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if session.get('logged_in'):
        return redirect(url_for('formulario'))  # Se já estiver logado, vai para o formulário

    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        # Verifica se o usuário já existe
        if Usuario.query.filter_by(usuario=usuario).first():
            flash('Usuário já existe! Escolha outro nome.')
            return redirect(url_for("cadastro"))

        # Hash da senha antes de salvar no banco
        senha_hash = generate_password_hash(senha)

        novo_usuario = Usuario(usuario=usuario, senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso!')
        return redirect(url_for("login"))

    return render_template("cadastro.html")

@app.route('/chat', methods=['GET'])
def chat():
    mensagens = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
    mensagens_json = [{"text": msg.text, "sender": msg.sender} for msg in mensagens]
    return jsonify({"messages": mensagens_json})

# Defina a classe ChatMessage primeiro
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    sender = db.Column(db.String(100), nullable=False)  # Nome do remetente
    sender_type = db.Column(db.String(50), nullable=False)  # 'user' ou 'admin'
    recipient = db.Column(db.String(100), nullable=True)  # Nome do destinatário
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.id}>'

# Rota para servir arquivos carregados
@app.route('/uploads/<nome_arquivo>')
def uploaded_file(nome_arquivo):
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo)

# Rota para enviar uma nova mensagem
@app.route('/enviar_mensagem', methods=['POST'])
def enviar_mensagem():
    data = request.get_json()
    text = data.get('text')
    sender = data.get('sender')  # Pode ser 'klisman' ou outro usuário
    sender_type = data.get('sender_type')  # 'user' ou 'admin'
    recipient = data.get('recipient')  # Apenas se for resposta de admin

    if not text or not sender or not sender_type:
        return jsonify({"success": False, "message": "Faltam dados obrigatórios!"}), 400

    # Salvar a mensagem no banco de dados
    nova_mensagem = ChatMessage(
        text=text,
        sender=sender,
        sender_type=sender_type,
        recipient=recipient if sender_type == 'admin' else None  # Apenas admins podem ter destinatário
    )
    db.session.add(nova_mensagem)
    db.session.commit()

    return jsonify({"success": True}), 200

@app.route('/cadastrar_login', methods=['POST'])
def cadastrar_login():
    usuario = request.form['usuario']
    senha = request.form['senha']
    permissao = request.form['permissao']

    # Verifique se já existe o usuário no banco
    usuario_existente = Usuario.query.filter_by(usuario=usuario).first()
    if usuario_existente:
        flash('Usuário já existe! Escolha outro nome.')
        return redirect(url_for('solicitacoes'))

    senha_hash = generate_password_hash(senha)

    novo_usuario = Usuario(usuario=usuario, senha=senha_hash)
    # Adicione lógica aqui se desejar salvar a permissão no banco (criar coluna permissao em Usuario)
    db.session.add(novo_usuario)
    db.session.commit()

    flash('Usuário cadastrado com sucesso!')
    return redirect(url_for('solicitacoes'))

@app.route('/excluir_usuario/<int:id_usuario>', methods=['POST'])
def excluir_usuario(id_usuario):
    if not session.get('logged_in') or session.get('usuario') != 'admin':
        flash('Permissão negada!')
        return redirect(url_for('login'))

    usuario = Usuario.query.get_or_404(id_usuario)

    if usuario.usuario == 'admin':
        flash('Você não pode excluir o administrador principal!')
        return redirect(url_for('solicitacoes'))

    db.session.delete(usuario)
    db.session.commit()

    flash('Usuário excluído com sucesso!')
    return redirect(url_for('solicitacoes'))


if __name__ == "__main__":
    app.run(debug=True)
