# supabase_client.py
# (Versão Lote 6.2 - Robusta, usa dotenv_values)

import os
from supabase import create_client, Client
from dotenv import dotenv_values # <-- MUDANÇA: Não usamos mais 'load_dotenv'

# --- (MUDANÇA CRUCIAL LOTE 6.2) ---

# 1. Encontra o caminho absoluto para a pasta onde ESTE ficheiro está
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Cria o caminho completo para o ficheiro .env
DOTENV_PATH = os.path.join(APP_DIR, ".env")

print(f"A ler ficheiro .env de: {DOTENV_PATH}")

# 3. Lemos o ficheiro .env diretamente para um dicionário 'config'
config = dotenv_values(DOTENV_PATH)

# 4. Verificamos se a leitura falhou (ficheiro vazio ou formato errado)
if not config:
    if not os.path.exists(DOTENV_PATH):
         raise Exception(f"Erro: Ficheiro .env não encontrado em: {DOTENV_PATH}")
    raise Exception(f"Erro: Ficheiro .env foi encontrado, mas está vazio ou com formato inválido. Verifique o conteúdo (ex: espaços, aspas).")

# 5. Obtemos as chaves DIRETAMENTE do dicionário 'config'
SUPABASE_URL = config.get("SUPABASE_URL")
SUPABASE_KEY = config.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = config.get("SUPABASE_SERVICE_KEY")

# --- FIM DA MUDANÇA ---


# Validação (agora com debug melhorado)
if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_SERVICE_KEY:
    print("--- ERRO DE CHAVE (Debug Lote 6.2) ---")
    print(f"Caminho do .env: {DOTENV_PATH}")
    
    # Este print vai-nos mostrar EXATAMENTE o que o Python leu:
    print(f"Valores lidos do .env: {config}") 
    
    print("---------------------------------")
    print(f"URL: {'Encontrado' if SUPABASE_URL else 'FALTOU'}")
    print(f"KEY: {'Encontrado' if SUPABASE_KEY else 'FALTOU'}")
    print(f"SERVICE_KEY: {'Encontrado' if SUPABASE_SERVICE_KEY else 'FALTOU'}")
    print("---------------------")
    raise Exception("Erro: Uma ou mais chaves (SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY) não foram encontradas DENTRO do .env. Verifique se os nomes das variáveis estão corretos (sem espaços, em maiúsculas).")

try:
    # Cliente 'anon' (para utilizadores normais)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Ligação ao Supabase (Cliente Anon) inicializada com sucesso!")
except Exception as e:
    print(f"Erro ao inicializar Cliente Anon: {e}")
    supabase = None

try:
    # Cliente 'admin' (para a admin_view)
    supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("Ligação ao Supabase (Cliente Admin) inicializada com sucesso!")
except Exception as e:
    print(f"Erro ao inicializar Cliente Admin: {e}")
    supabase_admin = None