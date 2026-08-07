---
id: chemistry.fick_flux
version: 0.1.0
status: experimental
domain: chemistry
title: 1D Fick Diffusion Flux
---

# Purpose

Species transport wave-0: finite-difference Fick flux between two
concentration nodes. Thin wrap over `oec.chemistry.fick_flux_1d`.

# Formula

`J = −D · (c_B − c_A) / Δx`
