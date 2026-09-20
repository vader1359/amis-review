# C5 Manual QA — PSI inspect CLI

Build under test: `3e686be94834e343e3018bce1ddc69d20fa5957d`  
Surface: local CLI subprocess (`uv run psi inspect`).  
Manifest: committed sanitized golden manifest; retained evidence is redacted.

## Scenario brainstorm and augmentation

Scenarios were listed before execution; the second block adds adversarial/environmental cases.

### P0

1. `P0-01` `psi --help` prints help and exits 0.
2. `P0-02` `psi inspect --help` prints option help and exits 0.
3. `P0-03` cold inspect into a new external directory exits 0 and publishes PASS.
4. `P0-04` cold output contains exactly seven Parquets and one report.
5. `P0-05` warm inspect exits 0, reports seven hits, and preserves Parquet bytes/mtimes.
6. `P0-06` independently parse report JSON and recompute its semantic hash successfully.
7. `P0-07` all seven Parquets have expected ordered schemas/shapes and String columns via PyArrow.
8. `P0-08` six manifest source hashes are equal before and after cold/warm execution.
9. `P0-09` repeated fresh runs produce the same semantic hash and relation/cache identities.
10. `P0-10` stderr is concise, exit status is correct, and no traceback/path leak appears.

### P1

11. `P1-01` malformed TOML manifest fails closed without creating a first-run output.
12. `P1-02` hash-drift manifest fails closed without creating a first-run output.
13. `P1-03` missing source file fails closed without cache publication.
14. `P1-04` copied source workspace drift after cold is rejected before warm hits.
15. `P1-05` renamed projected header in a copied source is rejected.
16. `P1-06` truncated Parquet warm cache is rejected and stale PASS is replaced by FAIL.
17. `P1-07` valid-content Parquet with tampered metadata/content is rejected.
18. `P1-08` regular-file output is rejected without mutation or traceback.
19. `P1-09` output symlink is rejected without touching target.
20. `P1-10` traversal output is rejected without creating artifacts.
21. `P1-11` foreign/incomplete output state is rejected without creating a PASS report.
22. `P1-12` interrupted report/cache publication cleans temporary and newly-created roots.

### P2

23. `P2-01` unicode/CSV-boundary semantic hash distinctions remain collision-free through executable hash surface.
24. `P2-02` source and output mtimes remain stable across warm execution.
25. `P2-03` report excludes raw row values, absolute paths, and timestamp keys.
26. `P2-04` cache key/report relation ordering is deterministic.
27. `P2-05` empty/extra command arguments fail with normal CLI usage errors.
28. `P2-06` no unrelated source, DB, web, or git state is mutated.
29. `P2-07` no temporary cache/report residue remains after cleanup.
30. `P2-08` long-running cold invocation completes without partial final publication.

### Adversarial/environmental augmentation

31. `ADV-01` cache root symlink points outside the run root.
32. `ADV-02` report path symlink attempts to redirect an existing run.
33. `ADV-03` foreign file coexists with otherwise plausible output.
34. `ADV-04` incomplete cache has fewer than seven Parquets.
35. `ADV-05` cache has an extra foreign Parquet.
36. `ADV-06` cache Parquet has valid content but stale embedded integrity metadata.
37. `ADV-07` manifest uses source path traversal/absolute path.
38. `ADV-08` manifest removes a required projected header while updating source hash.
39. `ADV-09` a stale PASS report exists before a warm corruption failure.
40. `ADV-10` warm source bytes drift while output cache remains intact.

## Exact command evidence

Artifacts are listed in the matrix below. Raw cells, PII, and absolute temporary paths are intentionally omitted from retained logs.

<!-- Results and artifacts appended after execution. -->

## Surface evidence matrix

Exact invocation family for CLI rows: `uv run psi inspect --manifest tests/psi_tool/fixtures/golden_manifest.toml --output-dir <external-new-dir>`; mutations are explicitly described per row. All PASS rows reference non-empty artifacts.

