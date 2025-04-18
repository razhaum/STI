from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import pytz
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
import sqlite3



app = Flask(__name__)

# Configurações básicas e sessão
app.secret_key = os.urandom(24)  # Usando uma chave secreta gerada aleatoriamente
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sua-chave'


UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
fuso_sp = pytz.timezone('America/Sao_Paulo')


# Inicializando banco de dados e migrações
db = SQLAlchemy(app)
migrate = Migrate(app, db)
##socketio = SocketIO(app)



class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(100), nullable=False)
    sender_type = db.Column(db.String(50), nullable=False)  # 'user' ou 'admin'
    text = db.Column(db.Text, nullable=False)  # Uma única definição correta aqui
    recipient = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(fuso_sp))

    def __repr__(self):
        return f"<ChatMessage {self.sender}: {self.text}>"




# Modelos do banco de dados
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    senha = db.Column(db.String(120), nullable=False)
    permissao = db.Column(db.String(50), nullable=False, default='user')

class Solicitacao(db.Model):
    __tablename__ = 'solicitacao'
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
    datahora_fim = db.Column(db.DateTime, nullable=True)
    atendente = db.Column(db.String(100), nullable=True)

    # Função fora da classe para criar usuarios iniciais
    def __repr__(self):
        return f'<Solicitacao {self.id}>'


# Criando usuarios iniciais automaticamente no banco
def criar_usuarios_iniciais():
    if not Usuario.query.filter_by(usuario='raphael').first():
        novo_usuario = Usuario(usuario='raphael', senha=generate_password_hash('123'), permissao='user')
        db.session.add(novo_usuario)

    if not Usuario.query.filter_by(usuario='admin').first():
        novo_admin = Usuario(usuario='admin', senha=generate_password_hash('admin123'), permissao='admin')
        db.session.add(novo_admin)

    db.session.commit()
    print("✔️ Usuários iniciais foram adicionados.")


    with app.app_context():
        db.create_all()  # Cria explicitamente as tabelas se não existirem ainda
        criar_usuarios_iniciais()  # Usuários iniciais garantidos agora!


@app.route('/home_user')
def home_user():
    if session.get('logged_in') and session.get('permissao') == 'user':
        return render_template('home_user.html', usuario=session['usuario'])
    else:
        flash('Acesso negado. Faça login como usuário.', 'warning')
        return redirect(url_for('login'))
# Rota inicial para login
@app.route("/", methods=['GET', 'POST'])
def login():
    # Verifica se o usuário já está logado
    if session.get('logged_in'):
        if session['permissao'] == 'admin':
            return redirect(url_for('solicitacoes'))
        elif session['permissao'] == 'user':
            return redirect(url_for('home_user'))
        else:
            session.clear()
            flash('Permissão inválida!', 'danger')
            return redirect(url_for('login'))
    # Outros usuários vão para o formulário

    # Se o método for POST, faz o login
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        # Verificar se o usuário existe no banco de dados
        usuario_cadastrado = Usuario.query.filter_by(usuario=usuario).first()

        if usuario_cadastrado and check_password_hash(usuario_cadastrado.senha, senha):
            # Usuário logado com sucesso
            session.clear()
            session['logged_in'] = True
            session['usuario'] = usuario_cadastrado.usuario
            session['permissao'] = usuario_cadastrado.permissao
            session['qra_usuario'] = usuario_cadastrado.usuario


            flash(f'Bem-vindo, {session["usuario"]}!', 'success')

            # Redireciona de acordo com a permissão do usuário
            if session['permissao'] == 'admin':
                return redirect(url_for('solicitacoes'))
            else:
                return redirect(url_for('home_user'))  # Para outros usuários, vai para o formulário

        flash('Usuário ou senha incorretos!')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/styles.css')
def serve_css():
    return send_from_directory('templates', 'styles.css')

@app.route('/')
def index():
    return render_template('index')  # O arquivo HTML deve estar na pasta templates
# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Sessão encerrada. Faça login novamente!', 'success')

    return redirect(url_for('login'))

# Página protegida - Formulário de solicitação
@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == "POST":
        arquivo = request.files['imagem']
        nome_arquivo = None

        if arquivo and arquivo.filename != "":
            if arquivo.mimetype.startswith('image/'):
                nome_arquivo = secure_filename(arquivo.filename)
                arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            else:
                flash('O arquivo enviado não é uma imagem válida!', 'error')
                return redirect(url_for('formulario'))

        nova_solicitacao = Solicitacao(
            setor=request.form['setor'],
            qra=request.form['qra'],
            solicitacao=request.form['solicitacao'],
            prioridade=request.form['prioridade'],
            status=request.form['status'],
            imagem=nome_arquivo,
            datahora=datetime.now(pytz.timezone('America/Sao_Paulo')),
            horario_inicio=datetime.now(pytz.timezone('America/Sao_Paulo'))
        )

        try:
            db.session.add(nova_solicitacao)
            db.session.commit()
            dados_da_solicitacao = {
                'id': nova_solicitacao.id,
                'setor': nova_solicitacao.setor,
                'qra': nova_solicitacao.qra,
                'solicitacao': nova_solicitacao.solicitacao,
                'prioridade': nova_solicitacao.prioridade,
                'status': nova_solicitacao.status,
                'datahora': nova_solicitacao.datahora.strftime('%Y-%m-%d %H:%M:%S')
            }



            flash('Solicitação enviada com sucesso!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao enviar a solicitação: {e}', 'error')

        return redirect(url_for("formulario"))

    return render_template('formulario.html')



