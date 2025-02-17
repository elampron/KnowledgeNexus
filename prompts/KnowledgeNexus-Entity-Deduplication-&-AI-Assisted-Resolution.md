# KnowledgeNexus – Entity Deduplication & AI-Assisted Resolution

This document provides detailed specs for implementing **entity deduplication** and **AI-driven entity resolution** in the KnowledgeNexus system. By combining fuzzy matching, LLM-powered decisions, and robust graph relationships, we aim to maintain a unified knowledge graph with minimal duplication.

---

## 1. Core Requirements

1. **Prevent Duplicate Entities**: The system must avoid creating redundant nodes for the same real-world entity.
2. **Fuzzy Matching Support**: Use alias tracking, string similarity algorithms, and vector embeddings to handle name variations.
3. **LLM Decision**: For ambiguous matches, query GPT models to decide whether two entities are the same, providing a confidence score.
4. **Confidence Thresholds**: Define lower/upper thresholds for auto-merge, auto-distinct, and a gray zone requiring extra analysis.
5. **Human-in-the-Loop**: Provide a way to manually review ambiguous cases.
6. **Relationship Inference**: Let AI infer new relationships from text or graph structure.

---

## 2. Proposed Architecture Overview

We extend the existing KnowledgeNexus architecture to include an **Entity Resolution Pipeline** with four major stages:

1. **Ingestion**: Data arrives through watchers, CLI, or file uploads (later). The system extracts candidate entities using the LLM.
2. **Fuzzy Matching & Thresholding**:
   - Compute multiple similarity scores (string-based, embedding-based, alias-based).
   - If total score ≥ `upperThreshold` (e.g. 0.9) → auto-merge.
   - If total score ≤ `lowerThreshold` (e.g. 0.5) → treat as a new entity.
   - Otherwise, forward to **AI-Assisted** or **Manual** resolution.
3. **AI-Assisted Resolution**:
   - Prompt GPT with both entity records to see if they refer to the same real-world object.
   - GPT returns **YES/NO** and a **confidence**. If high confidence in “YES,” merge. If “NO,” keep separate. If uncertain, queue for manual review.
4. **Relationship Inference**:
   - As an optional step, let LLM or a link-prediction model infer relationships between newly added/merged entities and existing nodes.

---

## 3. Fuzzy Matching Engine

1. **Alias Management**:
   - Store known aliases (e.g., abbreviations, alternate spellings, former names) in entity properties.
   - Each alias is also vectorized for semantic similarity.

2. **String Similarity Methods**:
   - **Levenshtein or Jaro-Winkler** for textual differences.
   - **Metaphone** or phonetic approach for names.

3. **Vector Embedding**:
   - Generate embeddings for names/aliases with a sentence transformer or GPT embedding endpoint.
   - Compare embeddings via cosine similarity.

4. **Score Aggregation**:
   - Weighted sum of textual and embedding similarity scores.
   - Compare to thresholds (`upperThreshold`, `lowerThreshold`).

---

## 4. AI-Assisted Resolution

1. **Decision Prompt**:
   - Provide both entity’s data (name, aliases, type, partial profile) to GPT.
   - Ask: *“Are these two entries the same entity? Please return `{"match": (yes/no), "confidence": float, "reason": string}`.”*

2. **Interpreting the Response**:
   - If `match=yes` and `confidence >= X%`, auto-merge.
   - If `match=no` with strong confidence, keep them distinct.
   - If uncertain, log it for human review.

3. **Implementation Detail**:
   - Leverage a library that supports `response_model` or parse JSON carefully.
   - Store the LLM’s confidence and reason for auditing.

---

## 5. Deduplication Workflow Example

1. **Entity Extraction**: Input text mentions "Marie-Eve Girard". The pipeline extracts an entity.
2. **Fuzzy Check**: The system sees an existing node "Marie Eve G." that is 0.85 similar.
3. **Threshold**: 0.85 is < 0.9 upper threshold and > 0.5 lower threshold → ambiguous.
4. **AI-Assisted**: System prompts GPT:
   ```json
   {
     "entityA": {"name": "Marie-Eve Girard"...},
     "entityB": {"name": "Marie Eve G."...}
   }
   ```
   GPT responds `{"match": "yes", "confidence": 0.92, "reason": "Same name, slight variation."}`.
5. **Auto-Merge**: Because confidence (0.92) is >= 0.9, the pipeline merges them.
6. **Relationship Inference**: If the text also states "Marie-Eve is my girlfriend," the system might add a `RELATIONSHIP` between the user entity and the entity node with a label `[GirlfriendOf]` or something similar.

---

## 6. Relationship Inference

1. **NLP Extraction**: For each chunk of text, prompt GPT or run an extraction pipeline to identify subject, predicate, and object.
2. **Graph Update**: For each triple, create or merge a relationship in Neo4j (e.g., `(subject)-[RELATION]->(object)`).
3. **Confidence**: Tag each relationship with a confidence score. If confidence is below a threshold, queue for review.

---

## 7. Manual Review & UI

1. **Ambiguity Queue**: Entities that remain ambiguous or have conflicting data appear in a review queue.
2. **UI Tools**: Provide side-by-side comparison, show fuzzy match scores, GPT verdict, etc.
3. **Reviewer Action**: Merge or keep distinct. The system logs that decision.
4. **Feedback Loop**: Optionally update thresholds or train an ML model on these decisions.

---

## 8. Implementation Notes

- **Configuration**: Store thresholds (`upperThreshold`, `lowerThreshold`), AI model usage, LLM prompt templates, and synonyms/aliases in a config file.
- **Performance**: Use a blocking or indexing strategy to limit pairwise comparisons in large datasets.
- **Logging & Audit**: Log each step of the resolution pipeline. Keep track of merges, LLM calls, and manual review outcomes.
- **Scalability**: For large-scale entity resolution, consider a distributed approach or a specialized library (e.g., Apache Spark for offline matching). For the prototype, simpler in-memory or Neo4j-based solutions suffice.

---

## 9. Next Steps

1. **Implement Fuzzy Matching**:
   - Integrate string similarity + vector embeddings.
   - Summarize into an overall similarity score.
2. **Add AI-Assisted Stage**:
   - Build GPT prompt logic.
   - Parse JSON output for `match` and `confidence`.
3. **Develop Relationship Extraction**:
   - Extend existing pipeline to parse relationships from text.
   - Store relationships in Neo4j.
4. **Manual Review UI** (optional in the prototype, but essential for production).
5. **Tune Thresholds & Evaluate**:
   - Adjust thresholds based on real usage.
   - Build a test set of known duplicates to measure precision/recall.

---

By following these specs, KnowledgeNexus gains a robust *deduplication and entity resolution pipeline*, preventing data clutter and ensuring a comprehensive, high-quality personal knowledge system.

