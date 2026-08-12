from __future__ import annotations

from typing import Any

from oec.physics.optics import thin_lens_image_distance, thin_lens_magnification


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    f = float(inputs["focal_length_m"])
    u = float(inputs["object_distance_m"])
    v = thin_lens_image_distance(f, u)
    m = thin_lens_magnification(u, v)
    return {
        "result": {
            "image_distance_m": v,
            "magnification": m,
            "focal_length_m": f,
            "object_distance_m": u,
        },
        "diagnostics": {},
    }
