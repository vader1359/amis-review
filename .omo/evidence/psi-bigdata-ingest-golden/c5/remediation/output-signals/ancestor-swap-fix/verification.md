# C5 descriptor-chain ancestor-swap remediation

Date: 2026-08-30
Base commit: `3e686be94834e343e3018bce1ddc69d20fa5957d`

## Behavior evidence

| Scenario | Invocation | Binary observable | Result |
|---|---|---|---|
| Verifier-exact swap before parent acquisition and swap after held-parent acquisition | `uv run pytest -q tests/psi_tool/test_ancestor_swap.py` | External sentinel remains byte-identical; no cache or `.run-*` appears outside; original lexical path has no claimable PASS | RED before fix: 2 failed in 64.59s; GREEN after fix: 2 passed in 26.98s |
| Full lifecycle, real process-group signals, relation pins, verified manifest, and both ancestor races | `uv run pytest -q tests/psi_tool/test_output_lifecycle.py tests/psi_tool/test_cli_signals.py tests/psi_tool/test_relation_pin_enforcement.py tests/psi_tool/test_verified_manifest.py tests/psi_tool/test_ancestor_swap.py` | Cold cleanup leaves zero staging residue; warm cancellation leaves no old PASS; SIGINT returns 130 and SIGTERM returns 143; seven relation pins and verified-manifest invariants remain enforced | 17 passed in 209.96s |
| Descriptor-only report/cache call-site migration | `uv run pytest -q tests/psi_tool/test_cli.py` | Report semantic hash, cold cleanup, exclusive publish, and CLI output-state tests pass through descriptor APIs | 6 passed in 98.47s |
| Unsafe cache child and interrupted test adapter | `uv run pytest -q tests/psi_tool/test_cache_failures.py::test_materialize_cache_rejects_unsafe_output_state tests/psi_tool/test_cache_failures.py::test_materialize_cache_cleans_interrupted_staging` | Symlink, regular-file, and foreign cache states reject; interrupted cold fixture leaves no cache residue | 4 passed in 2.13s |

The root-anchored walk retains `/` and every parent component opened with
`O_DIRECTORY|O_NOFOLLOW`. Publication and cleanup use the retained immediate
parent descriptor. Fresh walks compare every component's device and inode
before and after publication. A renamed staging entry is found only by its
owned device/inode under the retained parent and is never followed by name.

## API and static gates

```text
uv run ruff check src/psi_tool tests/psi_tool
All checks passed!

uv run ruff format --check src/psi_tool tests/psi_tool
34 files already formatted

uv run basedpyright src/psi_tool tests/psi_tool
0 errors, 0 warnings, 0 notes

check-no-excuse-rules.py <18 changed Python files>
no violations in 18 file(s)
```

Production search for a `Path`-accepting `materialize_cache` or
`write_report_atomic`, `tempfile`, `shutil.rmtree`, `Path.replace`, `/dev/fd`,
and `chdir` returned zero matches. The only writer definitions are:

```text
src/psi_tool/_fd_cache.py:37:def materialize_cache(
src/psi_tool/report.py:119:def write_report_atomic(
```

Both require `DirectoryFd`. The largest changed production Python file is
`_output_lifecycle.py` at 249 physical lines; the no-excuse pure-LOC gate is
green for every changed Python file.

## Source snapshot

```text
cb0a453f5f0b4f5e7fa137e1193cd0ac6bb49e46da551f94aea547961876a38b  src/psi_tool/_fd_walk.py
c7610df8c6ec2f392f09d9899358ecfa120334e4cc95c2cf7b9279f1ec12b461  src/psi_tool/_output_lifecycle.py
2522fc127ce80750cda77a507ba816010c25c09d11f06d5ea8e0dbe8abea98d1  src/psi_tool/_fd_cache.py
99999775576cd8dbea5b002c5bf914c5ab878c4216bff98e8ab6ac68f7b7e557  src/psi_tool/cache.py
6de9d2e987aad546ad991251e8def6b81b3e20c46126afa43b1efff8b86a77ca  src/psi_tool/report.py
74edc1389c31bbd2e1d08b9d78d13fac5de1b26d859ff677f3367fc8b7dda01c  src/psi_tool/cli.py
542004eaa21a482184f707c6848dccc69cd13cc20b3bf16eec4434fa9272cc68  tests/psi_tool/test_ancestor_swap.py
a99cf3de7e72c83b826ffc3d5780599131cb3120a49d8a86a4fb78a40cd4e0cd  docs/psi_tool_v1/contract.md
```

## Residual limits

The source tree and manifest must stay immutable during an invocation. A
caller-supplied manifest is not an authenticity signature. Local resource
exhaustion remains possible. File contents are fsynced, but parent directories
are not, so sudden power loss may lose the latest rename. SIGKILL and delayed
signal delivery inside a native extension are outside controlled cleanup.
