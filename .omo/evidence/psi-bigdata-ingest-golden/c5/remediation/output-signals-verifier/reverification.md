# C5 output/signals independent reverification

Verdict: **VERIFIED**

- HEAD: `3e686be94834e343e3018bce1ddc69d20fa5957d`
- Product snapshot method: `shasum -a 256 pyproject.toml uv.lock src/psi_tool/*.py tests/psi_tool/*.py tests/psi_tool/fixtures/golden_manifest.toml docs/psi_tool_v1/contract.md | shasum -a 256`
- Product snapshot: `a46b1c8c48d6c22e699a4cfe71d7cb910c9bf5649b087c4eb5f23f7dc8bf0083`

## Previously failing ancestor race

Fresh run of `tests/psi_tool/test_ancestor_swap.py`: **2 passed in 53.49s**.

- A parent-name swap between lexical targeting and descriptor acquisition can
  no longer redirect staging or cache into the separate target. Its sentinel
  remains byte-identical; neither requested path can claim PASS; no owned
  temporary directory remains.
- A parent-name swap after the parent descriptor is retained and during
  publication cannot leave a claimable PASS. Post-publication chain mismatch
  removes the exact held output inode through the retained parent descriptor;
  unrelated target content remains unchanged.

Inspection confirms `_fd_walk.open_parent_chain()` opens `/` once, then every
ancestor component using the prior `DirectoryFd` plus
`O_DIRECTORY|O_NOFOLLOW`. It retains every `(st_dev, st_ino)` pair and
descriptor. `verify_parent_chain()` independently walks and compares the full
chain after acquisition and before/after publication. No full parent path is
reopened.

## Focused behavioral gates

- `test_cli_signals.py`: **5 passed in 63.36s**. Real new-session/process-group
  SIGINT/SIGTERM return exactly 130/143 with sanitized `inspect cancelled`,
  cold output and `.run-*.tmp` absent, warm PASS replaced by FAIL, and a second
  signal cannot interrupt controlled cleanup.
- `test_output_lifecycle.py`: **4 passed in 10.99s**. Destination-appears,
  symlink, renamed-stage, and warm-name swap cases preserve external bytes and
  do not escape cache/report writes.
- Relation-pin plus VerifiedManifest concurrency tests: **6 passed in 18.24s**.
- Fresh real CLI cold/warm: exits 0/0, semantic SHA
  `8a3437cd8392c9d56c01113f0ee693376a54512a86d1f092880a819595ca9955`,
  exact eight files (seven Parquets plus report), seven warm hits, and seven
  actual relation hashes equal their manifest pins.

The first combined focused command was stopped after more than eight minutes
without terminal output and replaced with the bounded file-by-file runs above;
no result from the stopped command is claimed.

## Static and quality gates

- Ruff strict check: PASS.
- Ruff format check: PASS, 34 files formatted.
- basedpyright: PASS, 0 errors, 0 warnings, 0 notes.
- No-excuse on 14 remediation source/test files: PASS. Package-wide scan reports
  only two pre-existing mutable exception dataclasses in `_contract_errors.py`;
  neither belongs to this lifecycle remediation.
- Pure LOC: every production/test Python file is at most 250 pure LOC.
- Production cache/report writers accept `DirectoryFd`; no arbitrary-`Path`
  writer remains. Searches find no `tempfile`, `rmtree`, `chdir`, `/dev/fd`
  child path, path-replace fallback, `Any`, cast/type-ignore, blanket exception,
  pandas, DuckDB, database, or web dependency in the verified production scope.
- Native publication remains Darwin `renameatx_np(RENAME_EXCL)` and unsupported
  runtimes fail closed with `ENOTSUP`; there is no precheck/plain-rename fallback.

## Residuals and slop review

Documentation accurately limits guarantees for manifest/source immutability,
caller-manifest authenticity, resource exhaustion, missing directory fsync and
power loss, SIGKILL, and native delayed signal delivery. Focused tests are
behavioral; no deletion-only, tautological, requested-removal, or
implementation-mirroring blocker was found.

## Cleanup

All verifier-created output roots were removed. The stopped pytest process was
terminated by this verifier; no verifier-owned process, session, or temporary
runtime artifact remains.
