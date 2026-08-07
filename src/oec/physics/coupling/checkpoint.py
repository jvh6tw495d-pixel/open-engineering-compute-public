"""Iteration checkpoints for coupling rollback."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckpointStore:
    """Last-good state snapshots (per iteration)."""

    _stack: list[dict[str, Any]] = field(default_factory=list)

    def push(self, state: dict[str, Any]) -> None:
        self._stack.append(deepcopy(state))

    def peek(self) -> dict[str, Any] | None:
        if not self._stack:
            return None
        return deepcopy(self._stack[-1])

    def pop(self) -> dict[str, Any]:
        if not self._stack:
            raise RuntimeError("CheckpointStore is empty")
        return self._stack.pop()

    def clear(self) -> None:
        self._stack.clear()

    def __len__(self) -> int:
        return len(self._stack)


__all__ = ["CheckpointStore"]
