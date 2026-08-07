"""Control & Dynamics Specialist for governed public OEC skills."""

from __future__ import annotations

from agents.common import SkillSpecialist


class ControlDynamicsSpecialist(SkillSpecialist):
    name = "control_dynamics_specialist"
    demos = {
        "pid": (
            "control.pid_discrete",
            {
                "reference": [1.0, 1.0],
                "measurement": [0.0, 0.0],
                "kp": 2.0,
                "ki": 0.0,
                "kd": 0.0,
                "dt": 0.1,
            },
        ),
        "kalman": (
            "control.kalman_filter",
            {
                "A": [[1.0]],
                "C": [[1.0]],
                "Q": [[0.0]],
                "R": [[1.0]],
                "z": [[5.0]],
                "x0": [0.0],
                "P0": [[1.0]],
            },
        ),
        "stability": ("dynamics.stability_margins", {"A": [[-1.0]], "time_base": "continuous"}),
    }