| scenario id | criterion reference | surface | exact invocation/result | verdict | artifactRefs |
|---|---|---|---|---|---|
| P0-01 | C5 help | CLI | `uv run psi --help`; exit 0, 12 lines | PASS | A1 |
| P0-02 | C5 help | CLI | `uv run psi inspect --help`; exit 0, 10 lines | PASS | A1 |
| P0-03 | C4 cold | CLI | inspect to new external root; exit 0/PASS | PASS | A1 |
| P0-04 | C4 tree | CLI/filesystem | same cold root; 7 Parquets + 1 report | PASS | A1,A5 |
| P0-05 | C4 warm | CLI/filesystem | same inspect invocation twice; warm hits 7/7 | PASS | A1 |
| P0-06 | C4 semantic hash | JSON parser | independent parse/re-hash; match true | PASS | A2 |
| P0-07 | C3 PyArrow parity | PyArrow | independent readback of seven cache files; 7/7 | PASS | A2 |
| P0-08 | C3 source immutability | filesystem | SHA-256 before/after six sources; cmp exit 0 | PASS | A1,A6 |
| P0-09 | C4 determinism | CLI/filesystem | fresh cold runs and warm report identities; equal semantic hash | PASS | A1,A2 |
| P0-10 | C4 error boundary | CLI | failure probes; no traceback/path leak, concise validation failure | PASS | A3 |
| P1-01 | C1 malformed manifest | CLI | inspect with malformed TOML; exit 1, no root | PASS | A3 |
| P1-02 | C1 hash drift | CLI | inspect with one zeroed source hash; exit 1, no root | PASS | A3 |
| P1-03 | C1 missing source | CLI copied workspace | remove one copied source, inspect; exit 1 | PASS | A3 |
| P1-04 | C3 stale source | CLI copied workspace | cold then append bytes to copied source and warm; 0/1, FAIL report | PASS | A3 |
| P1-05 | C1 header contract | CLI copied workspace | rename projected header and update source hash; exit 1, no cache | PASS | A3 |
| P1-06 | C3 cache integrity | CLI | truncate one warm Parquet; cold 0, warm 1, FAIL report | PASS | A3 |
| P1-07 | C3 cache integrity | CLI | preserve content but tamper embedded metadata; cold 0, warm 1, FAIL | PASS | A3 |
| P1-08 | C4 output safety | CLI | output path is regular file; exit 1, sentinel unchanged | PASS | A3 |
| P1-09 | C4 output safety | CLI | output path is symlink; exit 1, target entries 0 | PASS | A3 |
| P1-10 | C4 traversal | CLI | output contains `..`; exit 1, no normalized run | PASS | A3 |
| P1-11 | C4 foreign state | CLI | pre-existing foreign output; exit 1, no report/cache | PASS | A3 |
| P1-12 | C4 interruption | pytest executable seam | targeted interrupted report hook; exit 0, 2 passed | PASS | A4 |
| P2-01 | C3 semantic boundaries | Python/Polars | unicode + null/empty CSV boundary hashes; 64 hex, distinct | PASS | A2 |
| P2-02 | C4 stability | filesystem | warm comparison; bytes/mtimes unchanged | PASS | A1 |
| P2-03 | C4 redaction | JSON/grep | independent report scan; 0 leak matches | PASS | A2 |
| P2-04 | C4 ordering | JSON | 7 relation entries, ordered schema/shape checks 7/7 | PASS | A2 |
| P2-05 | C2 CLI misuse | CLI | missing option and extra argument; exits 2/2 | PASS | A3 |
| P2-06 | C5 scope | git/filesystem | source hashes and dirty-worktree readback; no product writes | PASS | A6 |
| P2-07 | C5 cleanup | filesystem | external roots removed; zero `/tmp/psi-c5-*` directories | PASS | A6 |
| P2-08 | C4 completion | CLI | real cold completed with all 8 final files; no partial publish | PASS | A5 |
| ADV-01 | C4 symlink cache | CLI | cold then cache replaced by symlink; warm exit 1, target empty | PASS | A3 |
| ADV-02 | C4 symlink report | CLI | cold then report replaced by symlink; warm exit 1, target unchanged | PASS | A3 |
| ADV-03 | C4 foreign state | CLI | foreign file in output root; exit 1 | PASS | A3 |
| ADV-04 | C4 incomplete state | CLI | one-file cache only; exit 1, no report | PASS | A3 |
| ADV-05 | C4 foreign cache | CLI | complete cache plus extra Parquet; warm exit 1, FAIL report | PASS | A3 |
| ADV-06 | C3 metadata trust | CLI/PyArrow | valid Parquet with stale integrity metadata; exit 1/FAIL | PASS | A3 |
| ADV-07 | C1 path boundary | CLI | traversal source path in manifest; exit 1, no root | PASS | A3 |
| ADV-08 | C1 schema drift | CLI copied workspace | renamed required header; exit 1, no cache | PASS | A3 |
| ADV-09 | C4 stale PASS | CLI | stale PASS then corrupt warm cache; replaced with FAIL | PASS | A3 |
| ADV-10 | C3 source trust | CLI copied workspace | source bytes drift after cold; rejected before hit | PASS | A3 |

## Adversarial case matrix

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| ADV-01 | C4 | cache-root symlink | reject before touching target | PASS | A3 |
| ADV-02 | C4 | report-path symlink | reject and preserve outside target | PASS | A3 |
| ADV-03 | C4 | foreign output state | reject without PASS publication | PASS | A3 |
| ADV-04 | C4 | incomplete cache | reject without report | PASS | A3 |
| ADV-05 | C4 | extra cache artifact | reject and publish FAIL, never PASS | PASS | A3 |
| ADV-06 | C3 | metadata tamper | reject integrity mismatch | PASS | A3 |
| ADV-07 | C1 | path traversal | reject before source/cache write | PASS | A3 |
| ADV-08 | C1 | schema/header drift | reject required header mismatch | PASS | A3 |
| ADV-09 | C4 | stale success state | atomically replace stale PASS with FAIL | PASS | A3 |
| ADV-10 | C3 | source drift | reject before warm cache hit | PASS | A3 |

## Artifact references

| id | kind | description | path |
|---|---|---|---|
| A1 | log | help, cold/warm CLI, seven hits, semantic SHA, source/mtime parity | `c5/help-and-cold-warm.txt` |
| A2 | log | independent JSON semantic re-hash, PyArrow parity, boundary hashes, redaction scan | `c5/independent-parity.txt` |
| A3 | log | real CLI adversarial/error matrix and exit/results | `c5/adversarial-cli.txt` |
| A4 | log | full package and targeted interruption quality gates | `c5/quality-gates.txt` |
| A5 | log | exact output tree and non-empty artifact counts | `c5/tree-hash.txt` |
| A6 | log | cleanup receipt, six-source readback, snapshot/HEAD before-after | `c5/cleanup.txt` |

<verdict>PASS</verdict>
