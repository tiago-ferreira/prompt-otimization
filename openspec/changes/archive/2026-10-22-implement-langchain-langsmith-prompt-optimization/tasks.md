# Tasks

## 1. Confirm Starter Repository and Pull the Seed Prompt

- [x] 1.1 Inspect the referenced starter repository's `src/pull_prompts.py`, prompt YAML format, `.env.example`, dependencies, and existing README; verify the actual interfaces and environment-variable names before implementation.
- [x] 1.2 Implement and run the seed-prompt pull using the repository's existing conventions; verify `prompts/bug_to_user_story_v1.yml` is loadable YAML and the LangSmith request uses the required public-prompt opt-in.
- [x] 1.3 Document credential setup, public-handle prerequisites, and the pull command in the README; verify each documented filename and command against the starter repository.

## 2. Author and Validate the Optimized Prompt

- [x] 2.1 Create `prompts/bug_to_user_story_v2.yml` with Brazilian Portuguese system/user instructions, role and output-format rules, few-shot input/output examples, edge-case handling, and metadata for at least two techniques; verify the YAML parses and contains no `[TODO]`.
- [x] 2.2 Implement the six required prompt validation tests against the repository's actual YAML structure; run `pytest tests/test_prompts.py` and verify the system prompt, role, format, examples, TODO absence, and technique metadata checks pass.
- [x] 2.3 Document the selected techniques, rationale, practical application, and v1-to-v2 prompt changes in the README; verify the documentation describes the actual v2 prompt.

## 3. Publish the Optimized Prompt

- [x] 3.1 Implement the push workflow using the verified prompt schema and configured Hub handle; run it with valid credentials and verify `{handle}/bug_to_user_story_v2` is published with tags, description, technique metadata, and public visibility.
- [x] 3.2 Document the push command, required Hub setup, and publication metadata in the README; verify the instructions match the implemented command and never expose credentials.

## 4. Evaluate, Iterate, and Record Evidence

- [x] 4.1 Implement a separate quota-aware batch evaluation runner that reuses the existing evaluation/metric behavior, checkpoints valid per-example results by prompt/dataset/provider/model identity, stops explicitly on quota errors, resumes only unfinished examples, and never changes `src/evaluate.py`, `src/metrics.py`, `src/utils.py`, or the supplied dataset; add focused tests for checkpoint identity, resumption, and interrupted runs.
- [x] 4.2 Run the batch evaluator and inspect its per-example feedback and LangSmith experiment link; verify a simulated or observed interruption preserves completed examples and a resumed run does not evaluate them again.
- [x] 4.3 Complete evaluation of all 15 examples and inspect the five aggregate metric results; verify every example has valid LangSmith feedback and the combined batch-experiment links correspond to the final prompt and provider/model configuration.
- [x] 4.4 Iterate on v2 using completed per-example metric feedback for approximately three to five evaluation runs, continuing if necessary until Helpfulness, Correctness, F1-Score, Clarity, and Precision are each at least 0.8 across all 15 examples; verify the final aggregate results meet every threshold.
- [x] 4.5 Share the evaluation dataset intentionally and collect its public link, links for all final batch experiments, screenshots showing all final aggregate scores at or above 0.8, and traces for at least three examples; verify the links open as intended and the evidence reflects the final evaluation.
- [x] 4.6 Document the observed final aggregate scores, public dataset and batch-experiment links, screenshots, and model/provider context in the README; verify every reported score and URL against the actual LangSmith results.

## 5. Verify the Complete Deliverable

- [x] 5.1 Follow the README setup and execution steps from a clean environment with credentials supplied outside tracked files; verify pull, prompt tests, push, batch evaluation, and resumption work in the documented order.
- [x] 5.2 Confirm the existing evaluator, metric, utility, and dataset files remain unchanged and run the repository's relevant test suite; verify all applicable tests pass and no credentials are tracked.
