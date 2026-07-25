# ADR 0012: Skills execute in a subprocess; timeout is enforced, network/filesystem isolation is not (yet)

- **Status:** accepted
- **Date:** 2026-07-25

## Context

`SkillManifest.execution` (`ExecutionPolicy`, ADR-adjacent to section 8.2
of the master plan) declares, per skill:

```yaml
execution:
  deterministic: true
  timeout_seconds: 5
  network_access: false
  filesystem_access: false
```

The Skill Execution Service (this sprint) is the first component that
actually runs a skill's `implementation.py`. Two implementation
strategies were considered:

1. **In-process**: `importlib` the skill's module inside the OEC process
   and call its entrypoint function directly.
2. **Subprocess**: spawn a fresh Python interpreter, run the skill's
   entrypoint there, and communicate via stdin/stdout.

In-process execution cannot actually deliver what `ExecutionPolicy`
promises:

- **`timeout_seconds`**: Python has no reliable, cross-platform way to
  forcibly stop a running thread. Signal-based timeouts
  (`signal.alarm`) don't exist on Windows. A "timeout" that can't
  actually interrupt a runaway skill is not a timeout, it's a warning
  label.
- **`network_access: false` / `filesystem_access: false`**: Python has
  no built-in mechanism to revoke socket or filesystem access from
  code running in the same process and interpreter. Monkey-patching
  `socket`/`open` is trivially bypassable (skill code can just save a
  reference to the original before it's patched, or use a C extension)
  and is not a security boundary — instruction 4.7 in the plan requires
  real timeouts and real limits, not a symbolic gesture.

Subprocess execution can deliver a real timeout: the parent process can
unconditionally kill the child when `subprocess.run(..., timeout=...)`
expires, on both Windows and POSIX. It does **not**, by itself, deliver
network or filesystem isolation — that requires OS-level sandboxing
(Windows Job Objects with a restricted token, Linux namespaces/seccomp,
or a container), which is out of scope for this sprint.

## Decision

Skills execute in a subprocess, launched as a fresh `sys.executable`
process running a small, fixed runner script
(`oec.execution.runner`, added this sprint). The parent:

1. Serializes `ExecutionRequest.inputs` (plus the resolved skill path,
   entrypoint module/function) to JSON.
2. Runs the runner via `subprocess.run(..., input=..., timeout=
   manifest.execution.timeout_seconds, capture_output=True)`.
3. On `subprocess.TimeoutExpired`, classifies the execution as
   `ExecutionStatus.FAILED` with a `timeout` diagnostic — the process is
   already dead by the time `TimeoutExpired` is raised.
4. On a clean exit, parses the runner's JSON stdout as the skill's raw
   result; on a non-zero exit, captures stderr and classifies as
   `ExecutionStatus.FAILED` with the captured traceback in `diagnostics`
   (never in `warnings` or silently dropped — plan instruction 10: don't
   mask solver/execution failures).

The runner script itself does the dynamic import
(`importlib.util.spec_from_file_location`), never the parent process —
this is also why the Skill Loader (Sprint 01) deliberately never imports
a skill's code: only the sandboxed runner does, and only at execution
time, never at load/list/inspect time.

**`timeout_seconds` is genuinely enforced.** **`network_access` and
`filesystem_access` are declared in the manifest but *not yet enforced*
by this sprint's implementation.** This is stated explicitly, everywhere
it matters:

- `ExecutionResult.diagnostics` includes a `sandbox` object reporting
  what was actually enforced for that run (`{"timeout_enforced": true,
  "network_isolation_enforced": false, "filesystem_isolation_enforced":
  false}`), so no caller can mistake the manifest's declaration for a
  guarantee.
- If a skill declares `network_access: false` or `filesystem_access:
  false`, the Execution Service does not silently claim compliance —
  the gap is surfaced, not hidden (plan instruction 11: don't claim
  validation without evidence).

Real OS-level isolation (Job Objects / namespaces / containers) is
deferred to a future hardening sprint (candidate: Sprint 09,
"Hardening e Public Alpha") once there is a concrete threat model
(untrusted third-party skills) to design against — building it
speculatively now, before any skill actually needs it, would be
over-engineering for the Alpha.

## Consequences

- A skill that hangs is reliably killed at `timeout_seconds`, even on
  Windows — testable today, not aspirational.
- A skill that opens a socket or writes outside its directory can still
  do so in this sprint. Any skill claiming to need real isolation before
  the hardening sprint lands must not be treated as trusted-by-default;
  this is a documented gap, not a silent one.
- Every execution has real subprocess overhead (interpreter startup).
  Acceptable for the Alpha's synchronous, one-skill-at-a-time execution
  model (plan section 13.3: "execução síncrona no Alpha"); revisit if
  Sprint 07's REST API needs to run many executions concurrently.
- The runner script is the *only* place in the codebase that imports
  skill-authored code. This keeps the "don't execute untrusted code
  without need" boundary from ADR/plan section 4.7 auditable at a single
  file.
