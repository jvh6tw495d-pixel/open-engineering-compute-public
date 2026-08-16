"""L9-L11 core-safe RL contracts and optional ART boundary."""

from __future__ import annotations

import pytest

from oec.learning.backends.art import ARTBackend
from oec.learning.environments import MathematicsEnvironment, RewardSpec
from oec.learning.errors import BackendNotAvailableError
from oec.learning.rl import Action, Episode, State, Trajectory


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
