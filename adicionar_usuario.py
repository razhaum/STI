from werkzeug.security import generate_password_hash
from app import db, \
    Usuario  # Certifique-se de que você tenha o modelo 'Usuario' e a instância do db configurada corretamente

# Lista de nomes dos usuários a serem adicionados
nomes_usuarios = [
    "CASSIA", "PAIXAO", "ADRIANA FLORIANO", "JANETE", "LEIA", "DISCO", "TEIXEIRA",
    "CLEBER", "NASCIMENTO", "REIS", "JOILTON", "FERNANDES", "GALEGO", "ASSIS",
    "PAULA ARE", "JORGE", "ROSELI", "ROSANGELA", "WILKA", "EDILENE", "RONI",
    "CEZAR", "STELA", "AUDINEIA", "BARREIROS", "ROGERIO OLIVEIRA", "ALVES",
    "TOBIAS", "SANDRA CAETANO", "EDJAINE", "ARCANJO", "MARCIA PEREIRA", "TATIANA",
    "ANDREA", "VANESSA LUIZ", "OZEAS", "BRITO", "MARCIO APARECIDO", "GILMAR",
    "ALESSANDRA", "RODNEI", "ECINEIA", "EDLEIA", "PIMENTEL", "ALEXANDRA", "ELAINE",
    "ERICA MARIA", "DJARIA", "CASTILHO", "ADRIANO", "LIVINO", "ROGERIO", "PAULO SANTOS",
    "KEYLA", "DENISE", "JANETE SILVA", "CINTRA", "SOBRINHO", "EDSON SILVA", "ANDREASSA",
    "DE PAULA", "ROBERTA", "LOPES", "PAULO", "FERNANDA", "LUANA", "TELMA CARVALHO",
    "ELIANE", "MOTA", "DIAS", "ARIADINE", "JARDIM", "MAIARA", "BERALDES", "MARYEL",
    "BARRETO", "FRAGOZO", "MAIRTA", "SALOMAO", "DEISE", "D SOUSA", "GUIOMAR", "MICHEL",
    "FABIANA COSTA", "PATRICIA", "SANTANA", "VALENTIM", "CHAVES", "CALEGARI", "PANTONI",
    "RODOLFO", "R. SOUZA", "LOBO", "KLISMAN", "HIGINO", "VITOR", "FRANCHI",
    "RAPHAELLA SILVA", "MOURA", "LISBOA", "MARIA", "DOS SANTOS", "ADRIEL", "PACHECO",
    "GUILHERME", "SARTURI", "AGUIAR", "XAVIER", "RODRIGO", "ARAUJO", "JULIANA",
    "VENTURINI", "DAIANA JESUS", "ZOZIMO", "TOLEDO", "REGARMUTO", "DEODORO", "CAYRES",
    "LACERDA", "RENATO BRAZ", "SHIRAHIGE", "JOELMA", "FLAVIA", "PATRICIA CESAR", "DAIANE",
    "TIBURTINO", "ADRIANNY", "REIS", "BARBOSA", "HUGO", "ALINE MOURA", "FELIPE LUIS",
    "MOSE", "BETTIOL", "DE SA", "ANSELMO MAXIMO", "GABRIELLI", "AGUIAR", "CIENCIA",
    "J FELLIPPE", "THAIS CRUZ", "ANA SANTOS", "THAIS LIMA", "MARCELO ALVES",
    "CAVALCANTE", "JOAB", "GREISE", "MARCOS", "BENEDETTI", "CIRANO", "WELLINGTON",
    "MENEGALDO", "FABIANA", "BARALLE"
]

# Cria os usuários e os adiciona ao banco de dados
for nome in nomes_usuarios:
    usuario_existente = Usuario.query.filter_by(usuario=nome).first()

    if not usuario_existente:  # Verifica se o usuário já existe
        senha_hash = generate_password_hash('123')  # Gera o hash da senha "123"
        novo_usuario = Usuario(usuario=nome, senha=senha_hash,
                               permissao='user')  # Define permissao como 'user' para todos

        db.session.add(novo_usuario)
        db.session.commit()
        print(f'Usuário {nome} adicionado com sucesso!')
    else:
        print(f'Usuário {nome} já existe.')