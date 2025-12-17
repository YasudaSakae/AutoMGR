import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Carrega o arquivo .env
load_dotenv()

# --- 1. CONFIGURAÇÕES ---
ARQUIVO_DADOS = "dados.json"
ARQUIVO_PROMPT = "prompt_template.txt"
MARCA_SEPARADOR = "___SEPARADOR___"

# Sua chave do OpenRouter (coloque no .env como OPENROUTER_API_KEY)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- 2. MENU DE MODELOS (OS MELHORES PARA SEU CASO) ---
MODELOS_DISPONIVEIS = {
    "1": {
        "nome": "Claude 3.5 Sonnet (Anthropic)",
        "slug": "anthropic/claude-3.5-sonnet",
        "desc": "Melhor qualidade de texto e lógica jurídica. Recomendado para versão final."
    },
    "2": {
        "nome": "DeepSeek V3",
        "slug": "deepseek/deepseek-chat",
        "desc": "Excelente custo-benefício. Quase de graça e muito inteligente. Ótimo para testes."
    },
    "3": {
        "nome": "DeepSeek R1 (Raciocínio)",
        "slug": "deepseek/deepseek-r1",
        "desc": "Modelo que 'pensa' passo-a-passo. Ótimo para achar riscos complexos."
    },
    "4": {
        "nome": "Gemini 2.0 Flash (Google)",
        "slug": "google/gemini-2.0-flash-001",
        "desc": "Janela de contexto gigante (1M tokens). Use se o TR for gigantesco."
    },
    "5": {
        "nome": "Llama 3.3 70B (Meta)",
        "slug": "meta-llama/llama-3.3-70b-instruct",
        "desc": "Melhor Open Source atual. Muito sólido."
    }
}

# --- 3. FUNÇÕES DE DADOS (Limpeza e Montagem) ---
# (Reaproveitando sua lógica de limpeza para economizar tokens)
CHAVES_IGNORAR = ["id", "fk_processo", "active", "order", "code", "created_at", "updated_at"]

def carregar_montar_prompt():
    print(f"📂 Lendo arquivos...")
    if not os.path.exists(ARQUIVO_DADOS):
        print(f"❌ '{ARQUIVO_DADOS}' não encontrado.")
        return None, None

    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f: dados = json.load(f)
    with open(ARQUIVO_PROMPT, 'r', encoding='utf-8') as f: template = f.read()

    # Função interna de limpeza
    def limpar(d):
        if isinstance(d, dict): return {k: limpar(v) for k, v in d.items() if k not in CHAVES_IGNORAR and v is not None and v != "null"}
        if isinstance(d, list): return [i for i in [limpar(x) for x in d] if i]
        return d

    # Separação System/User
    if MARCA_SEPARADOR in template:
        sys_txt, user_txt = template.split(MARCA_SEPARADOR)
    else:
        sys_txt, user_txt = "", template

    sys_txt, user_txt = sys_txt.strip(), user_txt.strip()

    # Injeção de variáveis
    for k, v in dados.get("metadados", {}).items():
        user_txt = user_txt.replace(f"{{{{{k}}}}}", str(v))

    user_txt = user_txt.replace("{{ETP_CONTEUDO}}", json.dumps(limpar(dados.get("etp_conteudo", "")), ensure_ascii=False))
    user_txt = user_txt.replace("{{TR_CONTEUDO}}", json.dumps(limpar(dados.get("tr_conteudo", "")), ensure_ascii=False))

    return sys_txt, user_txt

# --- 4. FUNÇÃO DE CHAMADA (GENÉRICA PARA OPENROUTER) ---
def chamar_ia(modelo_info, system_prompt, user_prompt):
    print(f"\n🚀 Enviando para: {modelo_info['nome']}...")
    print(f"   Slug: {modelo_info['slug']}")

    if not OPENROUTER_API_KEY:
        print("❌ Erro: Configure a OPENROUTER_API_KEY no arquivo .env")
        return

    # O OpenRouter usa a mesma biblioteca da OpenAI!
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://github.com/seuseu/automgr",
                "X-Title": "AutoMGR",
            },
            model=modelo_info['slug'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2, # Temperatura baixa para ser consistente
        )

        resposta = completion.choices[0].message.content

        # Salva o arquivo
        safe_name = modelo_info['nome'].split(" ")[0].lower()
        filename = f"resultado_{safe_name}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(resposta)

        print(f"✅ Sucesso! Resposta salva em '{filename}'")

    except Exception as e:
        print(f"❌ Erro ao chamar API: {e}")

# --- 5. EXECUÇÃO ---
if __name__ == "__main__":
    sys, user = carregar_montar_prompt()

    if sys and user:
        print(f"📝 Prompt pronto ({len(user)} caracteres).")
        print("\nEscolha qual modelo testar:")
        for k, v in MODELOS_DISPONIVEIS.items():
            print(f"{k}) {v['nome']} - {v['desc']}")

        escolha = input("\nDigite o número (ou 'todas' para rodar tudo): ").strip()

        if escolha == 'todas':
            for key in MODELOS_DISPONIVEIS:
                chamar_ia(MODELOS_DISPONIVEIS[key], sys, user)
        elif escolha in MODELOS_DISPONIVEIS:
            chamar_ia(MODELOS_DISPONIVEIS[escolha], sys, user)
        else:
            print("Opção inválida.")
