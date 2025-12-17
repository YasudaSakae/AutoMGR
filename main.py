import json
import os

# Nomes dos arquivos
ARQUIVO_DADOS = "dados.json"
ARQUIVO_PROMPT = "prompt_template.txt"

def carregar_arquivos():
    # 1. Carregar os DADOS do JSON
    print(f"Lendo dados de '{ARQUIVO_DADOS}'...")
    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    # 2. Carregar o TEMPLATE do Prompt
    print(f"Lendo template de '{ARQUIVO_PROMPT}'...")
    with open(ARQUIVO_PROMPT, 'r', encoding='utf-8') as f:
        template = f.read()

    return dados, template

def preencher_prompt(dados, template):
    print("Injetando dados no prompt...")

    prompt_final = template

    # 1. Substituir Metadados (loop pelas chaves do json)
    for chave, valor in dados["metadados"].items():
        placeholder = f"{{{{{chave}}}}}"  # Cria a string {{CHAVE}}
        prompt_final = prompt_final.replace(placeholder, str(valor))

    # 2. Substituir ETP e TR
    prompt_final = prompt_final.replace("{{ETP_CONTEUDO}}", dados["etp_conteudo"])
    prompt_final = prompt_final.replace("{{TR_CONTEUDO}}", dados["tr_conteudo"])

    return prompt_final

def main():
    try:
        dados, template = carregar_arquivos()
        prompt_pronto = preencher_prompt(dados, template)

        # --- AQUI VOCÊ CONECTARIA COM A API ---
        # Por enquanto, vamos apenas salvar o resultado para você conferir

        nome_saida = "prompt_final_para_envio.txt"
        with open(nome_saida, 'w', encoding='utf-8') as f_out:
            f_out.write(prompt_pronto)

        print(f"\nSUCESSO! O prompt montado foi salvo em '{nome_saida}'.")
        print("Agora você pode copiar o conteúdo desse arquivo e colar no ChatGPT/Claude para testar manualmente, ou plugar a API aqui.")

    except FileNotFoundError as e:
        print(f"ERRO: Arquivo não encontrado - {e}")
    except json.JSONDecodeError:
        print(f"ERRO: O arquivo '{ARQUIVO_DADOS}' não é um JSON válido. Verifique vírgulas e aspas.")
    except Exception as e:
        print(f"ERRO inesperado: {e}")

if __name__ == "__main__":
    main()
