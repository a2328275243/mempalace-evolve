"""LLM-backed memory consolidation pipeline for MemPalace.

This module provides an optional LLM-powered pipeline for:
  - Candidate extraction from conversation transcripts
  - Memory review and quality scoring
  - Memory consolidation (merging similar, detecting contradictions)
  - Summarization of daily memories

All LLM features are optional — the system falls back gracefully
to rule-based heuristics when no LLM backend is configured.

Architecture:
  1. Candidate Extraction (LLM) — identify potential memories from raw text
  2. Review & Score (LLM) — assess importance, detect contradictions
  3. Consolidation (LLM) — merge near-duplicates, resolve conflicts
  4. Summarization (LLM) — generate structured daily digests

Each step accepts a structured output schema and validates results.
The pipeline is designed to work with any LLM provider via a common
client interface (OpenAI-compatible API).
"""
