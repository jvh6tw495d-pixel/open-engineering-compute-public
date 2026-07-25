from pathlib import Path

import pytest

from oec.execution.runner import RunnerContractError, _load_entrypoint, _run


def _write_module(tmp_path: Path, code: str, *, name: str = "implementation") -> Path:
    (tmp_path / f"{name}.py").write_text(code, encoding="utf-8")
    return tmp_path


def test_load_entrypoint_returns_the_callable(tmp_path: Path) -> None:
    _write_module(tmp_path, "def execute(inputs):\n    return inputs\n")
    func = _load_entrypoint(tmp_path, "implementation", "execute")
    assert func({"a": 1}) == {"a": 1}


def test_load_entrypoint_missing_module_raises(tmp_path: Path) -> None:
    with pytest.raises(ImportError):
        _load_entrypoint(tmp_path, "does_not_exist", "execute")


def test_load_entrypoint_missing_function_raises(tmp_path: Path) -> None:
    _write_module(tmp_path, "x = 1\n")
    with pytest.raises(AttributeError):
        _load_entrypoint(tmp_path, "implementation", "execute")


def test_run_returns_result_and_diagnostics(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "def execute(inputs):\n"
        "    return {'result': {'value': inputs['value']}, 'diagnostics': {'converged': True}}\n",
    )
    outcome = _run(
        {
            "skill_path": str(tmp_path),
            "module": "implementation",
            "function": "execute",
            "inputs": {"value": 5},
        }
    )
    assert outcome == {"result": {"value": 5}, "diagnostics": {"converged": True}}


def test_run_fills_in_missing_result_or_diagnostics(tmp_path: Path) -> None:
    _write_module(tmp_path, "def execute(inputs):\n    return {'result': {'value': 1}}\n")
    outcome = _run(
        {
            "skill_path": str(tmp_path),
            "module": "implementation",
            "function": "execute",
            "inputs": {},
        }
    )
    assert outcome == {"result": {"value": 1}, "diagnostics": {}}


def test_run_rejects_a_non_dict_return_value(tmp_path: Path) -> None:
    _write_module(tmp_path, "def execute(inputs):\n    return 42\n")
    with pytest.raises(RunnerContractError):
        _run(
            {
                "skill_path": str(tmp_path),
                "module": "implementation",
                "function": "execute",
                "inputs": {},
            }
        )


def test_run_rejects_unexpected_keys(tmp_path: Path) -> None:
    _write_module(tmp_path, "def execute(inputs):\n    return {'result': {}, 'extra_key': True}\n")
    with pytest.raises(RunnerContractError):
        _run(
            {
                "skill_path": str(tmp_path),
                "module": "implementation",
                "function": "execute",
                "inputs": {},
            }
        )


def test_run_propagates_the_skills_own_exception(tmp_path: Path) -> None:
    _write_module(tmp_path, "def execute(inputs):\n    raise ValueError('boom')\n")
    with pytest.raises(ValueError, match="boom"):
        _run(
            {
                "skill_path": str(tmp_path),
                "module": "implementation",
                "function": "execute",
                "inputs": {},
            }
        )
