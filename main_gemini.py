import json
import os
import time
import warnings
import google.generativeai as genai
from dotenv import load_dotenv

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
warnings.filterwarnings("ignore") # Esconde avisos chatos
os.environ["GRPC_VERBOSITY"] = "ERROR"

ARQUIVO_DADOS = "dados.json"
ARQUIVO_PROMPT = "prompt_template.txt"
MARCA_SEPARADOR = "___SEPARADOR___"
CHAVE_GOOGLE = os.getenv("GOOGLE_API_KEY")

# --- DEFINIÇÃO DOS MODELOS (ATUALIZADO) ---
# Substituído pelo 2.5 Pro conforme solicitado
MODELO_PRO = "models/gemini-2.5-pro"
ALIAS_PRO = "pro"

MODELO_FLASH = "models/gemini-2.0-flash"
ALIAS_FLASH = "flash"

QUANTIDADE_POR_MODELO = 3

# --- 1. FUNÇÕES DE ARQUIVO ---
CHAVES_IGNORAR = ["id", "fk_processo", "active", "order", "code", "created_at", "updated_at"]

def carregar_montar_prompt():
    print(f"📂 Lendo dados e template...")
    if not os.path.exists(ARQUIVO_DADOS): return None, None

    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f: dados = json.load(f)
    with open(ARQUIVO_PROMPT, 'r', encoding='utf-8') as f: template = f.read()

    def limpar(d):
        if isinstance(d, dict): return {k: limpar(v) for k, v in d.items() if k not in CHAVES_IGNORAR and v is not None}
        if isinstance(d, list): return [i for i in [limpar(x) for x in d] if i]
        return d

    if MARCA_SEPARADOR in template: sys_txt, user_txt = template.split(MARCA_SEPARADOR)
    else: sys_txt, user_txt = "", template

    for k, v in dados.get("metadados", {}).items():
        user_txt = user_txt.replace(f"{{{{{k}}}}}", str(v))

    user_txt = user_txt.replace("{{ETP_CONTEUDO}}", json.dumps(limpar(dados.get("etp_conteudo", "")), ensure_ascii=False))
    user_txt = user_txt.replace("{{TR_CONTEUDO}}", json.dumps(limpar(dados.get("tr_conteudo", "")), ensure_ascii=False))

    return sys_txt.strip(), user_txt.strip()

# --- 2. FUNÇÃO GERADORA ---
def gerar_lote(modelo_nome, alias_arquivo, system, user, quantidade):
    print(f"\n{'='*60}")
    print(f"🚀 INICIANDO BATERIA DE TESTES: {alias_arquivo.upper()}")
    print(f"   Modelo: {modelo_nome}")
    print(f"{'='*60}")

    genai.configure(api_key=CHAVE_GOOGLE)

    config_seguranca = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    try:
        model = genai.GenerativeModel(
            modelo_nome,
            system_instruction=system,
            safety_settings=config_seguranca
        )
    except Exception as e:
        print(f"❌ Erro ao configurar modelo {modelo_nome}: {e}")
        return

    for i in range(1, quantidade + 1):
        nome_arquivo = f"resultado_{alias_arquivo}_{i:02d}.md"
        print(f"\n📄 Gerando resposta {i}/{quantidade}...")

        try:
            inicio = time.time()

            # Usando temperatura levemente alta para variar as respostas entre si
            response = model.generate_content(
                user,
                stream=True,
                generation_config=genai.types.GenerationConfig(temperature=0.4)
            )

            texto_final = ""
            print("   ↳ ", end="")

            for chunk in response:
                if chunk.text:
                    print(".", end="", flush=True) # Imprime pontinhos
                    texto_final += chunk.text

            tempo = time.time() - inicio

            with open(nome_arquivo, "w", encoding="utf-8") as f:
                f.write(texto_final)

            print(f"\n   ✅ Salvo em '{nome_arquivo}' ({tempo:.1f}s)")

            if i < quantidade:
                time.sleep(2)

        except Exception as e:
            print(f"\n   ❌ Falha na geração {i}: {e}")
            time.sleep(5)

# --- 3. EXECUÇÃO ---
if __name__ == "__main__":
    if not CHAVE_GOOGLE:
        print("❌ Erro: Configure GOOGLE_API_KEY no .env")
        exit()

    sys, user = carregar_montar_prompt()

    if sys and user:
        # 1. Gera 3 versões com o PRO (2.5)
        gerar_lote(MODELO_PRO, ALIAS_PRO, sys, user, QUANTIDADE_POR_MODELO)

        # 2. Gera 3 versões com o FLASH (2.0)
        gerar_lote(MODELO_FLASH, ALIAS_FLASH, sys, user, QUANTIDADE_POR_MODELO)

        print("\n🏁 Processo finalizado! 6 arquivos gerados.")
