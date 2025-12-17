import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Carrega as variáveis do arquivo .env
load_dotenv()

# 2. Pega a chave usando a biblioteca OS
CHAVE_GOOGLE = os.getenv("GOOGLE_API_KEY")

if not CHAVE_GOOGLE:
    print("❌ Erro: A variável CHAVE_GOOGLE não foi encontrada no arquivo .env")
    exit()

# 3. Configura o Gemini
genai.configure(api_key=CHAVE_GOOGLE)

print("🔍 Conectando ao Google para listar modelos...")
print("-" * 40)

try:
    # Lista os modelos que suportam geração de texto
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ {m.name}")

except Exception as e:
    print(f"❌ Erro ao listar: {e}")
