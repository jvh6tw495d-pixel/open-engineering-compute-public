"""L9-L11 core-safe RL contracts and optional ART boundary."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from oec.learning.backends.art import ARTBackend
from oec.learning.environments import MathematicsEnvironment, RewardSpec
from oec.learning.errors import BackendNotAvailableError
from oec.learning.rl import Action, Episode, RLResult, State, Trajectory
from oec.learning.verifiers import execution_result_reward, execution_result_scores


def test_trajectory_checks_transition_shape() -> None:
    trajectory = Trajectory(
        states=(State(values={"x": 1}), State(values={"x": 2}, terminal=True)),
        actions=(Action(name="increment"),),
        rewards=(0.5,),
    )
    assert Episode(episode_id="one", trajectory=trajectory).total_reward == 0.5

    with pytest.raises(ValueError, match="one more state"):
        Trajectory(states=(State(),), actions=(Action(name="bad"),), rewards=(0.0,))


def test_reward_is_deterministic_and_closed() -> None:
    spec = RewardSpec(correct=2.0, units=0.5, constraints=1.0, tokens=0.25, latency=0.25)
    scores = {"correct": 1.0, "units": 1.0, "constraints": 0.5, "tokens": 0.8, "latency": 0.4}
    assert MathematicsEnvironment(reward_spec=spec).reward(scores) == pytest.approx(3.3)
    with pytest.raises(ValueError, match="exactly"):
        spec.reward({"correct": 1.0})


def test_art_fails_closed_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.learning.backends.art as art_module

    def missing_art(_name: str) -> object:
        raise ImportError()

    monkeypatch.setattr(art_module.importlib, "import_module", missing_art)
    with pytest.raises(BackendNotAvailableError):
        ARTBackend().train(MathematicsEnvironment(), ())


def test_art_delegates_to_imported_train_grpo(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.learning.backends.art as art_module

    expected = RLResult(status="ok", backend="art", message="mock")
    module = SimpleNamespace(train_grpo=lambda **_kwargs: expected)
    monkeypatch.setattr(art_module.importlib, "import_module", lambda _name: module)
    assert ARTBackend().train(MathematicsEnvironment(), ()) is expected


def test_art_converts_trajectory_instead_of_dropping_it(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.learning.backends.art as art_module

    captured: dict[str, object] = {}

    def _train_grpo(**kwargs: object) -> RLResult:
        captured.update(kwargs)
        return RLResult(status="ok", backend="art")

    monkeypatch.setattr(
        art_module.importlib, "import_module", lambda _name: SimpleNamespace(train_grpo=_train_grpo)
    )
    trajectory = Trajectory(states=(State(),), actions=(), rewards=())
    ARTBackend().train(MathematicsEnvironment(), trajectory)
    episodes = captured["episodes"]
    assert isinstance(episodes, tuple)
    assert len(episodes) == 1
    assert isinstance(episodes[0], Episode)
    assert episodes[0].trajectory is trajectory


def test_execution_result_verifier_bridge_is_closed_and_deterministic() -> None:
    spec = RewardSpec(correct=2.0, units=0.5, constraints=1.0)
    result = {"status": "ok", "units_ok": True, "constraint_ok": False}
    assert execution_result_scores(result) == {
        "correct": 1.0,
        "units": 1.0,
        "constraints": 0.0,
        "tokens": 1.0,
        "latency": 1.0,
    }
    assert execution_result_reward(result, spec) == pytest.approx(2.5)
