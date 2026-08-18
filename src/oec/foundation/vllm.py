"""vLLM remote backend — OpenAI-compatible HTTP client only (ADR 0046).

OEC never imports or installs the ``vllm`` Python package (Linux+NVIDIA
engine, not an OEC extra). This module only speaks HTTP, via the standard
library, to an already-running ``vllm serve`` instance. Fail-closed: a
down/unreachable server or an unparsable response raises
:class:`~oec.foundation.errors.VllmUnreachableError` — never fabricated text.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from oec.foundation.contracts import VllmGenerateSpec
from oec.foundation.errors import VllmUnreachableError

_REQUEST_TIMEOUT_SECONDS = 30.0
_COMPLETIONS_PATH = "/v1/completions"


def run_vllm_generate(spec: VllmGenerateSpec) -> dict[str, Any]:
    """POST ``{base_url}/v1/completions`` and return the parsed completion.

    Bounded timeout, no retries — a down server fails closed immediately.
    """
    url = spec.base_url.rstrip("/") + _COMPLETIONS_PATH
    body = {
        "model": spec.model_id,
        "prompt": spec.prompt,
        "max_tokens": int(spec.max_new_tokens),
        "temperature": float(spec.temperature),
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(  # nosec B310 -- scheme validated to http/https by VllmGenerateSpec
            request, timeout=_REQUEST_TIMEOUT_SECONDS
        ) as response:
            raw = response.read().decode("utf-8")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise VllmUnreachableError(details={"base_url": spec.base_url, "reason": str(exc)}) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VllmUnreachableError(
            "vLLM server returned a non-JSON response",
            details={"base_url": spec.base_url, "reason": str(exc)},
        ) from exc

    try:
        text = str(payload["choices"][0]["text"])
    except (KeyError, IndexError, TypeError) as exc:
        raise VllmUnreachableError(
            "vLLM server response is missing choices[0].text",
            details={"base_url": spec.base_url, "reason": str(exc)},
        ) from exc

    return {
        "backend": "vllm",
        "backend_version": None,
        "model_id": spec.model_id,
        "base_url": spec.base_url,
        "prompt": spec.prompt,
        "text": text,
        "max_new_tokens": spec.max_new_tokens,
        "temperature": spec.temperature,
        "seed": spec.seed,
        "merit_owner": "vllm",
        "message": "OpenAI-compatible vLLM /v1/completions generation",
    }
