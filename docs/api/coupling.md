# Multiphysics coupling API (v2.7)

## Library

```python
from oec.physics.coupling import (
    CouplingGraph,
    run_wire_i2r_coupling,
    run_solar_thermal_electrical_coupling,
)
```

Weak Gauss–Seidel co-simulation only (ADR 0028). Strong/implicit coupling is out of scope.

## Skills

| Skill id | Owner |
|----------|--------|
| `multiphysics.wire_i2r` | electrical ↔ thermal I²R |
| `multiphysics.solar_thermal_electrical` | solar + thermal + PV η(T) |
