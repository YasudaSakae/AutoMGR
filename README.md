# AutoMGR

Geração automática de **Mapa de Gerenciamento de Riscos (MGR)** para contratações públicas (Lei nº 14.133/2021) a partir de insumos como **ETP** e **TR**, usando modelos de IA (Gemini, Groq, OpenAI e/ou OpenRouter).

## O que ele faz

- Lê `inputs/dados.json` (metadados + conteúdo do ETP + conteúdo do TR).
- Monta um prompt a partir de `inputs/prompt_template.txt` (com separador `___SEPARADOR___`).
- Envia o prompt para um ou mais provedores de IA (com streaming no terminal).
- Salva o prompt final em `outputs/prompt_montado_debug.txt` e as respostas em `outputs/resultado_*.md`.

## Requisitos

- Python 3.10+ (recomendado)
- Chave(s) de API conforme o provedor que você for usar:
  - `GOOGLE_API_KEY` (Google Gemini)
  - `GROQ_API_KEY` (Groq)
  - `OPENAI_API_KEY` (OpenAI)
  - `OPENROUTER_API_KEY` (OpenRouter)

## Instalação

Crie e ative um ambiente virtual e instale o pacote em modo editável:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -U pip
pip install -e .
```

No Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .
```

Alternativa simples (sem instalar o pacote): `pip install -r requirements.txt` e rode com `PYTHONPATH=src`.

## Configuração do `.env`

Copie `.env.example` para `.env` e preencha as chaves que você tiver:

```env
GOOGLE_API_KEY=...
GROQ_API_KEY=...
OPENAI_API_KEY=...
OPENROUTER_API_KEY=...
```

Você pode configurar só algumas chaves; os scripts pulam provedores sem chave configurada.

## Entradas do projeto

### `inputs/dados.json`

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

### `inputs/prompt_template.txt`

- Tudo **antes** de `___SEPARADOR___` vira o *SYSTEM prompt*.
- Tudo **depois** de `___SEPARADOR___` vira o *USER prompt*.
- Placeholders principais:
  - `{{ETP_CONTEUDO}}`, `{{TR_CONTEUDO}}`
  - `{{ORGAO_UNIDADE}}`, `{{NUM_PROCESSO}}`, `{{MODALIDADE}}` etc. (vindos de `metadados`)

## Como executar

### 1) CLI (recomendado)

Roda Gemini + Groq + OpenAI em sequência:

```bash
automgr run
```

Roda em modo interativo (lista modelos e deixa você escolher):

```bash
automgr run --select-models
```

Saídas típicas:

- `outputs/prompt_montado_debug.txt`
- `outputs/resultado_gemini.md`
- `outputs/resultado_groq.md`
- `outputs/resultado_openai.md`

Executa OpenRouter (menu interativo):

```bash
automgr openrouter
```

Executa OpenRouter com lista completa de modelos (interativo, pode ser grande):

```bash
automgr openrouter --select-model
```

Executa OpenRouter direto por slug:

```bash
automgr openrouter --model deepseek/deepseek-chat
```

Listar modelos do Gemini:

```bash
automgr list-gemini-models
```

Listar modelos por provider (com filtro):

```bash
automgr models --provider gemini --filter 2.5
automgr models --provider groq
automgr models --provider openai --filter gpt-4o
automgr models --provider openrouter --filter deepseek
```

Gerar lote (várias versões) com Gemini:

```bash
automgr gemini-batch --count 3
```

### 2) Scripts (atalhos)

Os arquivos em `scripts/` são apenas wrappers do CLI:

```bash
python scripts/main_api.py
python scripts/main_openrouter.py
python scripts/main_gemini.py
python scripts/list_models.py
```

## Notas importantes

- **Custos e limites**: chamadas de API são pagas; revise modelo, `max_tokens` e tamanho do prompt antes de rodar em lotes.
- **Segurança**: não comite `.env` e evite salvar prompts/respostas com dados sensíveis fora do necessário.
- **Aderência ao TR/ETP**: o conteúdo final depende diretamente da qualidade/estrutura de `inputs/dados.json` e do template em `inputs/prompt_template.txt`.
