# C5 session-acquisition cancellation remediation

Date: 2026-08-30
Base commit: `3e686be94834e343e3018bce1ddc69d20fa5957d`

## Exact-window reproduction and repair

The deterministic injection sends SIGINT or SIGTERM inside
`OutputSession.__init__` after the cold staging directory and root descriptor
exist but before either the lifecycle function or its caller can bind the new
session. Before remediation, the SIGINT parameter returned 130 but left one
`.run-*.tmp` sibling. The focused RED run was 1 failed and 1 passed.

The controlled handler now records the first signal while session acquisition
is deferred. It raises `InspectCancelled` only on leaving the defer boundary,
after the caller assignment is complete. Normal execution outside this narrow
boundary still raises cancellation immediately. Cleanup continues to ignore
later SIGINT/SIGTERM.

| Scenario | Invocation | Binary observable | Result |
|---|---|---|---|
| Exact post-stage/pre-binding SIGINT and SIGTERM, with opposite second signal during cleanup | `uv run pytest -q tests/psi_tool/test_cli_signals.py::test_signal_after_stage_before_session_binding_is_deferred_and_cleaned` | CLI exits 130/143; stderr is exactly `inspect cancelled`; stdout starts `FAIL report=none`; no final output; zero `.run-*`; `/dev/fd` count unchanged | 2 passed in 0.45s |
| All cancellation surfaces, including real process-group SIGINT/SIGTERM | `uv run pytest -q tests/psi_tool/test_cli_signals.py` | Real child process exits 130/143 after partial Parquet; `communicate()` reaps it; no staging residue; warm PASS becomes FAIL; second signal cannot interrupt cleanup | 7 passed in 85.20s |
| Final focused lifecycle, cancellation, ancestor race, relation-pin, verified-manifest/no-CWD aggregate | `uv run pytest -q tests/psi_tool/test_output_lifecycle.py tests/psi_tool/test_cli_signals.py tests/psi_tool/test_ancestor_swap.py tests/psi_tool/test_relation_pin_enforcement.py tests/psi_tool/test_verified_manifest.py` | All cold/warm, exclusive publication, stage rename, ancestor swap, 130/143, pin, manifest and no-chdir assertions pass | 19 passed in 117.77s |

## Strict gates

```text
uv run ruff check src/psi_tool tests/psi_tool
All checks passed!

uv run ruff format --check src/psi_tool tests/psi_tool
35 files already formatted

uv run basedpyright src/psi_tool tests/psi_tool
0 errors, 0 warnings, 0 notes

check-no-excuse-rules.py <5 changed Python files>
no violations in 5 file(s)
```

Production search returned zero matches for blanket `except Exception` or
`except BaseException`, obsolete pthread masking/defer functions, path-based
recursive deletion, `tempfile`, and `/dev/fd`. Every changed Python file is
under 250 physical lines; the largest is `test_cli_signals.py` at 234 and the
largest changed production file is `_output_lifecycle.py` at 211.

No project-local `.run-*.tmp` remained after verification.

## Source snapshot

```text
9ec2e7eb246ed6c10e901b8271f78934e92f3914c0d18ef83bc00a442f4a9fe1  src/psi_tool/_fd_cleanup.py
1fce6367c98b4f4d251d62ae8794bd683fe9c59cdce95dc0bc856e311e9abbe2  src/psi_tool/_output_lifecycle.py
b91e879acde5f5afba4247f15948e7bc6cbd484c6c68a9a2ad2ae7826106995b  src/psi_tool/_signals.py
e4ee4680340e6d55b99c3631be4545453d6083afdffe5a132d28ace9da585601  src/psi_tool/cli.py
5587a0b4c0ced002964b45150c5ab9fceb8cc6618ef29ac3dbe0c2eca58f43f0  tests/psi_tool/test_cli_signals.py
```

## Residual limits

SIGKILL and signal delivery delayed inside native extensions remain outside
controlled cleanup. File contents are fsynced but parent directories are not;
power loss may lose the latest rename. The source tree and manifest must remain
immutable during one invocation, and a caller manifest is not an authenticity
signature. Local resource exhaustion remains possible.
