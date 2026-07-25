"""Integration tests for the REST API (ADR 0005, ADR 0015): the real
FastAPI app, built against the real ``skills/`` directory, exercised
through Starlette's ``TestClient`` (in-process, no real socket) --
mirrors ``tests/integration/test_sdk_engine.py``'s "exercise the real
thing, not a mock" approach.
"""

from __future__ import annotations

import math
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from oec.api.app import create_app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    # TestClient only runs the app's lifespan (which builds and warms
    # the Engine, ADR 0015) when used as a context manager -- a bare
    # TestClient(app) leaves app.state.engine unset.
    with TestClient(create_app(skills_root="skills")) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_skills(client: TestClient) -> None:
    response = client.get("/skills")
    assert response.status_code == 200
    ids = [manifest["id"] for manifest in response.json()]
    assert "mathematics.solve_root" in ids


def test_list_skills_filters_by_domain(client: TestClient) -> None:
    response = client.get("/skills", params={"domain": "mathematics"})
    assert response.status_code == 200
    assert all(manifest["domain"] == "mathematics" for manifest in response.json())


def test_list_skills_filters_by_tag(client: TestClient) -> None:
    response = client.get("/skills", params={"tag": "mvp"})
    assert response.status_code == 200
    assert all("mvp" in manifest["tags"] for manifest in response.json())


def test_get_skill(client: TestClient) -> None:
    response = client.get("/skills/mathematics.solve_root")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "mathematics.solve_root"
    assert body["method"]["iterative"] is True


def test_get_skill_unknown_returns_404(client: TestClient) -> None:
    response = client.get("/skills/mathematics.not_a_real_skill")
    assert response.status_code == 404


def test_run_skill_verified_result_returns_200(client: TestClient) -> None:
    response = client.post(
        "/skills/mathematics.solve_root/run",
        json={"inputs": {"expression": "x**2 - 2", "bracket": [0, 2]}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "VALIDATED"
    assert math.isclose(body["result"]["root"], math.sqrt(2), rel_tol=1e-9)


def test_run_skill_invalid_status_still_returns_200(client: TestClient) -> None:
    """A schema-rejected skill input is ExecutionStatus.INVALID -- a
    structured scientific outcome the caller reads from the body, not
    a transport failure (ADR 0015 §1: only unknown skill / unparseable
    body get a non-200)."""
    response = client.post(
        "/skills/mathematics.solve_root/run",
        json={"inputs": {"expression": "x**2 - 2", "bracket": [0, 2], "unexpected_field": True}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INVALID"


def test_run_skill_unknown_skill_returns_404(client: TestClient) -> None:
    response = client.post("/skills/mathematics.not_a_real_skill/run", json={"inputs": {}})
    assert response.status_code == 404


def test_run_skill_malformed_body_returns_422(client: TestClient) -> None:
    """An extra/unknown top-level field is a transport-level bad
    request (RunRequest forbids extras) -- distinct from a skill-level
    INVALID, which still returns 200 (see test above)."""
    response = client.post(
        "/skills/mathematics.solve_root/run",
        json={"inputs": {"expression": "x**2 - 2", "bracket": [0, 2]}, "not_a_real_field": True},
    )
    assert response.status_code == 422


def test_run_skill_forwards_provenance_fields(client: TestClient) -> None:
    response = client.post(
        "/skills/mathematics.solve_root/run",
        json={
            "inputs": {"expression": "x - 1", "bracket": [0, 2]},
            "trace_id": "my-trace-id",
            "requested_by": "test-suite",
            "seed": 42,
        },
    )
    assert response.status_code == 200
    provenance = response.json()["provenance"]
    assert provenance["trace_id"] == "my-trace-id"
    assert provenance["requested_by"] == "test-suite"
    assert provenance["seed"] == 42
