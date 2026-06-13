# Module 4 - Evaluation

## Overview

This module covers the full evaluation pipeline for a RAG system built on the LLM Zoomcamp course FAQ dataset. It answers the question: **how good is our retrieval and generation?**

The evaluation is split into three layers: **data generation**, **search (retrieval) evaluation**, **RAG answer evaluation**, and **agent evaluation**.

---

## 1. Ground Truth Data Generation (`data-gen.ipynb`)

### What it does
Generates a ground truth dataset by using an LLM to simulate student questions for each FAQ document.

### Pipeline
1. Load all FAQ documents for the `llm-zoomcamp` course (79 documents).
2. For each document, prompt the LLM (qwen3.5:9b via Ollama) to generate exactly 5 distinct questions a student might ask.
3. Use Pydantic structured output (`Questions` model with `min_length=5, max_length=5`) to enforce the schema.
4. Each generated question is paired with its source document ID to form a ground truth record.
5. Execution is parallelized with `ThreadPoolExecutor` (6 workers) and `map_progress` for progress tracking.

### Output
- `data/ground_truth-new.csv` - 395 records (79 docs x 5 questions), columns: `question`, `document`
- `data/ground-truth-data.csv` - 395 records with an additional `course` column

### Cost tracking
Uses `calc_price` / `calc_total_price` to estimate LLM API costs based on token usage ($0.75/M input, $4.50/M output).

---

## 2. Search Evaluation (`search_eval.ipynb`)

### What it does
Evaluates the **retrieval component** independently of the LLM generation step.

### Methodology
For each ground truth question:
1. Run a text search against the minsearch index (top 5 results).
2. Build a **relevance vector** - a binary list indicating whether each returned document matches the expected ground truth document ID.
   - Example: `[1, 0, 0, 0, 0]` means the correct document was found at rank 1.

### Metrics

| Metric | Definition | Result |
|--------|-----------|--------|
| **Hit Rate** | Fraction of queries where the correct document appears anywhere in the top-k results | **0.8987** (~90%) |
| **MRR** (Mean Reciprocal Rank) | Average of `1/rank` for the first correct result per query | **0.7672** |

### Parameter Tuning
A grid search over boost values for `question`, `answer`, and `section` fields:

- `question_boost`: [1.0, 2.0, 5.0]
- `answer_boost`: [1.0, 2.0, 4.0, 10.0]
- `section_boost`: [0.1, 0.2, 0.5]

**Best configuration** (by MRR):

| question | answer | section | Hit Rate | MRR |
|----------|--------|---------|----------|-----|
| 1.0 | 2.0 | 0.1 | 0.9747 | 0.8838 |
| 2.0 | 4.0 | 0.2 | 0.9747 | 0.8838 |
| 5.0 | 10.0 | 0.5 | 0.9747 | 0.8838 |

Key insight: the **ratio** between boosts matters more than absolute values. The optimal ratio is approximately `question:answer:section = 1:2:0.1`.

---

## 3. RAG Evaluation (`rag_evals.ipynb`)

### What it does
Evaluates the **end-to-end RAG pipeline** (retrieval + LLM generation) using the **LLM-as-a-Judge** pattern.

### Pipeline
1. Generate RAG answers for all 395 ground truth questions using `RAGWithUsage` (extends `RAGBase` with token usage tracking).
2. Answers are generated in parallel (6 workers) and saved to `data/rag-answers-new.csv`.
3. Each answer is evaluated by a second LLM call acting as a judge.

### Evaluation Pattern: A->Q->A'
The judge receives:
- **A** (original answer from FAQ - ground truth)
- **Q** (the student question)
- **A'** (the LLM-generated answer)

The judge decides if A' is **semantically equivalent** to A using a binary `good`/`bad` score with reasoning.

### Judge Rules
- Word-for-word match is NOT required
- Extra detail is acceptable as long as the core answer is correct
- Mark `bad` only if the answer is wrong or misses the key point

### Structured Output
Uses Pydantic `AnswerEvaluation` model with `reasoning` (str) and `score` (Literal["good", "bad"]).

### Results
- **379/395 good = 95.95%** accuracy
- 16 bad answers, mostly due to the LLM hallucinating details not in the context or missing nuanced information

### Output
- `data/rag-answers-new.csv` - generated answers
- `data/rag-evaluations-new.csv` - evaluation scores with reasoning

