import sys
from pathlib import Path

from langsmith.utils import LangSmithConflictError

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from push_prompts import push_prompt_to_langsmith  # noqa: E402


class FailedPushClient:
    def __init__(self, error):
        self.error = error

    def push_prompt(self, *args, **kwargs):
        raise self.error


def valid_prompt():
    return {
        "description": "Bug report prompt",
        "system_prompt": "You write user stories.",
        "user_prompt": "{bug_report}",
        "version": "v2",
        "techniques_applied": ["Few-shot Learning", "Role Prompting"],
    }


def test_unchanged_published_prompt_is_successful(capsys):
    client = FailedPushClient(
        LangSmithConflictError(
            "Nothing to commit: prompt has not changed since latest commit"
        )
    )

    assert push_prompt_to_langsmith(
        "owner/bug_to_user_story_v2",
        valid_prompt(),
        client=client,
    )
    assert "já está publicado sem alterações" in capsys.readouterr().out


def test_other_push_http_errors_remain_failures(capsys):
    client = FailedPushClient(LangSmithConflictError("Unexpected conflict"))

    assert not push_prompt_to_langsmith(
        "owner/bug_to_user_story_v2",
        valid_prompt(),
        client=client,
    )
    assert "Falha ao publicar" in capsys.readouterr().out
