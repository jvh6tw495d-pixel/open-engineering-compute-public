"""L13 — permanent backend comparison suite (protocol, not live GPU)."""

from __future__ import annotations

from typing import Any

from oec.learning.capability import capability_matrix, probe_optional
from oec.learning.contracts import FineTuneBackendName, MetricDirection, MetricSpec
from oec.learning.evaluation import Benchmark, compare_results

BACKEND_SUITE_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(name="loss", direction=MetricDirection.MINIMIZE),
    MetricSpec(name="vram_gb", direction=MetricDirection.MINIMIZE),
    MetricSpec(name="train_seconds", direction=MetricDirection.MINIMIZE),
)

AGENTIC_SUITE_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(name="reward", direction=MetricDirection.MAXIMIZE),
    MetricSpec(name="task_success", direction=MetricDirection.MAXIMIZE),
    MetricSpec(name="tokens_per_task", direction=MetricDirection.MINIMIZE),
)


def backend_benchmark() -> Benchmark:
    return Benchmark(name="learning-backend-suite", metrics=BACKEND_SUITE_METRICS)


def agentic_benchmark() -> Benchmark:
    return Benchmark(name="learning-agentic-suite", metrics=AGENTIC_SUITE_METRICS)


def declared_backends() -> dict[str, tuple[str, ...]]:
    return {
        "finetune": tuple(item.value for item in FineTuneBackendName),
        "rl": ("art", "none"),
    }


def compare_backend_runs(left: dict[str, float], right: dict[str, float]) -> dict[str, Any]:
    return compare_results(backend_benchmark(), left, right, left_id="A", right_id="B")


def measure_capability_suite() -> dict[str, Any]:
    """Measured availability probe — never invents GPU timings or losses."""
    probes = probe_optional()
    rows = capability_matrix()
    return {
        "benchmark": "learning-capability-probe",
        "probes": probes,
        "matrix": rows,
        "wired": [row["wave"] for row in rows if row.get("status") in {"wired", "adapter"}],
        "available_backends": [row["backend"] for row in rows if row.get("available")],
    }
