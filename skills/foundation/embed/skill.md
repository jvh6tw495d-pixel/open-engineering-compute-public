---
id: foundation.embed
version: 0.1.1
status: validated
domain: foundation
title: Text Embeddings (builtin hash or transformers)
---

# Purpose

Embed text with a closed backend catalog. ``builtin_hash`` is an OEC-owned
deterministic vector (not an LLM). ``transformers`` requires ``oec[foundation]``.

# Official methodology

Method id: `foundation_embed`.

# Changelog

- 0.1.1: validated — `builtin_hash` golden is a deterministic reference
  vector, not an "error OR success" placeholder.
- 0.1.0: W6 initial.
