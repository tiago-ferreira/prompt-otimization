# Prompt Optimization Evaluation Specification

## Purpose

Provides a repeatable way to retrieve, improve, publish, and evaluate bug-to-user-story prompts, with observable quality results and validation of the prompt deliverable.

## Requirements

### Requirement: Retrieve the seed prompt
The workflow MUST retrieve the designated seed prompt from the LangSmith Prompt Hub and persist a usable local YAML representation without changing the source prompt.

#### Scenario: Seed prompt retrieval succeeds
- **WHEN** valid LangSmith credentials are configured and the pull workflow is run
- **THEN** the designated `leonanluppi/bug_to_user_story_v1` prompt is saved as `prompts/bug_to_user_story_v1.yml`

#### Scenario: Seed prompt retrieval fails
- **WHEN** credentials are missing, access is denied, or the Hub request fails
- **THEN** the workflow reports the failure and does not report a successful local pull

### Requirement: Produce a validated optimized prompt
The optimized v2 prompt MUST be a usable YAML prompt with distinct system and user instructions, Brazilian Portuguese output, explicit output guidance and edge-case handling, Few-shot examples, and metadata naming at least two prompt-engineering techniques.

#### Scenario: Prompt meets the challenge content requirements
- **WHEN** the prompt validation tests are run against v2
- **THEN** they confirm a non-empty system prompt, a role definition, Brazilian Portuguese user-story output, a required response format, input/output examples, no `[TODO]` markers, and at least two techniques in the YAML metadata

#### Scenario: Prompt handles incomplete bug reports
- **WHEN** an input bug report lacks information needed for a specific user story
- **THEN** the prompt instructs the model to avoid inventing facts and to identify missing information while producing the required structured response

### Requirement: Publish the optimized prompt
The workflow MUST publish the optimized YAML prompt to the configured LangSmith Hub handle under the v2 name and include descriptive metadata for the prompt.

#### Scenario: Prompt publication succeeds
- **WHEN** a valid Hub handle and LangSmith credentials are configured and the push workflow is run
- **THEN** the Hub contains `{handle}/bug_to_user_story_v2` with tags, a description, technique metadata, and public visibility

#### Scenario: Hub handle is unavailable
- **WHEN** the configured handle is absent or the account has not established a public Hub handle
- **THEN** the workflow identifies the missing setup and does not claim that publication succeeded

### Requirement: Evaluate optimized prompts incrementally and resumably
The evaluation workflow MUST report Helpfulness, Correctness, F1-Score, Clarity, and Precision for the optimized prompt against all 15 supplied examples. It MUST process examples in small batches, record valid per-example feedback in LangSmith batch experiments, and persist enough local checkpoint state to resume an interrupted evaluation without repeating completed examples for the same prompt, dataset, provider, and model configuration. Provider or quota failures MUST be reported explicitly and MUST NOT be counted as valid metric scores or as approval. The workflow MUST aggregate scores across the complete set of 15 valid examples before determining approval.

#### Scenario: Evaluation is interrupted by provider quota
- **WHEN** the provider quota is exhausted during a batch
- **THEN** the workflow reports the interruption, preserves valid completed results, does not treat failed examples as scored, and can resume the unfinished examples after quota or provider configuration is restored

#### Scenario: Evaluation resumes with compatible checkpoint state
- **WHEN** the workflow is rerun with the same prompt content, dataset, provider, and model configuration
- **THEN** it skips already completed examples, evaluates only unfinished examples, and retains links to the LangSmith experiments for the batches

#### Scenario: Evaluation identity changes
- **WHEN** the prompt content, dataset, provider, or model configuration differs from the saved checkpoint
- **THEN** the workflow does not combine the old scores with the new run and requires a distinct evaluation state

#### Scenario: All metric thresholds are met
- **WHEN** all 15 examples have valid results and each aggregate metric is at or above 0.8
- **THEN** the evaluation is reported as approved and links to the batch experiments are available

#### Scenario: One or more metric thresholds are missed
- **WHEN** all 15 examples have valid results and any required aggregate metric is below 0.8
- **THEN** the evaluation is reported as not approved, identifies every metric below threshold, and exposes per-example results that can guide another prompt iteration

### Requirement: Document reproducible execution and evidence
The project documentation MUST explain setup, execution, the selected prompt-engineering techniques and their rationale, and the final comparison and evaluation evidence without asserting results that were not observed.

#### Scenario: Results are documented after evaluation
- **WHEN** the implementation is submitted
- **THEN** the README describes how to run the workflow, the changes from v1 to v2, and verifiable LangSmith dataset/experiment evidence including the required evaluation results
