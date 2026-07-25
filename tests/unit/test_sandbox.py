from pathlib import Path

from oec.execution.sandbox import run_in_sandbox


def _write_module(tmp_path: Path, code: str) -> None:
    (tmp_path / "implementation.py").write_text(code, encoding="utf-8")


def test_successful_run(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "def execute(inputs):\n"
        "    return {\n"
        "        'result': {'value': inputs['value'] * 2},\n"
        "        'diagnostics': {'converged': True},\n"
        "    }\n",
    )
    result = run_in_sandbox(
        skill_path=tmp_path,
        module="implementation",
        function="execute",
        inputs={"value": 21},
        timeout_seconds=10.0,
    )
    assert not result.failed
    assert not result.timed_out
    assert result.result == {"value": 42}
    assert result.diagnostics == {"converged": True}


def test_timeout_is_enforced(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "import time\n"
        "def execute(inputs):\n"
        "    time.sleep(10)\n"
        "    return {'result': {}, 'diagnostics': {}}\n",
    )
    result = run_in_sandbox(
        skill_path=tmp_path,
        module="implementation",
        function="execute",
        inputs={},
        timeout_seconds=1.0,
    )
    assert result.timed_out
    assert result.failed


def test_skill_exception_is_captured_not_raised(tmp_path: Path) -> None:
    _write_module(tmp_path, "def execute(inputs):\n    raise ValueError('boom')\n")
    result = run_in_sandbox(
        skill_path=tmp_path,
        module="implementation",
        function="execute",
        inputs={},
        timeout_seconds=10.0,
    )
    assert result.failed
    assert not result.timed_out
    assert "ValueError" in result.error_output
    assert "boom" in result.error_output


def test_missing_module_is_captured_not_raised(tmp_path: Path) -> None:
    result = run_in_sandbox(
        skill_path=tmp_path,
        module="does_not_exist",
        function="execute",
        inputs={},
        timeout_seconds=10.0,
    )
    assert result.failed
    assert "ImportError" in result.error_output or "FileNotFoundError" in result.error_output
