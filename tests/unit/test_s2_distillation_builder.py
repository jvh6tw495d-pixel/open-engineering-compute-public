from oec.experiment.cross_domain import build_distill_then_eval_experiment


def test_distill_builder_is_catalogued_and_binds_student_artifacts() -> None:
    teacher_checkpoint = {
        "model_spec": {
            "architecture": "mlp",
            "input_dim": 1,
            "output_dim": 1,
            "hidden_dims": [4],
            "activation": "relu",
            "dropout": 0.0,
        }
    }
    spec = build_distill_then_eval_experiment(teacher_checkpoint=teacher_checkpoint)
    assert spec.required_extras == ("neural",)
    assert [step.skill_id for step in spec.steps] == ["neural.distill", "neural.evaluate"]
    assert {binding.as_key for binding in spec.steps[1].binds_from} == {"checkpoint", "normalize"}


def test_distill_builder_omits_teacher_normalize_without_an_override() -> None:
    spec = build_distill_then_eval_experiment(teacher_checkpoint={"model_spec": {}})
    assert "teacher_normalize" not in spec.steps[0].inputs


def test_distill_builder_preserves_explicit_teacher_normalize_override() -> None:
    normalize = {"mean": [2.0], "std": [0.5]}
    spec = build_distill_then_eval_experiment(
        teacher_checkpoint={"model_spec": {}}, teacher_normalize=normalize
    )
    assert spec.steps[0].inputs["teacher_normalize"] == normalize
