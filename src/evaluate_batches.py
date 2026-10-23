"""Quota-aware, resumable evaluation of optimized prompts."""

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from langsmith import Client
from langchain_core.load import dumpd

from evaluate import (
    APPROVAL_THRESHOLD,
    METRIC_KEYS,
    build_target,
    create_evaluation_dataset,
    evaluate_all_metrics,
    get_llm,
    load_dataset_from_jsonl,
    pull_prompt_from_langsmith,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "datasets" / "bug_to_user_story.jsonl"

load_dotenv(PROJECT_ROOT / ".env")


class EvaluationInterrupted(RuntimeError):
    """Raised when a batch cannot produce complete, valid metric feedback."""


class CheckpointIdentityMismatch(ValueError):
    """Raised when an explicit checkpoint belongs to a different evaluation."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_evaluation_identity(
    prompt_name: str,
    prompt_serialized: Any,
    examples: list[dict[str, Any]],
    provider: str,
    llm_model: str,
    eval_model: str,
) -> dict[str, str]:
    return {
        "prompt_name": prompt_name,
        "prompt_sha256": _sha256(_canonical_json(prompt_serialized)),
        "dataset_sha256": _sha256(_canonical_json(examples)),
        "provider": provider,
        "llm_model": llm_model,
        "eval_model": eval_model,
    }


def default_checkpoint_path(identity: dict[str, str]) -> Path:
    digest = _sha256(_canonical_json(identity))
    return PROJECT_ROOT / ".evaluation-state" / f"{digest}.json"


def load_checkpoint(
    path: Path, identity: dict[str, str]
) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": 1,
            "identity": identity,
            "examples": {},
            "experiments": [],
        }

    checkpoint = json.loads(path.read_text(encoding="utf-8"))
    if checkpoint.get("identity") != identity:
        raise CheckpointIdentityMismatch(
            f"Checkpoint {path} belongs to a different prompt, dataset, "
            "provider, or model configuration. Use its identity-specific "
            "checkpoint or choose a new checkpoint path."
        )
    if checkpoint.get("version") != 1:
        raise ValueError(f"Unsupported checkpoint version in {path}.")
    return checkpoint


def save_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(checkpoint, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _field(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _metric_results(row: Any) -> dict[str, dict[str, Any]]:
    run = _field(row, "run")
    if _field(run, "error"):
        raise EvaluationInterrupted(f"Target run failed: {_field(run, 'error')}")

    evaluation_results = _field(row, "evaluation_results", {}) or {}
    raw_results = _field(evaluation_results, "results", []) or []
    metrics = {}
    for result in raw_results:
        key = _field(result, "key")
        if key in METRIC_KEYS:
            metrics[key] = {
                "score": _field(result, "score"),
                "comment": _field(result, "comment", "") or "",
            }

    if set(metrics) != set(METRIC_KEYS):
        raise EvaluationInterrupted(
            "Batch did not return valid feedback for all five required metrics."
        )

    for key, metric in metrics.items():
        comment = metric["comment"].strip().lower()
        if comment.startswith(("erro na avaliação:", "erro ao processar resposta")):
            raise EvaluationInterrupted(
                f"{key} evaluator failed: {metric['comment']}"
            )
        score = metric["score"]
        if (
            isinstance(score, bool)
            or not isinstance(score, (float, int))
            or not math.isfinite(score)
            or not 0 <= score <= 1
        ):
            raise EvaluationInterrupted(f"{key} returned an invalid score.")
        metric["score"] = float(score)
    return metrics


def evaluate_in_batches(
    examples: list[Any],
    identity: dict[str, str],
    checkpoint_path: Path,
    evaluate_batch: Callable[[list[Any]], tuple[Any, str | None, str | None]],
) -> dict[str, Any]:
    checkpoint = load_checkpoint(checkpoint_path, identity)
    total = len(examples)

    for index, example in enumerate(examples):
        if str(index) in checkpoint["examples"]:
            continue
        indices = [index]

        batch = [example]
        try:
            results, experiment_url, failure = evaluate_batch(batch)
            experiment = {
                "url": experiment_url,
                "example_indices": indices,
                "status": "incomplete",
            }
            if experiment not in checkpoint["experiments"]:
                checkpoint["experiments"].append(experiment)
                save_checkpoint(checkpoint_path, checkpoint)

            if failure:
                raise EvaluationInterrupted(failure)
            if len(results) != len(batch):
                raise EvaluationInterrupted(
                    f"Expected {len(batch)} result(s), received {len(results)}."
                )

            for index, row in zip(indices, results):
                metrics = _metric_results(row)
                outputs = _field(row, "outputs", {}) or {}
                checkpoint["examples"][str(index)] = {
                    "scores": {
                        key: metric["score"] for key, metric in metrics.items()
                    },
                    "comments": {
                        key: metric["comment"] for key, metric in metrics.items()
                    },
                    "answer": outputs.get("answer", ""),
                }
                save_checkpoint(checkpoint_path, checkpoint)

            experiment["status"] = "complete"
            save_checkpoint(checkpoint_path, checkpoint)
            print(
                f"Saved examples {indices[0] + 1}-{indices[-1] + 1}/{total}"
                + (f": {experiment_url}" if experiment_url else "")
            )
        except Exception as error:
            raise EvaluationInterrupted(
                f"Evaluation paused at example(s) "
                f"{', '.join(str(index + 1) for index in indices)}: {error}. "
                f"Completed examples are saved in {checkpoint_path}."
            ) from error

    completed = checkpoint["examples"]
    scores = {
        key: round(
            sum(item["scores"][key] for item in completed.values()) / len(completed),
            4,
        )
        for key in METRIC_KEYS
    } if completed else {key: 0.0 for key in METRIC_KEYS}
    all_examples_complete = len(completed) == total
    passed = all_examples_complete and all(
        score >= APPROVAL_THRESHOLD for score in scores.values()
    )
    return {
        "scores": scores,
        "completed_examples": len(completed),
        "total_examples": total,
        "passed": passed,
        "experiments": checkpoint["experiments"],
        "checkpoint_path": str(checkpoint_path),
    }


def _remote_examples(client: Client, dataset_name: str, local_examples: list[dict]):
    dataset = client.read_dataset(dataset_name=dataset_name)
    remote_examples = list(client.list_examples(dataset_id=dataset.id))
    remaining = {}
    for remote in remote_examples:
        key = _canonical_json({"inputs": remote.inputs, "outputs": remote.outputs})
        remaining.setdefault(key, []).append(remote)

    paired = []
    for example in local_examples:
        key = _canonical_json(
            {"inputs": example["inputs"], "outputs": example["outputs"]}
        )
        if key not in remaining or not remaining[key]:
            raise ValueError(
                f"LangSmith dataset '{dataset_name}' does not match the local JSONL dataset."
            )
        paired.append(remaining[key].pop())

    if len(remote_examples) != len(local_examples) or any(remaining.values()):
        raise ValueError(
            f"LangSmith dataset '{dataset_name}' does not contain exactly the "
            f"{len(local_examples)} supplied examples."
        )
    return paired


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the v2 prompt in resumable LangSmith batches."
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Optional explicit checkpoint path; it must match this evaluation identity.",
    )
    args = parser.parse_args()

    provider = os.getenv("LLM_PROVIDER", "")
    llm_model = os.getenv("LLM_MODEL", "")
    eval_model = os.getenv("EVAL_MODEL", "")
    username = os.getenv("USERNAME_LANGSMITH_HUB", "")
    project_name = os.getenv("LANGSMITH_PROJECT", "")
    if not all((provider, llm_model, eval_model, username, project_name)):
        print(
            "Missing required environment variables: LLM_PROVIDER, LLM_MODEL, "
            "EVAL_MODEL, USERNAME_LANGSMITH_HUB, LANGSMITH_PROJECT."
        )
        return 1

    local_examples = load_dataset_from_jsonl(str(DATASET_PATH))
    if not local_examples:
        print(f"No examples were loaded from {DATASET_PATH}.")
        return 1

    client = Client()
    dataset_name = f"{project_name}-eval"
    create_evaluation_dataset(client, dataset_name, str(DATASET_PATH))
    examples = _remote_examples(client, dataset_name, local_examples)

    prompt_name = f"{username}/bug_to_user_story_v2"
    prompt_template = pull_prompt_from_langsmith(client, prompt_name)
    prompt_serialized = dumpd(prompt_template)
    identity = build_evaluation_identity(
        prompt_name,
        prompt_serialized,
        local_examples,
        provider,
        llm_model,
        eval_model,
    )
    checkpoint_path = args.checkpoint or default_checkpoint_path(identity)
    target = build_target(prompt_template, get_llm())
    target_errors = []
    metric_errors = []

    def guarded_target(inputs: dict) -> dict:
        try:
            return target(inputs)
        except Exception as error:
            target_errors.append(error)
            raise

    def strict_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
        result = evaluate_all_metrics(inputs, outputs, reference_outputs)
        for item in result.get("results", []):
            comment = str(item.get("comment", "")).strip().lower()
            if comment.startswith(
                ("erro na avaliação:", "erro ao processar resposta")
            ):
                metric_errors.append(item["comment"])
                raise RuntimeError(item["comment"])
        return result

    def evaluate_batch(batch: list[Any]):
        target_errors.clear()
        metric_errors.clear()
        results = client.evaluate(
            guarded_target,
            data=batch,
            evaluators=[strict_evaluator],
            experiment_prefix=prompt_name.replace("/", "-") + "-batch",
            max_concurrency=1,
            error_handling="log",
            metadata={
                **identity,
                "batch_size": len(batch),
            },
        )
        failures = target_errors + metric_errors
        return list(results), str(results.url) if results.url else None, (
            str(failures[0]) if failures else None
        )

    try:
        summary = evaluate_in_batches(
            examples,
            identity,
            checkpoint_path,
            evaluate_batch,
        )
    except Exception as error:
        print(f"Evaluation paused; completed examples remain checkpointed: {error}")
        return 1

    print(
        f"\nCompleted examples: {summary['completed_examples']}/"
        f"{summary['total_examples']}"
    )
    for key, score in summary["scores"].items():
        print(f"{key}: {score:.4f}")
    print(f"Checkpoint: {summary['checkpoint_path']}")
    for experiment in summary["experiments"]:
        if experiment.get("url"):
            print(f"Experiment: {experiment['url']}")

    if not summary["passed"]:
        below = [
            key
            for key, score in summary["scores"].items()
            if score < APPROVAL_THRESHOLD
        ]
        print("STATUS: NOT APPROVED")
        if summary["completed_examples"] < summary["total_examples"]:
            print("Evaluation is incomplete; rerun to resume remaining examples.")
        if below:
            print("Metrics below threshold: " + ", ".join(below))
        return 1

    print("STATUS: APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
