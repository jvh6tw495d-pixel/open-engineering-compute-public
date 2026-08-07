---
id: energy.pv_power
version: 0.1.0
status: experimental
domain: energy
title: Photovoltaic Instantaneous Power
---

# Purpose

Generic instantaneous PV power: `P = G × A × η × f_temp`. Thin adapter over
`oec.physics.pv.pv_power`. No IAM, soiling, shading, or inverter clipping.

# Official methodology

Method id: `pv_irradiance_area_efficiency`.

# Changelog

- 0.1.0: initial (v2.6.1 Wave 2).
