import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÕES ---
ARQUIVO_DADOS = "dados.json"
ARQUIVO_PROMPT = "prompt_template.txt"
MARCA_SEPARADOR = "___SEPARADOR___"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

TIMEOUT_SEGUNDOS = 600
MAX_TOKENS = 16000
TENTATIVAS_MAX = 3

# === LISTA DE MODELOS (ATUALIZADA) ===
MODELOS_DISPONIVEIS = {
    "1": {
        "nome": "DeepSeek V3 (Custo-Benefício)",
        "slug": "deepseek/deepseek-chat",
        "desc": "O equilíbrio perfeito. Inteligência de ponta com preço baixo."
    },
    "2": {
        "nome": "Qwen 2.5 72B Instruct (O Mais Barato)",
        "slug": "qwen/qwen-2.5-72b-instruct",
        "desc": "Modelo da Alibaba. Imbatível em preço para tarefas de formatação/JSON."
    },
    "3": {
        "nome": "Llama 3.3 70B (Meta)",
        "slug": "meta-llama/llama-3.3-70b-instruct",
        "desc": "O padrão do mercado ocidental. Muito estável."
    },
    "4": {
        "nome": "DeepSeek R1 (Raciocínio)",
        "slug": "deepseek/deepseek-r1",
        "desc": "Pensa antes de responder. Use para lógica complexa."
    },
    "5": {
        "nome": "Kimi K2 Thinking (Raciocínio)",
        "slug": "moonshotai/kimi-k2-thinking",
        "desc": "Modelo chinês que 'pensa' passo-a-passo. Ótimo para contextos longos."
    },
    "6": {
        "nome": "Kimi K2 Standard (Rápido)",
        "slug": "moonshotai/kimi-k2",
        "desc": "Versão padrão do Kimi. Mais rápida e estável que a versão Thinking."
    }
}

# --- FUNÇÕES DE DADOS (Mantidas) ---
CHAVES_IGNORAR = ["id", "fk_processo", "active", "order", "code", "created_at", "updated_at"]

def carregar_montar_prompt():
    print(f"📂 Lendo arquivos...")
    if not os.path.exists(ARQUIVO_DADOS):
        print(f"❌ '{ARQUIVO_DADOS}' não encontrado.")
        return None, None

    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f: dados = json.load(f)
    with open(ARQUIVO_PROMPT, 'r', encoding='utf-8') as f: template = f.read()

    def limpar(d):
        if isinstance(d, dict): return {k: limpar(v) for k, v in d.items() if k not in CHAVES_IGNORAR and v is not None and v != "null"}
        if isinstance(d, list): return [i for i in [limpar(x) for x in d] if i]
        return d

    if MARCA_SEPARADOR in template:
        sys_txt, user_txt = template.split(MARCA_SEPARADOR)
    else:
        sys_txt, user_txt = "", template

    sys_txt, user_txt = sys_txt.strip(), user_txt.strip()

    for k, v in dados.get("metadados", {}).items():
        user_txt = user_txt.replace(f"{{{{{k}}}}}", str(v))

    user_txt = user_txt.replace("{{ETP_CONTEUDO}}", json.dumps(limpar(dados.get("etp_conteudo", "")), ensure_ascii=False))
    user_txt = user_txt.replace("{{TR_CONTEUDO}}", json.dumps(limpar(dados.get("tr_conteudo", "")), ensure_ascii=False))

    return sys_txt, user_txt

# --- FUNÇÃO DE CHAMADA (CORRIGIDA) ---
def chamar_ia(modelo_info, system_prompt, user_prompt):
    print(f"\n🚀 Iniciando conexão com: {modelo_info['nome']}")
    print(f"   Slug: {modelo_info['slug']}")

    if not OPENROUTER_API_KEY:
        print("❌ Erro: Configure a OPENROUTER_API_KEY no arquivo .env")
        return

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    # Lógica inteligente para definir parâmetros
    # Se for modelo de raciocínio (Kimi Thinking, R1), NÃO usa penalidade de repetição
    is_reasoning_model = "thinking" in modelo_info['slug'] or "r1" in modelo_info['slug']

    params = {
        "model": modelo_info['slug'],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.6 if is_reasoning_model else 0.2, # Raciocínio precisa de mais "liberdade"
        "max_tokens": MAX_TOKENS,
        "timeout": TIMEOUT_SEGUNDOS,
        "stream": True
    }

    # Só adiciona penalidade se NÃO for modelo de raciocínio
    if not is_reasoning_model:
        params["frequency_penalty"] = 0.3
        params["presence_penalty"] = 0.3

    texto_completo = ""

    try:
        if is_reasoning_model:
            print("🧠 Modelo de raciocínio detectado: Ajustando parâmetros para evitar travamento...")

        print("⏳ Aguardando resposta...\n")
        print("-" * 40)

        stream = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://automgr.local",
                "X-Title": "AutoMGR Script",
            },
            **params # Desempacota os parâmetros configurados acima
        )

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                pedaco = chunk.choices[0].delta.content
                print(pedaco, end="", flush=True)
                texto_completo += pedaco

        print("\n" + "-" * 40)

        if not texto_completo.strip():
            print("\n⚠️ AVISO: O modelo retornou uma resposta vazia.")
        else:
            safe_name = modelo_info['slug'].split("/")[-1].replace("-", "_").replace(".", "")
            filename = f"resultado_{safe_name}.md"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(texto_completo)

            print(f"\n✅ Sucesso! Resposta salva em '{filename}'")

    except Exception as e:
        print(f"\n❌ Erro durante a geração: {e}")

if __name__ == "__main__":
    sys, user = carregar_montar_prompt()

    if sys and user:
        print(f"📝 Prompt pronto ({len(user)} caracteres).")
        print("\n=== MENU ATUALIZADO (6 OPÇÕES) ===")
        for k, v in MODELOS_DISPONIVEIS.items():
            print(f"{k}) {v['nome']}")

        escolha = input("\nDigite o número (ou 'todas'): ").strip()

        if escolha == 'todas':
            for key in MODELOS_DISPONIVEIS:
                chamar_ia(MODELOS_DISPONIVEIS[key], sys, user)
        elif escolha in MODELOS_DISPONIVEIS:
            chamar_ia(MODELOS_DISPONIVEIS[escolha], sys, user)
        else:
            print("Opção inválida.")
