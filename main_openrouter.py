import json
import os
import time  # <--- Adicionado para o delay entre tentativas
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÕES ---
ARQUIVO_DADOS = "dados.json"
ARQUIVO_PROMPT = "prompt_template.txt"
MARCA_SEPARADOR = "___SEPARADOR___"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

TIMEOUT_SEGUNDOS = 120  # Espera no máximo 2 minutos por resposta
MAX_TOKENS = 4000       # Trava para evitar gastos infinitos se a IA surtar
TENTATIVAS_MAX = 3      # Quantas vezes tentar se der erro

MODELOS_DISPONIVEIS = {
    "1": {
        "nome": "DeepSeek V3 (Recomendado)",
        "slug": "deepseek/deepseek-chat",
        "desc": "O 'Rei' do custo-benefício. Inteligência nível GPT-4 custando centavos."
    },
    "2": {
        "nome": "Qwen 2.5 72B Instruct",
        "slug": "qwen/qwen-2.5-72b-instruct",
        "desc": "Modelo da Alibaba. Excelente para seguir instruções técnicas e JSON."
    },
    "3": {
        "nome": "Llama 3.3 70B (Meta)",
        "slug": "meta-llama/llama-3.3-70b-instruct",
        "desc": "Muito estável e confiável. Ótimo padrão de mercado."
    },
    "4": {
        "nome": "DeepSeek R1 (Raciocínio)",
        "slug": "deepseek/deepseek-r1",
        "desc": "Modelo que 'pensa' passo-a-passo. Use para encontrar erros lógicos no ETP."
    },
    "5": {
        "nome": "Mistral Small 3 (Europa)",
        "slug": "mistralai/mistral-small-24b-instruct-2501",
        "desc": "Lançamento recente (2025). Muito barato e surpreendentemente inteligente para lógica."
    }
}

# --- 3. FUNÇÕES DE DADOS ---
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

# --- 4. FUNÇÃO DE CHAMADA (Melhorada) ---
# --- 4. FUNÇÃO DE CHAMADA (Com Streaming/Efeito Datilografia) ---
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

    # Variável para acumular o texto completo para salvar no arquivo depois
    texto_completo = ""

    try:
        print("⏳ Aguardando primeira resposta (pode demorar uns segundos)...\n")
        print("-" * 40) # Linha visual para separar

        # Ativamos o stream=True aqui
        stream = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://automgr.local",
                "X-Title": "AutoMGR Script",
            },
            model=modelo_info['slug'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=4000,
            timeout=120,
            stream=True  # <--- A MÁGICA ACONTECE AQUI
        )

        # Loop que processa cada "pedacinho" (chunk) que chega
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                pedaco = chunk.choices[0].delta.content
                print(pedaco, end="", flush=True) # Imprime sem pular linha
                texto_completo += pedaco

        print("\n" + "-" * 40) # Pula linha ao final e fecha a separação visual

        # Salva o arquivo com o texto acumulado
        safe_name = modelo_info['slug'].split("/")[-1].replace("-", "_").replace(".", "")
        filename = f"resultado_{safe_name}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(texto_completo)

        print(f"\n✅ Sucesso! Resposta salva em '{filename}'")

    except Exception as e:
        print(f"\n❌ Erro durante a geração: {e}")

# --- 5. EXECUÇÃO ---
if __name__ == "__main__":
    sys, user = carregar_montar_prompt()

    if sys and user:
        print(f"📝 Prompt pronto ({len(user)} caracteres).")
        print("\n=== MENU CUSTO-BENEFÍCIO (OPENROUTER) ===")
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
