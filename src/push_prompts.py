"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langsmith.utils import LangSmithConflictError
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = PROJECT_ROOT / "prompts" / "bug_to_user_story_v2.yml"

load_dotenv(PROJECT_ROOT / ".env")


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict, client=None) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return False

    client = client or Client()
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])
    techniques = prompt_data["techniques_applied"]
    tags = list(dict.fromkeys([
        *prompt_data.get("tags", []),
        *(technique.lower().replace(" ", "-") for technique in techniques),
    ]))
    description = (
        f"{prompt_data['description']} "
        f"Técnicas aplicadas: {', '.join(techniques)}."
    )

    try:
        url = client.push_prompt(
            prompt_name,
            object=prompt,
            is_public=True,
            description=description,
            tags=tags,
        )
    except LangSmithConflictError as error:
        if (
            "Nothing to commit: prompt has not changed since latest commit"
            in str(error)
        ):
            print(f"ℹ️  O prompt '{prompt_name}' já está publicado sem alterações.")
            return True
        print(f"❌ Falha ao publicar '{prompt_name}' no LangSmith: {error}")
        return False
    except Exception as error:
        print(f"❌ Falha ao publicar '{prompt_name}' no LangSmith: {error}")
        return False

    print(f"✅ Prompt publicado como público: {prompt_name}")
    if url:
        print(f"   {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list[str]]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []
    if not isinstance(prompt_data, dict):
        return False, ["O conteúdo do prompt deve ser um objeto YAML."]

    for field in ("description", "system_prompt", "user_prompt", "version"):
        value = prompt_data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Campo obrigatório ausente ou vazio: {field}")

    user_prompt = prompt_data.get("user_prompt", "")
    if isinstance(user_prompt, str) and "{bug_report}" not in user_prompt:
        errors.append("user_prompt precisa conter a variável {bug_report}.")

    techniques = prompt_data.get("techniques_applied")
    if not isinstance(techniques, list) or len(techniques) < 2:
        errors.append("Informe pelo menos duas técnicas em techniques_applied.")
    elif any(not isinstance(item, str) or not item.strip() for item in techniques):
        errors.append("Cada técnica em techniques_applied deve ser texto não vazio.")

    prompt_text = " ".join(
        value for key, value in prompt_data.items()
        if isinstance(value, str) and key != "version"
    )
    if "[TODO]" in prompt_text or "[TODO]" in user_prompt:
        errors.append("O prompt ainda contém marcadores [TODO].")

    return not errors, errors


def main():
    """Função principal"""
    print_section_header("PUSH DO PROMPT OTIMIZADO")
    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    prompt_document = load_yaml(str(PROMPT_FILE))
    if not isinstance(prompt_document, dict):
        print(f"❌ Não foi possível carregar o YAML: {PROMPT_FILE}")
        return 1

    prompt_data = prompt_document.get("bug_to_user_story_v2")
    if not isinstance(prompt_data, dict):
        print("❌ O YAML deve conter o objeto 'bug_to_user_story_v2'.")
        return 1

    prompt_name = f"{os.environ['USERNAME_LANGSMITH_HUB']}/bug_to_user_story_v2"
    return 0 if push_prompt_to_langsmith(prompt_name, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
