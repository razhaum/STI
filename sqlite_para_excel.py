import sqlite3
import pandas as pd
import os

# Caminho absoluto corretamente até a pasta instance
caminho_banco = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'mydatabase.db')
conexao = sqlite3.connect(caminho_banco)

# Nome exato da tabela confirmada agora que existe!
nome_tabela = "solicitacao"

# Realizando a consulta SQL e exportando os dados pra Excel
df = pd.read_sql_query(f'SELECT * FROM {nome_tabela}', conexao)
conexao.close()

# Exporta diretamente para Excel
df.to_excel('solicitacoes.xlsx', index=False, engine='openpyxl')



print(f'🚀 Tabela "{nome_tabela}" exportada com sucesso para "solicitacoes.xlsx"!')
