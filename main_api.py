import json
import os
import time  # <--- Necessário para o delay entre tentativas
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

# --- FUNÇÕES UTILITÁRIAS ---
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

# --- 4. FUNÇÕES DAS APIS (COM STREAMING E RETRY) ---

def chamar_gemini(system, user):
    print("\n" + "="*50)
    print("🔵 [Google] Iniciando Gemini PRO...")

    if not CHAVE_GOOGLE:
        return print("⚠️ Pulei: GOOGLE_API_KEY não encontrada.")

    genai.configure(api_key=CHAVE_GOOGLE)

    # Prioridade para o modelo 2.5 e 1.5 Pro
    modelos_para_tentar = [
        "models/gemini-3-flash-preview",
        "models/gemini-3-pro-preview",
    ]

    for modelo_nome in modelos_para_tentar:
        print(f"   👉 Tentando modelo: {modelo_nome}")
        try:
            config_seguranca = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            model = genai.GenerativeModel(
                modelo_nome,
                system_instruction=system,
                safety_settings=config_seguranca
            )

            print("   ⏳ Gerando resposta (Streaming)...")
            # STREAMING ATIVADO
            response_stream = model.generate_content(
                user,
                stream=True, # <--- AQUI
                generation_config=genai.types.GenerationConfig(temperature=0.2)
            )

            texto_completo = ""
            print("-" * 30)

            for chunk in response_stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    texto_completo += chunk.text

            print("\n" + "-" * 30)

            with open("resultado_gemini.md", "w", encoding="utf-8") as f:
                f.write(texto_completo)

            print(f"\n✅ Sucesso! Salvo em 'resultado_gemini.md'")
            return # Sai da função se der certo

        except Exception as e:
            if "404" in str(e) or "not found" in str(e):
                continue # Tenta o próximo modelo silenciosamente
            print(f"\n❌ Erro no Gemini ({modelo_nome}): {e}")
            time.sleep(1) # Pequena pausa antes de tentar outro modelo

def chamar_groq(system, user):
    print("\n" + "="*50)
    print("🟠 [Groq] Iniciando Llama 3...")

    if not CHAVE_GROQ:
        return print("⚠️ Pulei: GROQ_API_KEY não encontrada.")

    client = Groq(api_key=CHAVE_GROQ)

    for tentativa in range(3): # Tenta 3 vezes
        try:
            stream = client.chat.completions.create(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=4000,
                stream=True # <--- STREAMING
            )

            texto_completo = ""
            print("   ⏳ Gerando resposta...")
            print("-" * 30)

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    pedaco = chunk.choices[0].delta.content
                    print(pedaco, end="", flush=True)
                    texto_completo += pedaco

            print("\n" + "-" * 30)

            with open("resultado_groq.md", "w", encoding="utf-8") as f: f.write(texto_completo)
            print("\n✅ Sucesso! Salvo em 'resultado_groq.md'")
            return

        except Exception as e:
            print(f"\n⚠️ Erro Groq (Tentativa {tentativa+1}): {e}")
            time.sleep(2)

def chamar_openai(system, user):
    print("\n" + "="*50)
    print("🟢 [OpenAI] Iniciando GPT-4o...")

    if not CHAVE_OPENAI:
        return print("⚠️ Pulei: OPENAI_API_KEY não encontrada.")

    client = OpenAI(api_key=CHAVE_OPENAI)

    for tentativa in range(3):
        try:
            stream = client.chat.completions.create(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                model="gpt-4o",
                temperature=0.2,
                stream=True, # <--- STREAMING
                frequency_penalty=0.3 # Evita repetições
            )

            texto_completo = ""
            print("   ⏳ Gerando resposta...")
            print("-" * 30)

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    pedaco = chunk.choices[0].delta.content
                    print(pedaco, end="", flush=True)
                    texto_completo += pedaco

            print("\n" + "-" * 30)

            with open("resultado_gpt4o.md", "w", encoding="utf-8") as f: f.write(texto_completo)
            print("\n✅ Sucesso! Salvo em 'resultado_gpt4o.md'")
            return

        except Exception as e:
            print(f"\n⚠️ Erro OpenAI (Tentativa {tentativa+1}): {e}")
            time.sleep(2)

# --- 5. EXECUÇÃO ---

if __name__ == "__main__":
    print("--- INICIANDO AUTOMGR (Modo Multi-Provider) ---")
    dados_json, template_txt = carregar_arquivos()

    if dados_json and template_txt:
        sys_msg, user_msg = montar_prompt(dados_json, template_txt)

        # Salva debug
        with open(ARQUIVO_DEBUG, "w", encoding="utf-8") as f:
            f.write(f"=== SYSTEM ===\n{sys_msg}\n\n=== USER ===\n{user_msg}")

        # Chama um por um
        chamar_gemini(sys_msg, user_msg)
        chamar_groq(sys_msg, user_msg)
        chamar_openai(sys_msg, user_msg)

        print("\n🏁 Fim de todas as execuções.")
