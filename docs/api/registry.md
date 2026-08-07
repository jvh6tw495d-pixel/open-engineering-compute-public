# Model Registry & Scientific IR API v0 (milestone 2.9)

## Model Registry

```python
from oec.registry import default_registry, FidelityLevel, ModelRecord

reg = default_registry()
for m in reg.list(domain="chemistry", fidelity=FidelityLevel.MID):
    print(m.key, m.entrypoint)
```

| Concept | Meaning |
|---------|---------|
| `ModelRecord` | Versioned entrypoint + fidelity + assumptions |
| `FidelityLevel` | `reduced` \| `mid` \| `high` |
| `deprecate` | Soft-remove with optional `replaced_by` |
| JSON catalog | `save_json` / `load_json` |

Distinct from `oec.skills.registry` (skill package discovery on disk).

## Scientific IR

```python
from oec.modeling.scientific_ir import ScientificDocument, SpeciesDecl

doc = ScientificDocument(
    id="example",
    title="Demo",
    species=(SpeciesDecl(id="H2", name="Hydrogen", formula={"H": 2}),),
)
manifest = doc.to_manifest()
```

Documents are declarative; solvers live in domain packages.

## Migrations

See `docs/contracts/migrations.md`.
