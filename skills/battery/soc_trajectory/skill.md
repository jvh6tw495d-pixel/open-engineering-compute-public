---
id: battery.soc_trajectory
version: 0.1.0
status: experimental
domain: battery
title: Battery SOC Trajectory (Energy-Based)
---

# Purpose

Multi-step **energy-based** SOC trajectory for a BESS power schedule.
Maps to `oec.physics.storage.storage_trajectory` (power × time × η /
energy capacity). **Not** coulomb-counting (current/Ah).

Legacy single-step `battery.soc_step` is unchanged (D6).

# Official methodology

Method id: `energy_based_storage_trajectory`.

# Changelog

- 0.1.0: initial (v2.6.1 Wave 2).