# Página protegida - Listagem de solicitações
@app.route('/solicitacoes', methods=['GET', 'POST'])
def solicitacoes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    lista = Solicitacao.query.order_by(Solicitacao.id.desc()).all()
    usuarios_cadastrados = Usuario.query.all()
    return render_template("solicitacoes.html",titulo_pagina="Gerenciamento de Usuários", solicitacoes=lista, usuarios=usuarios_cadastrados)

# Alteração de status de uma solicitação
@app.route('/alterar_status/<int:solicitacao_id>')
def alterar_status(solicitacao_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    solicitacao = Solicitacao.query.get_or_404(solicitacao_id)
    usuario_atual = session.get('qra_usuario')

    print('QRA Atual:', usuario_atual)  # Teste rápido no terminal Flask

    agora_sp = datetime.now(fuso_sp)  # Pegamos aqui uma vez só, pra usar sempre igual




    if solicitacao.status == 'Pendente':
        solicitacao.status = 'Em andamento'
        solicitacao.horario_inicio = solicitacao.horario_inicio or datetime.now()  # Define horário de início se ainda não definido
        solicitacao.datahora_fim = None
        solicitacao.atendente = usuario_atual
        # Limpa o campo caso volte de concluído para pendente/em andamento

    elif solicitacao.status == 'Em andamento':
        solicitacao.status = 'Concluído'
        solicitacao.datahora_fim = datetime.now(fuso_sp)

        # Grava agora claramente a data/hora fim!

    elif solicitacao.status == 'Concluído':
        solicitacao.status = 'Pendente'
        solicitacao.datahora_fim = None
        solicitacao.atendente = None

        # Limpa novamente o campo finalizado

    db.session.commit()
    return redirect(url_for('solicitacoes'))

@app.route('/excluir_solicitacao/<int:solicitacao_id>')
def excluir_solicitacao(solicitacao_id):
    solicitacao = Solicitacao.query.get_or_404(solicitacao_id)

    db.session.delete(solicitacao)
    db.session.commit()

    return redirect(
        url_for('solicitacoes'))  # substitua corretamente pela função ou rota que lista as solicitações.



@app.route("/cadastro", methods=["POST"])
def cadastro():
    if not session.get('logged_in') or session['permissao'] != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('login'))

    usuario = request.form["usuario"]
    senha = request.form["senha"]
    permissao = request.form["permissao"]

    # bloco sugerido aqui:
    if permissao not in ['admin', 'user']:
        flash('Permissão inválida!', 'danger')
        return redirect(url_for('solicitacoes'))

    # Continua restante do seu código padrão abaixo...
    usuario_existente = Usuario.query.filter_by(usuario=usuario).first()
    if usuario_existente:
        flash('Usuário já existe!', 'warning')
        return redirect(url_for('solicitacoes'))

    senha_hash = generate_password_hash(senha)
    novo_usuario = Usuario(usuario=usuario, senha=senha_hash, permissao=permissao)

    try:
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Usuário cadastrado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro no cadastro: {e}', 'danger')

    return redirect(url_for("solicitacoes"))

@app.route('/alterar_permissao_usuario/<int:usuario_id>')
def alterar_permissao_usuario(usuario_id):
    if not session.get('logged_in') or session['permissao'] != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('login'))

    usuario = Usuario.query.get_or_404(usuario_id)

    # Alterna claramente a permissão entre 'admin' e 'user'
    nova_permissao = 'admin' if usuario.permissao == 'user' else 'user'
    usuario.permissao = nova_permissao

    try:
        db.session.commit()
        flash(f'Permissão alterada para "{nova_permissao}" com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar permissão: {e}', 'danger')

    return redirect(url_for("solicitacoes"))


