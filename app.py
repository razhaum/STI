import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import pytz
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_from_directory


app = Flask(__name__)

# Configurações básicas e sessão
app.secret_key = os.urandom(24)  # Usando uma chave secreta gerada aleatoriamente
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydaabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Inicializando banco de dados e migrações
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    sender = db.Column(db.String(100), nullable=False)
    sender_type = db.Column(db.String(50), nullable=False)  # 'user' ou 'admin'
    recipient = db.Column(db.String(100), nullable=True)  # Nome do destinatário
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.id}>'
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
    # Remover datahora, se não for mais necessário
    datahora = db.Column(db.DateTime, nullable=True)  # Nullable permite que o campo seja vazio
    horario_inicio = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Solicitacao {self.id}>'

# Criar as tabelas no banco de dados
with app.app_context():
    db.create_all()

    if not Usuario.query.filter_by(usuario='raphael').first():
        senha_hash = generate_password_hash('123')
        novo_usuario = Usuario(usuario='raphael', senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()

    if not Usuario.query.filter_by(usuario='admin').first():
        senha_hash = generate_password_hash('admin123')
        novo_usuario = Usuario(usuario='admin', senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()

# Rota inicial para login
@app.route("/", methods=['GET', 'POST'])
def login():
    # Verifica se o usuário já está logado
    if session.get('logged_in'):
        if session['permissao'] == 'admin':
            return redirect(url_for('solicitacoes'))  # Admin vai para solicitações
        return redirect(url_for('formulario'))  # Outros usuários vão para o formulário

    # Se o método for POST, faz o login
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        # Verificar se o usuário existe no banco de dados
        usuario_cadastrado = Usuario.query.filter_by(usuario=usuario).first()

        if usuario_cadastrado and check_password_hash(usuario_cadastrado.senha, senha):
            # Usuário logado com sucesso
            session['logged_in'] = True
            session['usuario'] = usuario
            session['permissao'] = usuario_cadastrado.permissao
            flash(f'Bem-vindo, {session["usuario"]}!', 'success')

            # Redireciona de acordo com a permissão do usuário
            if usuario == 'admin':
                return redirect(url_for('solicitacoes'))  # Admin vai para solicitações
            return redirect(url_for('formulario'))  # Para outros usuários, vai para o formulário

        flash('Usuário ou senha incorretos!')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/styles.css')
def serve_css():
    return send_from_directory('templates', 'styles.css')
# Inicialização do aplicativo
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
            datahora=datetime.now(pytz.timezone('America/Sao_Paulo')),  # Registra a data e hora atual no formato correto
            horario_inicio=datetime.now(pytz.timezone('America/Sao_Paulo'))  # Horário de início, pode ser o mesmo
        )
        db.session.add(nova_solicitacao)
        db.session.commit()
        return redirect(url_for("formulario"))

    return render_template("formulario.html")

# Página protegida - Listagem de solicitações
@app.route('/solicitacoes', methods=['GET', 'POST'])
def solicitacoes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    lista = Solicitacao.query.order_by(Solicitacao.id.desc()).all()
    usuarios_cadastrados = Usuario.query.all()
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


@app.route('/cadastrar_login', methods=['POST'])
def cadastrar_login():
    # Pegando os dados do formulário
    usuario = request.form['usuario']
    senha = request.form['senha']
    permissao = request.form['permissao']

    # Verificando se o usuário já existe no banco
    usuario_existente = Usuario.query.filter_by(usuario=usuario).first()
    if usuario_existente:
        # Caso o usuário já exista, você pode retornar uma mensagem de erro
        return "Usuário já existe. Tente novamente."

    # Criando um novo usuário e adicionando ao banco de dados
    novo_usuario = Usuario(usuario=usuario, senha=senha, permissao=permissao)

    try:
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('solicitacoes'))  # Redireciona para a página de solicitações
    except Exception as e:
        db.session.rollback()
        return f"Erro ao cadastrar usuário: {e}"
# Cadastro no solicitacoes
@app.route("/cadastro", methods=["POST"])
def cadastro():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    usuario = request.form["usuario"]
    senha = request.form["senha"]
    permissao = request.form["permissao"]

    # Verifica se o usuário já existe
    if Usuario.query.filter_by(usuario=usuario).first():
        flash('Usuário já existe! Escolha outro nome.')
        return redirect(url_for("solicitacoes"))

    # Hash da senha antes de salvar no banco
    senha_hash = generate_password_hash(senha)

    novo_usuario = Usuario(usuario=usuario, senha=senha_hash, permissao=permissao)
    db.session.add(novo_usuario)
    db.session.commit()

    flash('Cadastro realizado com sucesso!')
    return redirect(url_for("solicitacoes"))  # Redireciona para a página de solicitações


@app.route('/chat', methods=['GET'])
def chat():
    mensagens = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
    mensagens_json = [{"text": msg.text, "sender": msg.sender} for msg in mensagens]
    return jsonify({"messages": mensagens_json})



# Rota para servir arquivos carregados
@app.route('/uploads/<nome_arquivo>')
def uploaded_file(nome_arquivo):
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo)


@app.route('/enviar_mensagem', methods=['POST'])
def enviar_mensagem():
    data = request.get_json()  # Recebe o JSON enviado
    texto = data.get('text')   # Extrai o texto da mensagem
    if texto:
        # Cria a nova mensagem no banco de dados
        nova_mensagem = ChatMessage(text=texto, sender='user', sender_type='user')
        db.session.add(nova_mensagem)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False})

# Rota para enviar uma nova solicitação
@app.route('/enviar_solicitacao', methods=['POST'])
def enviar_solicitacao():
    # Recebe os dados do formulário
    setor = request.form['setor']
    qra = request.form['qra']
    solicitacao = request.form['solicitacao']
    prioridade = request.form['prioridade']
    imagem = request.files.get('imagem')  # Aqui é onde o arquivo de imagem é recebido

    if imagem and allowed_file(imagem.filename):  # Verifica se o arquivo é válido
        imagem_filename = secure_filename(imagem.filename)  # Garante que o nome do arquivo é seguro
        imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_filename))  # Salva o arquivo no diretório correto
    else:
        imagem_filename = None  # Caso não haja imagem ou o arquivo seja inválido

    # Criação da nova solicitação sem 'datahora' e 'horario_inicio'
    nova_solicitacao = Solicitacao(
        setor=setor,
        qra=qra,
        solicitacao=solicitacao,
        prioridade=prioridade,
        status="Pendente",  # Definindo o status como Pendente ou outro valor desejado
        imagem=imagem_filename,  # Salva o nome do arquivo ou None
        # Remova os campos 'datahora' e 'horario_inicio' da inserção
    )

    # Adiciona a solicitação ao banco de dados
    try:
        db.session.add(nova_solicitacao)
        db.session.commit()
        flash('Solicitação enviada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao salvar a solicitação: {e}', 'error')

    return redirect(url_for('listar_solicitacoes'))

# Rota para excluir um usuário
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

# Rodando a aplicação
if __name__ == "__main__":
    app.run(debug=True)
