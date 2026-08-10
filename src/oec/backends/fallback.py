"""Backend fallback policy (v2.4, ADR 0021): declared backend missing ->
clear ``ERROR``, never a silent solver swap.

Mirrors ``oec.execution.limits.InputLimits``/``check_input_limits``'s shape
on purpose: a declarative check function returning
``list[ValidationOutcome]``, so "backend fit vs. skill declaration" plugs
into the Verification Engine's pre-checks the same way other declarative
policies already plug into the execution pipeline.

``SkillManifest`` has no field declaring a required backend capability
today, and adding one is a skill-authoring contract change across every
skill — out of scope for v2.4. Instead this covers exactly the skills with
a genuine optional hard dependency today: every ``method.id`` backed by
HiGHS (``oec[optimization]`` extra), found via a repo-wide survey of
``skills/optimization/*/skill.yaml``. A method id with no entry here has no
declared requirement — this check reports nothing for it, which is not the
same as declaring it always available.
"""

from __future__ import annotations

from oec.backends.capabilities import DECLARED_CAPABILITIES
from oec.backends.registry import get_backend_capabilities
from oec.validation.base import Severity, ValidationOutcome

LAYER = "backend_fit"

# method.id -> required capability domain, for skills with a genuine
# optional hard dependency today (all HiGHS-backed method ids).
_METHOD_BACKEND_REQUIREMENTS: dict[str, str] = {
    "highs_lp": "lp",
    "highs_milp": "milp",
    "highs_feasibility": "lp",
    "highs_lp_diagnostics": "lp",
    "highs_weighted_sum": "lp",
    "highs_scenario_batch": "lp",
    # ADR 0031 — neural (oec[neural] / torch)
    "torch_mlp_regressor_train": "neural_train",
    "torch_mlp_classifier_train": "neural_train",
    "torch_mlp_predict": "neural_eval",
    "torch_mlp_evaluate": "neural_eval",
    # N2 autoencoders
    "torch_autoencoder_basic": "neural_train",
    "torch_autoencoder_denoising": "neural_train",
    # N3 sequence models
    "torch_cnn1d_train": "neural_train",
    "torch_lstm_train": "neural_train",
    "torch_gru_train": "neural_train",
    "torch_tcn_train": "neural_train",
    # N4 transformer
    "torch_transformer_encoder_train": "neural_train",
    "torch_transformer_seq_regressor": "neural_train",
    "torch_transformer_seq_classifier": "neural_train",
    # N5 GNN (pure torch, ADR 0032)
    "torch_gcn_train": "neural_train",
    "torch_graphsage_train": "neural_train",
    "torch_gat_train": "neural_train",
    # ADR 0031 — evolutionary (oec[evolutionary] / pymoo)
    "pymoo_optimize_single": "evolutionary_single",
    "pymoo_de": "evolutionary_single",
    "pymoo_ga": "evolutionary_single",
    "pymoo_cmaes": "evolutionary_single",
    "pymoo_pso": "evolutionary_single",
    # E2 multi-objective + X1 benchmark
    "pymoo_nsga2": "evolutionary_multi",
    "pymoo_nsga3": "evolutionary_multi",
    "pymoo_moead": "evolutionary_multi",
    "pymoo_pareto_search": "evolutionary_multi",
    "pymoo_evolutionary_benchmark": "evolutionary_single",
}


def check_backend_availability(method_id: str) -> list[ValidationOutcome]:
    """Return an ERROR outcome if ``method_id``'s required backend is unavailable.

    An empty list means either no requirement is declared for
    ``method_id``, or the declared requirement is satisfied.
    """
    domain = _METHOD_BACKEND_REQUIREMENTS.get(method_id)
    if domain is None:
        return []

    owner_name = next(
        (name for name, domains in DECLARED_CAPABILITIES.items() if domain in domains), None
    )
    if owner_name is None:
        # Declared requirement points at an undeclared domain -- a code bug in
        # this module's own map, not a runtime backend-availability outcome.
        return [
            ValidationOutcome(
                layer=LAYER,
                severity=Severity.ERROR,
                messages=[f"method {method_id!r} requires undeclared capability domain {domain!r}"],
                details={"method_id": method_id, "domain": domain},
            )
        ]

    capabilities = {c.name: c for c in get_backend_capabilities()}
    backend = capabilities[owner_name]
    if backend.available:
        return []

    return [
        ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[
                f"method {method_id!r} requires backend {owner_name!r} "
                f"(capability {domain!r}), which is not available: {backend.reason}"
            ],
            details={"method_id": method_id, "backend": owner_name, "domain": domain},
        )
    ]