@app.route('/alterar_senha_usuario/<int:usuario_id>', methods=['POST'])
def alterar_senha_usuario(usuario_id):
    if not session.get('logged_in') or session['permissao'] != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('login'))

    usuario = Usuario.query.get_or_404(usuario_id)
    nova_senha = request.form.get('nova_senha')

    if nova_senha:
        senha_hash = generate_password_hash(nova_senha)  # Criptografa a senha
        usuario.senha = senha_hash  # Atualiza a senha do usuário

        try:
            db.session.commit()  # Salva no banco de dados
            flash('Senha alterada com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao alterar a senha: {e}', 'danger')

    return redirect(url_for('solicitacoes'))  # Redireciona de volta para a página de solicitações




@app.route('/criar_solicitacao', methods=['POST'])
def criar_solicitacao():
    setor = request.form['setor']
    qra = request.form['qra']
    descricao_solicitacao = request.form['solicitacao']
    prioridade = request.form['prioridade']

    arquivo_imagem = request.files.get('imagem')
    filename = None
    if arquivo_imagem and arquivo_imagem.filename:
        filename = secure_filename(arquivo_imagem.filename)
        arquivo_imagem.save(os.path.join(UPLOAD_FOLDER, filename))

    nova_solicitacao = Solicitacao(
        setor=setor,
        qra=qra,
        solicitacao=descricao_solicitacao,
        prioridade=prioridade,
        status='Pendente',
        imagem=filename,
        datahora=datetime.now(),
        horario_inicio=datetime.now()
    )

    db.session.add(nova_solicitacao)
    db.session.commit()

    return redirect(url_for('solicitacoes'))  # Ajuste o nome da rota conforme estiver definido


@app.route('/buscar_usuario', methods=['GET'])
def buscar_usuario():
    if not session.get('logged_in') or session['permissao'] != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('login'))

    nome_usuario = request.args.get('usuario', '').strip()

    # Verifique se o nome de usuário foi fornecido
    if nome_usuario:
        # Busca usuários no banco de dados que contêm o nome pesquisado
        usuarios = Usuario.query.filter(Usuario.usuario.ilike(f'%{nome_usuario}%')).all()
    else:
        # Caso nenhum nome seja fornecido, mostra todos os usuários
        usuarios = Usuario.query.all()

    # Passa a lista de usuários encontrados para o template
    # Passa o primeiro usuário encontrado como usuario_encontrado, se houver
    usuario_encontrado = usuarios[0] if usuarios else None
    return render_template('solicitacoes.html', usuarios=usuarios, usuario_encontrado=usuario_encontrado)



@app.route('/chat', methods=['GET'])
def carregar_chat():
    if not session.get('usuario'):
        return jsonify({"status": "erro", "msg": "Usuário não autenticado."}), 401

    mensagens = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()

    mensagens_json = [{"sender": m.sender, "text": m.text} for m in mensagens]

    return jsonify({
        "usuario_atual": session['usuario'],
        "messages": mensagens_json
    })

@app.route('/chat/enviar', methods=['POST'])
def enviar_mensagem():
    if not session.get('usuario'):
        return jsonify({"status": "erro", "msg": "Usuário não autenticado."}), 401

    data = request.get_json()
    texto = data.get('text')

    # Validação simples e direta
    if not texto:
        return jsonify({"status": "erro", "msg": "Nenhum texto enviado."}), 400

    nova_mensagem = ChatMessage(
        sender=session['usuario'],  # Usa nome diretamente da sessão
        sender_type=session['permissao'],  # Usa permissão diretamente da sessão
        text=texto  # Somente texto, sem mais nada
    )

    db.session.add(nova_mensagem)
    db.session.commit()

    return jsonify({"status": "ok"})

# Rota para servir arquivos carregados
@app.route('/uploads/<nome_arquivo>')
def uploaded_file(nome_arquivo):
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Rota para enviar uma nova solicitação
@app.route('/enviar_solicitacao', methods=['POST'])
def enviar_solicitacao():
    # Recebe os dados do formulário
    setor = request.form['setor']
    qra = request.form['qra']
    solicitacao = request.form['solicitacao']
    prioridade = request.form['prioridade']
    imagem = request.files.get('imagem')
    imagem_filename = None

    if imagem and allowed_file(imagem.filename):
        imagem_filename = secure_filename(imagem.filename)
        imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_filename))
    # Aqui é onde o arquivo de imagem é recebido


    # Criação da nova solicitação sem 'datahora' e 'horario_inicio'
    nova_solicitacao = Solicitacao(
        setor=setor,
        qra=qra,
        solicitacao=solicitacao,
        prioridade=prioridade,
        status="Pendente",
        imagem=imagem_filename,
    )



    # Adiciona a solicitação ao banco de dados
    try:
        db.session.add(nova_solicitacao)
        db.session.commit()
        flash('Solicitação enviada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao salvar a solicitação: {e}', 'error')

    return redirect(url_for('solicitacoes'))

@app.route('/')
def home():
    return render_template('home_user.html')

@app.route('/radio')
def radio():
    return render_template('radio.html')

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

if __name__ == '__main__':
    app.run(debug=True)

