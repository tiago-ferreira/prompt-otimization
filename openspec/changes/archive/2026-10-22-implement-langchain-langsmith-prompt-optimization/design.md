# Design

## Context

See `proposal.md` for motivation and `specs/prompt-optimization-evaluation/spec.md` for externally visible requirements. The challenge brief identifies an existing evaluation and metrics implementation, a 15-example dataset, and skeleton pull/push scripts in a separate starter repository. That repository is not present in this workspace; its actual data structures, serialization format, environment-variable names, and script interfaces remain unverified and must be inspected before implementation.

## Goals / Non-Goals

**Goals:**

- Keep the existing evaluation, metric, utility, and dataset behavior intact while connecting prompt retrieval, optimization, and publication to it.
- Keep prompt content and technique metadata in the specified YAML artifact so that tests, publication, and documentation use the same source.
- Make external side effects and evaluation outcomes visible and accurately reported.

**Non-Goals:**

- Reimplement or alter the provided dataset, evaluator, metrics, or utility modules.
- Automatically guarantee a metric score independent of model/provider behavior or claim approval without recorded evaluation evidence.
- Commit credentials, make a private dataset public implicitly, or automate creation of the user's LangSmith public handle.

## Decisions

1. **Treat the starter repository as the source of truth for integration details.** Before coding, inspect its skeleton scripts, YAML schema, evaluation entry point, tests, and environment configuration. Adapt to existing interfaces rather than assuming function names or inventing a parallel application structure. The brief alone establishes the expected deliverables and behavior, not these internal contracts.

2. **Use one optimized YAML prompt as the authoring source.** Keep the system and user messages, few-shot examples, edge-case rules, formatting expectations, and metadata together in `prompts/bug_to_user_story_v2.yml`. The prompt should apply Few-shot Learning and at least one additional technique, and metadata should enumerate at least two techniques to satisfy the stated validation rule. This avoids separate prompt definitions drifting between evaluation and push.

3. **Separate local authoring from LangSmith side effects.** Pull and push remain explicit CLI actions, driven by configured credentials and the user's pre-created Hub handle. Retrieval of the seed prompt must use the opt-in permission required for public serialized prompts. Publication should use the starter's supported visibility mechanism and report failures rather than treating a local YAML read as a successful push. Public dataset sharing is a deliberate evidence-generation step, not an implicit side effect of every evaluation.

4. **Preserve the existing evaluator inputs and add resumable orchestration.** Keep `src/evaluate.py`, `src/metrics.py`, `src/utils.py`, and the supplied JSONL dataset unchanged. Add a separate batch runner that evaluates a small number of examples per LangSmith experiment and stores completed per-example outputs and metric feedback in local checkpoint state. Bind checkpoint state to the prompt content, dataset, provider, and model configuration so results cannot be mixed across materially different runs. Stop clearly on quota/provider errors, retain only valid completed results, and resume by skipping examples already completed for the same run identity. Report approval only after all 15 examples have valid results and the aggregate of each required metric is at least 0.8. The brief expects approximately three to five prompt iterations; continue beyond that if needed, and report the observed results and links to all relevant batch experiments instead of promising a score before provider-backed evaluation.

5. **Validate the YAML prompt contract with focused tests.** Implement the six checks listed in the brief for the system prompt, role, output format, few-shot examples, absence of TODO markers, and at least two technique metadata entries. Use the repository's actual serialization shape once inspected.

6. **Write generated user stories in Brazilian Portuguese.** The user confirmed this language behavior, and it matches the language of the challenge brief.

## Risks / Trade-offs

- [Provider quotas can interrupt a full evaluation and invalidate partial feedback] → Use small batches, atomically persist completed examples, stop on quota errors without treating them as valid scores, and resume only the unfinished examples for the same prompt/dataset/provider/model identity.
- [Provider outputs and metric scores can vary by model, configuration, or API changes] → Record model/provider configuration with results where supported, preserve links to all batch experiments, and iterate from per-metric feedback; do not treat partial or prompt-only tests as proof of the 0.8 target.
- [The starter repository may use a YAML schema or interfaces different from assumptions in the brief] → Inspect the target repository before implementation and integrate through its existing helpers and script skeletons.
- [Publishing or sharing results exposes artifacts beyond the local project] → Require deliberate configuration and clearly distinguish public prompt publication from dataset sharing; never write secrets into files or evidence.
- [A Hub handle is account-specific and must be created externally] → Document the required manual setup and fail clearly when the configured handle is unavailable.

## Migration Plan

No data migration is expected. Set up credentials and the public Hub handle outside the repository, pull the seed prompt, author and validate v2, publish it, then run the batch evaluator. If quota is exhausted, restore quota or configure a supported provider/model and resume the same compatible checkpoint; start a distinct evaluation state when the prompt, dataset, provider, or model changes. Intentionally share the dataset only when creating public evidence, and report the collection of batch experiment links. Rollback consists of stopping use of v2 and leaving the original v1 prompt and supplied evaluation inputs unchanged; remove or deprecate the published v2 Hub prompt through the LangSmith interface if necessary.

## Open Questions

- Confirm the starter repository's YAML shape, credential variable names, and push visibility support during implementation; these details do not change the specified behavior or architecture.
