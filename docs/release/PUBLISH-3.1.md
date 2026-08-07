# Publish OEC 3.1.1 (human)

Short runbook. Full product notes: `docs/implementation/v3.1-CLOSEOUT.md`.

## Preconditions

- [x] Incubation at `oec==3.1.1`
- [x] Public sibling prepared: `open-engineering-compute-public-3.1.1`
- [ ] You reviewed the public tree
- [ ] You created/empty GitHub repo (no forced history from incubation)

## Commands

```powershell
cd "C:\Users\joaop\OneDrive\Anexos de email\Documentos\open-engineering-compute-public-3.1.1"

python scripts/check_forbidden_names.py --all-files
# expect: ok, zero forbidden terms

# optional: tests if env has deps
# uv sync ; uv run pytest -q

git remote add origin <YOUR_PUBLIC_REPO_URL>
git push -u origin main
git tag v3.1.1
git push origin v3.1.1
```

## Do not

- Push from `Documentos\OEC` (incubation) if it still holds private names/docs
- Force-push over an existing public history without review
- Commit `.env`, keys, or `docs/implementation` stress dumps
