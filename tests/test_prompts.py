"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

PROJECT_ROOT = Path(__file__).parent.parent
PROMPT_PATH = PROJECT_ROOT / "prompts" / "bug_to_user_story_v2.yml"


@pytest.fixture(scope="module")
def prompt_data():
    """Carrega o prompt v2 e valida o formato YAML do arquivo."""
    with PROMPT_PATH.open(encoding="utf-8") as prompt_file:
        document = yaml.safe_load(prompt_file)
    assert isinstance(document, dict)
    assert isinstance(document.get("bug_to_user_story_v2"), dict)
    return document["bug_to_user_story_v2"]

class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert isinstance(prompt_data.get("system_prompt"), str)
        assert prompt_data["system_prompt"].strip()

    def test_prompt_has_role_definition(self, prompt_data):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert "Você é uma Product Manager" in prompt_data["system_prompt"]

    def test_prompt_mentions_format(self, prompt_data):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        prompt_text = f"{prompt_data['system_prompt']}\n{prompt_data.get('user_prompt', '')}"
        assert "Markdown" in prompt_text
        assert "História de usuário" in prompt_text
        assert "Critérios de aceitação" in prompt_text

    def test_prompt_has_few_shot_examples(self, prompt_data):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt_data["system_prompt"]
        assert "EXEMPLO 1 — Entrada" in system_prompt
        assert "EXEMPLO 1 — Saída" in system_prompt
        assert "EXEMPLO 2 — Entrada" in system_prompt
        assert "EXEMPLO 2 — Saída" in system_prompt

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        prompt_text = "\n".join(
            value for value in prompt_data.values() if isinstance(value, str)
        )
        assert "[TODO]" not in prompt_text

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt_data.get("techniques_applied")
        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        assert all(isinstance(item, str) and item.strip() for item in techniques)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])