import json
import os
import google.generativeai as genai
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

ARQUIVO_DADOS = "dados.json"
ARQUIVO_PROMPT = "prompt_template.txt"
ARQUIVO_DEBUG = "prompt_montado_debug.txt"
MARCA_SEPARADOR = "___SEPARADOR___"

CHAVE_GOOGLE = os.getenv("GOOGLE_API_KEY")
CHAVE_GROQ = os.getenv("GROQ_API_KEY")
CHAVE_OPENAI = os.getenv("OPENAI_API_KEY")

CHAVES_IGNORAR = ["id", "fk_processo", "active", "order", "code", "created_at", "updated_at"]

def carregar_arquivos():
    print(f"📂 Lendo arquivos '{ARQUIVO_DADOS}' e '{ARQUIVO_PROMPT}'...")
    if not os.path.exists(ARQUIVO_DADOS) or not os.path.exists(ARQUIVO_PROMPT):
        print("❌ Erro: Arquivos de dados/template não encontrados.")
        return None, None
    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    with open(ARQUIVO_PROMPT, 'r', encoding='utf-8') as f:
        template = f.read()
    return dados, template

def limpar_json(dados):
    if isinstance(dados, dict):
        return {k: limpar_json(v) for k, v in dados.items() if k not in CHAVES_IGNORAR and v is not None and v != "null"}
    elif isinstance(dados, list):
        return [i for i in [limpar_json(item) for item in dados] if i]
    return dados

def json_para_string(conteudo):
    limpo = limpar_json(conteudo)
    if isinstance(limpo, (dict, list)):
        return json.dumps(limpo, indent=2, ensure_ascii=False)
    return str(limpo)

def montar_prompt(dados, template_bruto):
    print("⚙️  Processando dados e montando o prompt...")
    if MARCA_SEPARADOR in template_bruto:
        system_txt, user_txt = template_bruto.split(MARCA_SEPARADOR)
    else:
        system_txt, user_txt = "", template_bruto

    system_txt, user_txt = system_txt.strip(), user_txt.strip()

    for k, v in dados.get("metadados", {}).items():
        user_txt = user_txt.replace(f"{{{{{k}}}}}", str(v))

    etp_str = json_para_string(dados.get("etp_conteudo", ""))
    tr_str = json_para_string(dados.get("tr_conteudo", ""))

    user_txt = user_txt.replace("{{ETP_CONTEUDO}}", etp_str)
    user_txt = user_txt.replace("{{TR_CONTEUDO}}", tr_str)

    return system_txt, user_txt

# --- 4. FUNÇÕES DAS APIS ---

def chamar_gemini(system, user):
    print("\n🔵 [Google] Tentando Gemini...")
    if not CHAVE_GOOGLE: return print("⚠️ Pulei: GOOGLE_API_KEY não encontrada no .env")

    genai.configure(api_key=CHAVE_GOOGLE)

    modelos_para_tentar = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-flash-latest", "gemini-pro"]

    for modelo_nome in modelos_para_tentar:
        try:
            print(f"   ...Tentando: {modelo_nome}")
            model = genai.GenerativeModel(modelo_nome, system_instruction=system)
            response = model.generate_content(user)
            with open("resultado_gemini.md", "w", encoding="utf-8") as f: f.write(response.text)
            print(f"✅ Sucesso! Salvo em 'resultado_gemini.md'")
            return
        except Exception as e:
            if "404" in str(e) or "not found" in str(e): continue
            else: print(f"❌ Erro crítico Gemini: {e}"); return

def chamar_groq(system, user):
    print("\n🟠 [Groq] Tentando Llama 3...")
    if not CHAVE_GROQ: return print("⚠️ Pulei: GROQ_API_KEY não encontrada no .env")
    try:
        client = Groq(api_key=CHAVE_GROQ)
        resp = client.chat.completions.create(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            model="llama-3.3-70b-versatile", temperature=0.2
        )
        content = resp.choices[0].message.content
        with open("resultado_groq.md", "w", encoding="utf-8") as f: f.write(content)
        print("✅ Sucesso! Salvo em 'resultado_groq.md'")
    except Exception as e:
        print(f"❌ Erro Groq: {e}")

def chamar_openai(system, user):
    print("\n🟢 [OpenAI] Tentando GPT-4o...")
    if not CHAVE_OPENAI: return print("⚠️ Pulei: OPENAI_API_KEY não encontrada no .env")
    try:
        client = OpenAI(api_key=CHAVE_OPENAI)
        resp = client.chat.completions.create(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            model="gpt-4o", temperature=0.2
        )
        content = resp.choices[0].message.content
        with open("resultado_gpt4o.md", "w", encoding="utf-8") as f: f.write(content)
        print("✅ Sucesso! Salvo em 'resultado_gpt4o.md'")
    except Exception as e:
        print(f"❌ Erro OpenAI: {e}")

# --- 5. EXECUÇÃO ---

if __name__ == "__main__":
    print("--- INICIANDO AUTOMGR (Modo Seguro .env) ---")
    dados_json, template_txt = carregar_arquivos()
    if dados_json and template_txt:
        sys_msg, user_msg = montar_prompt(dados_json, template_txt)

        # Salva debug
        with open(ARQUIVO_DEBUG, "w", encoding="utf-8") as f:
            f.write(f"=== SYSTEM ===\n{sys_msg}\n\n=== USER ===\n{user_msg}")

        # Executa
        chamar_gemini(sys_msg, user_msg)
        chamar_groq(sys_msg, user_msg)
        chamar_openai(sys_msg, user_msg)
        print("\n🏁 Fim.")
