# C5 output and signal remediation evidence

Date: 2026-08-30
HEAD: `3e686be94834e343e3018bce1ddc69d20fa5957d`

## Binary observables

| Scenario | Invocation | Required observable | Captured result |
| --- | --- | --- | --- |
| Full bounded remediation set | `uv run pytest tests/psi_tool/test_cli.py tests/psi_tool/test_output_lifecycle.py tests/psi_tool/test_cli_signals.py tests/psi_tool/test_relation_pin_enforcement.py tests/psi_tool/test_verified_manifest.py` | All CLI, lifecycle, signal, relation-pin and immutable-manifest cases pass | `21 passed in 274.99s` |
| Real cold and warm CLI | `uv run pytest tests/psi_tool/test_e2e.py -k real_cold_then_warm_cache_is_stable` | First run publishes seven cold Parquets and PASS; second run reports seven hits without changing Parquet state | `1 passed, 7 deselected in 8.56s` |
| Real process-group SIGINT/SIGTERM | `uv run pytest tests/psi_tool/test_cli_signals.py -k real_cold_process_group_signal` | `uv run psi inspect` exits 130/143, stderr is only `inspect cancelled`, final output absent, no `.run-*.tmp` | `2 passed, 2 deselected in 5.28s` |
| Nested symlink and staging swap | `uv run pytest tests/psi_tool/test_output_lifecycle.py` as part of bounded set | Nested lexical symlink rejected; renamed owned inode cleaned by FD; planted symlink target remains byte-identical | PASS in bounded 21-case set |
| Final lifecycle-only rerun | `uv run pytest tests/psi_tool/test_output_lifecycle.py` | All path, rename, exclusive-publish and active-write adversarial cases pass after removal of unused path surface | `4 passed in 32.99s` |
| Active stage rename during first relation write | `test_active_stage_rename_during_write_does_not_mutate_symlink_target` | External sentinel bytes unchanged, no external cache, moved owned inode removed | PASS in bounded 21-case set |
| Active warm output swap | `test_active_warm_output_swap_does_not_mutate_external_target` | External sentinel bytes unchanged, no external report, retained output receives sanitized FAIL | PASS in bounded 21-case set |
| Exclusive destination race | `test_inspect_exclusive_publish_preserves_destination_that_appears` | Native exclusive rename refuses replacement and preserves foreign sentinel | PASS in bounded 21-case set |
| Second signal during cleanup | `test_second_signal_is_ignored_during_controlled_cleanup` | First cancellation remains exit 130; SIGTERM during cleanup is ignored; no residue | PASS in bounded 21-case set |
| Manual tmux Ctrl-C | `tmux` pane running real `uv run psi inspect ...`, then `C-c` after first partial Parquet | Pane prints sanitized cancellation; no final output and no staging residue | `FAIL report=none ...`; `inspect cancelled`; pane dead by `signal int`; temp parent empty |
| Strict lint and typing | `uv run ruff check ...` then `uv run basedpyright ...` over every changed Python file | Zero diagnostics | `All checks passed`; `0 errors, 0 warnings, 0 notes` |
| No-excuse changed files | `check-no-excuse-rules.py FILE` for every changed source and test file | Zero violations in changed files | `no violations` for every file |
| LOC | `wc -l` plus no-excuse pure-LOC rule | Every Python file under 250 pure LOC | Largest changed source file: `_output_lifecycle.py`, 236 physical lines; split test files 161/153/177 physical lines |

## Security mechanism observed

- Cold root is one random mode-0700 sibling opened through parent and root directory descriptors.
- Parquet and report reads/writes use `openat`-style `dir_fd` operations with `O_NOFOLLOW`; no `/dev/fd` child traversal, path fallback, or `chdir` is used.
- macOS publication uses `renameatx_np(RENAME_EXCL)` and unsupported runtimes fail closed.
- Cleanup recursively traverses the retained owned directory FD, then scans the immediate parent for the exact `st_dev + st_ino`; it never follows a replacement symlink.
- Warm invocation removes prior PASS before cache validation and verifies final-name identity before success publication completes.

## Red-to-green record

- Before remediation, `test_inspect_rejects_lexical_symlink_parent_without_mutating_target` returned PASS through a nested symlink ancestor.
- Before remediation, `test_inspect_cleanup_does_not_follow_swapped_staging_name` left the attacker-renamed owned staging tree.
- Both cases and the active-write variants pass in the final bounded suite above.

## Residual limits

- Source tree and trusted manifest must remain immutable for one invocation.
- Caller-supplied manifests are not authenticity signatures.
- Workbook/Parquet resource exhaustion is not quota-limited.
- File contents are fsynced but parent directories are not; sudden power loss can lose the latest rename.
- SIGKILL and delayed signal delivery inside native extensions are outside controlled cleanup.

## Cleanup receipt

- Removed owned `/tmp/psi-output-test.rBUDgA` after confirming it was empty.
- Killed owned tmux session `psi-c5-manual-sigint` and removed empty `/private/tmp/psi-c5-manual.QJKWI9`.
- No live `uv run psi inspect` process remained.
- Pytest-owned temporary directories were left to pytest cleanup.
