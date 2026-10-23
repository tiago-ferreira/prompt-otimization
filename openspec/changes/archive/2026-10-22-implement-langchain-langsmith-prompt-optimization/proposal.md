# Proposal

## Why

The challenge currently defines a manual, multi-stage workflow for improving bug-to-user-story prompts, but completing it reliably requires local prompt management, LangSmith publishing, repeatable evaluation, and clear validation. This change will turn those requirements into a usable workflow and make the quality target measurable through recorded experiments and tests.

## What Changes

- Add a local workflow to pull the seed prompt from LangSmith Prompt Hub and save it as YAML.
- Add an optimized v2 YAML prompt that uses Few-shot Learning and at least one additional prompt-engineering technique, with explicit formatting, behavior, and edge-case guidance.
- Add a workflow to publish v2 prompts to the user's LangSmith Hub with versioned naming and descriptive metadata.
- Add a quota-aware, resumable evaluation runner that processes the supplied 15-example dataset in small batches, preserves completed per-example results across interruptions, and supports prompt iteration until every required metric meets the 0.8 threshold.
- Add automated prompt validation tests and document setup, selected techniques, execution, and final evaluation evidence in the README.
- Preserve the supplied evaluation, metric, utility, and dataset files as-is.

## Capabilities

### New Capabilities

- `prompt-optimization-evaluation`: Manage the prompt optimization lifecycle from LangSmith pull through YAML-based optimization, publishing, and metric-based evaluation.

### Modified Capabilities

None.

## Impact

The implementation target is the `devfullcycle/mba-ia-pull-evaluation-prompt` starter repository referenced by the challenge brief. Expected areas include `src/pull_prompts.py`, `src/push_prompts.py`, a quota-aware batch evaluation runner, `prompts/bug_to_user_story_v2.yml`, prompt and runner tests, and `README.md`; `src/evaluate.py`, `src/metrics.py`, `src/utils.py`, and `datasets/bug_to_user_story.jsonl` remain unchanged inputs. LangChain, LangSmith, local resumable evaluation state, and the selected LLM provider credentials/models are involved. Metric thresholds depend on provider/model behavior and must be demonstrated by actual evaluation runs rather than assumed from prompt content.
