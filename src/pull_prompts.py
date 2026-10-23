"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = PROJECT_ROOT / "prompts" / "bug_to_user_story_v1.yml"

load_dotenv(PROJECT_ROOT / ".env")


def pull_prompts_from_langsmith(client=None) -> bool:
    """Pull the challenge seed prompt and save its messages in the local YAML schema."""
    client = client or Client()
    prompt = client.pull_prompt(
        PROMPT_NAME,
        dangerously_pull_public_prompt=True,
    )

    system_messages = []
    user_messages = []
    for message in prompt.messages:
        role = (
            getattr(message, "role", None)
            or getattr(message, "prompt_type", None)
            or getattr(message, "type", None)
        )
        if role is None:
            message_type = type(message).__name__.lower()
            if message_type.startswith("systemmessage"):
                role = "system"
            elif message_type.startswith("humanmessage"):
                role = "human"
        template = getattr(getattr(message, "prompt", None), "template", None)
        if not isinstance(template, str):
            raise ValueError(f"Unsupported prompt message template: {message!r}")

        if role == "system":
            system_messages.append(template)
        elif role in ("human", "user"):
            user_messages.append(template)

    if not system_messages or not user_messages:
        raise ValueError("Pulled prompt must contain at least one system and one user message.")

    prompt_data = {
        "bug_to_user_story_v1": {
            "description": "Prompt semente para converter relatos de bugs em User Stories",
            "system_prompt": "\n\n".join(system_messages),
            "user_prompt": "\n\n".join(user_messages),
            "version": "v1",
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }
    return save_yaml(prompt_data, str(OUTPUT_PATH))


def main():
    """Função principal"""
    print_section_header("PULL DO PROMPT SEMENTE")
    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        if not pull_prompts_from_langsmith():
            print(f"❌ Não foi possível salvar o prompt em {OUTPUT_PATH}")
            return 1
    except Exception as error:
        print(f"❌ Falha ao puxar o prompt '{PROMPT_NAME}': {error}")
        return 1

    print(f"✅ Prompt salvo em {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
