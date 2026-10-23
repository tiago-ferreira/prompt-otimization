import sys
from pathlib import Path

import pytest
from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evaluate_batches import (  # noqa: E402
    CheckpointIdentityMismatch,
    EvaluationInterrupted,
    build_evaluation_identity,
    evaluate_in_batches,
    load_checkpoint,
)


def make_identity(prompt="prompt-v2"):
    return build_evaluation_identity(
        "owner/prompt",
        {"messages": prompt},
        [{"inputs": {"bug_report": "bug"}, "outputs": {"reference": "story"}}],
        "google",
        "generation-model",
        "evaluation-model",
    )


def make_row(score=0.9):
    keys = ["helpfulness", "correctness", "f1_score", "clarity", "precision"]
    return {
        "outputs": {"answer": "story"},
        "evaluation_results": {
            "results": [
                {"key": key, "score": score, "comment": "valid"}
                for key in keys
            ]
        },
    }


def test_checkpoint_refuses_changed_identity(tmp_path):
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text(
        '{"version": 1, "identity": {"prompt_sha256": "old"}, "examples": {}, "experiments": []}',
        encoding="utf-8",
    )

    with pytest.raises(CheckpointIdentityMismatch):
        load_checkpoint(checkpoint_path, make_identity())


def test_langchain_prompt_serialization_is_fingerprinted():
    prompt = ChatPromptTemplate.from_messages(
        [("system", "You write user stories."), ("user", "{bug_report}")]
    )

    identity = build_evaluation_identity(
        "owner/prompt",
        dumpd(prompt),
        [{"inputs": {"bug_report": "bug"}, "outputs": {"reference": "story"}}],
        "google",
        "generation-model",
        "evaluation-model",
    )

    assert identity["prompt_sha256"]


def test_resume_skips_completed_examples(tmp_path):
    identity = make_identity()
    checkpoint = tmp_path / "checkpoint.json"
    calls = []

    def evaluate_batch(batch):
        calls.append(batch)
        return [make_row()], f"https://example.test/{len(calls)}", None

    summary = evaluate_in_batches(
        ["first", "second"],
        identity,
        checkpoint,
        evaluate_batch,
    )
    assert summary["completed_examples"] == 2
    assert len(calls) == 2

    resumed = evaluate_in_batches(
        ["first", "second"],
        identity,
        checkpoint,
        evaluate_batch,
    )
    assert resumed["completed_examples"] == 2
    assert len(calls) == 2


def test_interruption_preserves_prior_batch_for_resume(tmp_path):
    identity = make_identity()
    checkpoint = tmp_path / "checkpoint.json"
    calls = []

    def interrupted_after_first(batch):
        calls.append(batch)
        if len(calls) == 1:
            return [make_row()], "https://example.test/first", None
        return [], "https://example.test/failed", "RESOURCE_EXHAUSTED: quota exceeded"

    with pytest.raises(EvaluationInterrupted, match="Completed examples are saved"):
        evaluate_in_batches(
            ["first", "second"],
            identity,
            checkpoint,
            interrupted_after_first,
        )

    saved = load_checkpoint(checkpoint, identity)
    assert list(saved["examples"]) == ["0"]
    assert saved["examples"]["0"]["scores"]["f1_score"] == 0.9
    assert saved["examples"]["0"]["comments"]["precision"] == "valid"
    assert saved["experiments"][0]["status"] == "complete"
    assert saved["experiments"][0]["url"] == "https://example.test/first"
    assert saved["experiments"][1]["status"] == "incomplete"
    assert saved["experiments"][1]["url"] == "https://example.test/failed"

    resumed_calls = []

    def resume(batch):
        resumed_calls.append(batch)
        return [make_row()], "https://example.test/resumed", None

    summary = evaluate_in_batches(
        ["first", "second"],
        identity,
        checkpoint,
        resume,
    )
    assert resumed_calls == [["second"]]
    assert summary["completed_examples"] == 2


def test_incomplete_metric_feedback_is_not_checkpointed(tmp_path):
    identity = make_identity()
    checkpoint = tmp_path / "checkpoint.json"

    def missing_metric(_batch):
        return [{"evaluation_results": {"results": []}}], "https://example.test/failed", None

    with pytest.raises(EvaluationInterrupted, match="five required metrics"):
        evaluate_in_batches(
            ["first"],
            identity,
            checkpoint,
            missing_metric,
        )

    saved = load_checkpoint(checkpoint, identity)
    assert saved["examples"] == {}
    assert saved["experiments"][0]["status"] == "incomplete"
