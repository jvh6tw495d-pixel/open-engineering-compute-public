"""Neural & Evolutionary Specialist for governed public OEC skills.

Covers ``neural.*`` (dense families, training modes, search) and
``evolutionary.*`` (single/multi-objective, portfolio) public skills under
ADR 0031 / ADR 0033. Product-agnostic: no product branding in demos or
narratives.
"""

from __future__ import annotations

from agents.common import SkillSpecialist


class NeuralEvolutionarySpecialist(SkillSpecialist):
    """Maps neural/evolutionary demos → public skill ids + inputs."""

    name = "neural_evolutionary_specialist"
    demos = {
        "mlp_regressor": (
            "neural.mlp.regressor",
            {
                "x": [[0.0], [1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0]],
                "y": [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0],
                "hidden_dims": [16],
                "epochs": 40,
                "lr": 0.05,
                "val_fraction": 0.25,
                "seed": 0,
                "device": "cpu",
            },
        ),
        "mlp_classifier": (
            "neural.mlp.classifier",
            {
                "x": [
                    [0.0, 0.0],
                    [0.0, 1.0],
                    [1.0, 0.0],
                    [1.0, 1.0],
                    [0.1, 0.1],
                    [0.9, 0.1],
                    [0.1, 0.9],
                    [0.9, 0.9],
                ],
                "y": [0, 1, 1, 0, 0, 1, 1, 0],
                "n_classes": 2,
                "hidden_dims": [16, 8],
                "epochs": 40,
                "seed": 0,
                "device": "cpu",
            },
        ),
        "optimize_single": (
            "evolutionary.optimize_single",
            {
                "variables": [
                    {"name": "x1", "lower": -5.0, "upper": 5.0},
                    {"name": "x2", "lower": -5.0, "upper": 5.0},
                ],
                "built_in": "sphere",
                "algorithm": "differential_evolution",
                "generations": 15,
                "population": 12,
                "seed": 0,
            },
        ),
        "nsga2": (
            "evolutionary.nsga2",
            {
                "variables": [
                    {"name": "x0", "lower": 0.0, "upper": 1.0},
                    {"name": "x1", "lower": 0.0, "upper": 1.0},
                    {"name": "x2", "lower": 0.0, "upper": 1.0},
                    {"name": "x3", "lower": 0.0, "upper": 1.0},
                    {"name": "x4", "lower": 0.0, "upper": 1.0},
                ],
                "built_in": "zdt1",
                "generations": 10,
                "population": 12,
                "seed": 0,
            },
        ),
        "training_supervised": (
            "neural.training.supervised",
            {
                "x": [
                    [0.0],
                    [1.0],
                    [2.0],
                    [3.0],
                    [4.0],
                    [5.0],
                    [6.0],
                    [7.0],
                    [8.0],
                    [9.0],
                    [10.0],
                    [11.0],
                ],
                "y": [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0, 19.0, 21.0, 23.0],
                "seed": 0,
                "max_evaluations": 6,
                "inner_epochs": 10,
                "epochs": 20,
            },
        ),
        "de": (
            "evolutionary.differential_evolution",
            {
                "variables": [
                    {"name": "x1", "lower": -5.0, "upper": 5.0},
                    {"name": "x2", "lower": -5.0, "upper": 5.0},
                ],
                "built_in": "sphere",
                "generations": 15,
                "population": 12,
                "seed": 0,
            },
        ),
    }
