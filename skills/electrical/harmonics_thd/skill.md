---
id: electrical.harmonics_thd
version: 0.1.0
status: experimental
domain: electrical
title: Total Harmonic Distortion (THD-F)
---

# Purpose

Compute THD-F from a fundamental magnitude and a list of harmonic
magnitudes. Thin wrap over `oec.physics.harmonics.total_harmonic_distortion`.
Does **not** perform FFT on a waveform.