---

## 4. Agent Evaluation (`Agent_evals.ipynb`)

### What it does
Evaluates an **agent-based** approach where the LLM uses a search tool (function calling) instead of receiving pre-retrieved context.

### Architecture
- Uses the `toyaikit` framework with `OpenAIResponsesRunner`
- The agent has a single tool: `search(query)` which queries the FAQ index
- The agent decides when and how to call the search tool autonomously

### Pipeline
1. Run the agent on 50 ground truth questions (subset for cost/time reasons).
2. Capture the final answer, all tool calls, and cost per question.
3. Evaluate using a two-dimensional judge.

### Evaluation Dimensions

| Dimension | What it measures |
|-----------|-----------------|
| **Answer Score** | Does the agent's final answer match the ground truth? |
| **Trajectory Score** | Were the tool calls (search queries) relevant, non-redundant, and well-formed? |

### Trajectory Evaluation Criteria
- Search queries should include important keywords from the question
- Avoid duplicate or unnecessary tool calls
- 1 call is usually enough, 2-3 can be okay, >3 needs justification
- Tool calls should support the final answer

### Results (50 questions)
- **Answer: 45/50 good (90%)**
- **Trajectory: 49/50 good (98%)**

### Output
- `data/agent-answers.csv` - agent responses with tool calls and costs
- `data/agent-evaluations.csv` - dual-score evaluations

---

## Utility Module (`evaluation_utils.py`)

| Function/Class | Purpose |
|----------------|---------|
| `calc_price(usage)` | Calculate dollar cost from token usage |
| `calc_total_price(usages)` | Sum costs across multiple usages |
| `llm_structured(client, instructions, prompt, output_type)` | Call LLM with Pydantic structured output |
| `llm_structured_retry(...)` | Same as above with exponential backoff (max 3 retries) |
| `RAGWithUsage` | Extends `RAGBase` to track token usage per call |
| `map_progress(pool, seq, f)` | Parallel map with tqdm progress bar |

---

## Key Concepts Reference

### Hit Rate vs MRR
- **Hit Rate** tells you *whether* the system finds the right document (binary per query).
- **MRR** tells you *how quickly* it finds it (penalizes lower-ranked correct results).
- A system with hit rate 1.0 but MRR 0.5 finds the document every time but usually at rank 2+.

### LLM-as-a-Judge
- Replaces expensive human evaluation with automated LLM scoring.
- Works well for factual correctness but can miss tone, verbosity, or subtle errors.
- Using structured output (Pydantic) ensures consistent, parseable evaluations.
- The A->Q->A' pattern gives the judge both the ground truth and the generated answer for comparison.

### Binary vs Graded Evaluation
This module uses binary `good`/`bad` scoring. Alternatives include:
- **Likert scale** (1-5) for more granular quality measurement
- **Pairwise comparison** (A vs B) for ranking different systems
- **Rubric-based** scoring with separate dimensions (correctness, completeness, relevance)

### Token Cost Estimation
The pricing model used ($0.75/M input, $4.50/M output) corresponds to a mid-tier model. For Ollama (local), the actual cost is compute time, not API tokens. The cost tracking is useful for estimating what cloud deployment would cost.

### Retrieval vs Generation Evaluation
- **Search evaluation** (Hit Rate, MRR) isolates the retrieval component.
- **RAG evaluation** (LLM-as-a-Judge) evaluates the full pipeline.
- A system can have good retrieval but bad generation (poor prompt, bad model) or vice versa. Evaluating both independently helps diagnose issues.

---

## Data Files Summary

| File | Records | Description |
|------|---------|-------------|
| `ground_truth-new.csv` | 395 | Generated questions + document IDs |
| `ground-truth-data.csv` | 395 | Same with course column |
| `rag-answers-new.csv` | 395 | RAG-generated answers with ground truth |
| `rag-evaluations-new.csv` | 395 | LLM judge scores for RAG answers |
| `agent-answers.csv` | 50 | Agent answers with tool calls and costs |
| `agent-evaluations.csv` | 50 | Dual-score evaluations for agent |

---

## Prerequisites

- Ollama running locally at `localhost:11434` with `qwen3.5:9b` model pulled
- Elasticsearch (for `ElasticRAG` variant, optional)
- Python 3.12+, dependencies in `pyproject.toml`
