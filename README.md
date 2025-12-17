# AutoMGR

Geração automática de **Mapa de Gerenciamento de Riscos (MGR)** para contratações públicas (Lei nº 14.133/2021) a partir de insumos como **ETP** e **TR**, usando modelos de IA (Gemini, Groq, OpenAI e/ou OpenRouter).

## O que ele faz

- Lê `dados.json` (metadados + conteúdo do ETP + conteúdo do TR).
- Monta um prompt a partir de `prompt_template.txt` (com separador `___SEPARADOR___`).
- Envia o prompt para um ou mais provedores de IA (com streaming no terminal).
- Salva a resposta em arquivos `resultado_*.md` e salva o prompt final em `prompt_montado_debug.txt`.

## Requisitos

- Python 3.10+ (recomendado)
- Chave(s) de API conforme o provedor que você for usar:
  - `GOOGLE_API_KEY` (Google Gemini)
  - `GROQ_API_KEY` (Groq)
  - `OPENAI_API_KEY` (OpenAI)
  - `OPENROUTER_API_KEY` (OpenRouter)

## Instalação

Crie e ative um ambiente virtual e instale as dependências:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -U pip
pip install google-generativeai groq openai python-dotenv
```

No Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -U pip
pip install google-generativeai groq openai python-dotenv
```

## Configuração do `.env`

Crie um arquivo `.env` na raiz do projeto com as chaves que você tiver:

```env
GOOGLE_API_KEY=...
GROQ_API_KEY=...
OPENAI_API_KEY=...
OPENROUTER_API_KEY=...
```

Você pode configurar só algumas chaves; os scripts pulam provedores sem chave configurada.

## Entradas do projeto

### `dados.json`

Estrutura esperada (resumo):

```json
{
  "metadados": {
    "ORGAO_UNIDADE": "...",
    "NUM_PROCESSO": "...",
    "MODALIDADE": "...",
    "OBJETO_RESUMO": "...",
    "VALOR_ESTIMADO": "...",
    "PRAZO": "...",
    "LOCAL": "...",
    "OBSERVACOES": "..."
  },
  "etp_conteudo": { "...": "..." },
  "tr_conteudo": [ { "secao": "...", "itens": ["..."] } ]
}
```

Observação: os scripts fazem uma “limpeza” do JSON (removendo algumas chaves como `id`, `created_at` etc.) para reduzir ruído no prompt. A lista está em `CHAVES_IGNORAR` nos arquivos `main_api.py` e `main_openrouter.py`.

### `prompt_template.txt`

- Tudo **antes** de `___SEPARADOR___` vira o *SYSTEM prompt*.
- Tudo **depois** de `___SEPARADOR___` vira o *USER prompt*.
- Placeholders principais:
  - `{{ETP_CONTEUDO}}`, `{{TR_CONTEUDO}}`
  - `{{ORGAO_UNIDADE}}`, `{{NUM_PROCESSO}}`, `{{MODALIDADE}}` etc. (vindos de `metadados`)

## Como executar

### 1) Modo multi-provider (Gemini + Groq + OpenAI)

Roda em sequência e salva um arquivo por provedor:

```bash
python main_api.py
```

Saídas típicas:

- `prompt_montado_debug.txt`
- `resultado_gemini.md`
- `resultado_groq.md`
- `resultado_gpt4o.md`

### 2) Modo OpenRouter (menu de modelos)

Mostra um menu (ou opção `todas`) e salva a resposta em `resultado_<modelo>.md`:

```bash
python main_openrouter.py
```

### 3) Listar modelos do Gemini (opcional)

```bash
python list_models.py
```

## Notas importantes

- **Custos e limites**: chamadas de API são pagas; revise modelo, `max_tokens` e tamanho do prompt antes de rodar em lotes.
- **Segurança**: não comite `.env` e evite salvar prompts/respostas com dados sensíveis fora do necessário.
- **Aderência ao TR/ETP**: o conteúdo final depende diretamente da qualidade/estrutura de `dados.json` e do template em `prompt_template.txt`.

