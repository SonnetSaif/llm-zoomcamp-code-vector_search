# 8_faq_rag_pipeline

## Overview
Course FAQ assistant that compares non-RAG baseline vs RAG-grounded answer.

## Why this flow matters
Shows how domain documents improve support-answer reliability over generic model responses.

## Flow definition
- YAML: `8_faq_rag_pipeline.yaml`
- Namespace/ID: `zoomcamp.8_faq_rag_pipeline`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- Network access to DataTalksClub GitHub raw docs

## Inputs
- `student_question`: learner question

## How it works
1. `baseline_answer` generates a generic answer without retrieval.
2. `ingest_course_docs` embeds course README/module docs.
3. `rag_answer` retrieves relevant chunks and answers from course context.
4. `log_comparison` prints both answers for side-by-side review.

## Step-by-step tutorial
1. Run `zoomcamp.8_faq_rag_pipeline` with default question.
2. Compare baseline and RAG outputs in `log_comparison`.
3. Re-run with additional policy/process questions.

## Expected outcome (what to verify)
- RAG output is more course-specific and less generic than baseline.
- Answers are better aligned with documented course policies.

## Troubleshooting
- If RAG output is weak, verify ingest URL reachability.
- Verify Gemini API key.

## Next recommended flow
- Run `9_llm_evaluation.yaml` to score baseline vs RAG quality automatically.
