# Independent static execution-boundary review

Reviewed at 2026-10-16T03:20:28Z. Scope: the new budget CPU runner's authorization,
worker entry, shared lock, fresh outputs, monitoring, failure preservation,
cleanup and input identity, against section 5 and the input-preservation rules
of `docs/kumar_component_exploratory_protocol_20261016.md`.

- Reviewed runner SHA256:
  `4686a0d078797c2bdd28d388adce543ff95120ab64a8e29c7bf59f31c396a8c2`.
- Protocol SHA256:
  `1c3e87ad634148bde031579cd8efb976e75643635d452a2ea69d911ccc9b09fc`.
- This reviewer read code only. No real EEG, GDF, weights or scientific runner
  execution; no credentials, fit, query forward or new statistics. Only this
  review report was added.

The substantive issues identified in the initial implementation have matching
repairs in this revision. No remaining blocking execution-boundary defect was
identified by this static review within the stated scope.

| Initial issue | Repair observed in reviewed revision |
| --- | --- |
| Calls to reused `process_record` omitted its required procfs argument, preventing launcher/worker startup. | Both calls explicitly pass `Path("/proc")`. |
| TERM/HUP could terminate the launcher while its separate-session scientific child continued without monitoring. | Launcher installs TERM/HUP exception handlers and routes interruption through one cleanup boundary. |
| Wall-clock loop checks did not bound Python-visible blocking operations and could be affected by clock changes. | Existing monitor `deadline_guard` and a fixed monotonic deadline cover claim publication and monitored execution; the scientific boundary reserves 30 seconds for cleanup. |
| Cleanup exceptions could skip failure-receipt publication and lock-FD close. | Cleanup failures and signal events are captured; receipt writing and nested FD/handler restoration remain in `finally` paths. |
| A second launcher losing the lock race could write into another launcher's newly created operation directory. | `state_owned` becomes true only after this launcher's successful exclusive mkdir; only that owner writes the operation receipt. |
| Zero root exit could be described as completed even when descendants needed termination. | Observed descendant cleanup records signals, preserves a separate nonaccepted status and raises; zero exit without such cleanup remains pending independent audit. |
| Internal worker accepted a caller-provided claim and a previously unheld lock FD without demonstrating the intended launcher entry. | Worker checks canonical claim/output identity, actual parent's script plus `--execute`, absence of internal-worker mode in the parent, PID start ticks, host identity, bounded monotonic/epoch deadlines and inherited shared-lock inode. Ordinary Python switches are parsed by `is_launcher_command`, including `-u`, separate/attached `-W` and `-X`. |
| Source-model/file validation was limited to loading or in-memory state. | Source NPZ and original fit-audit identities are checked; every participant has a postcheck; all consumed dataset/source-model files and required loader text pins are rehashed after the whole consumer, with a new before/after manifest. Config, protocol, code, split, authorization, old receipt and saved predictions are rechecked before the final scientific receipt. |

Fresh scientific output and fresh operation state are exclusive, with no automatic
retry. The worker verifies the frozen historical fit scopes, and the launcher
retains resource samples and a pending-audit status instead of asserting
independent acceptance. This review does not evaluate the budget/EA numerical
implementation or establish that a scientific operation has succeeded.

## Required validation before real execution

Static review does not replace synthetic lifecycle tests. Those tests remain
required for: a standard launcher command and ordinary interpreter switches;
generic-parent/internal-worker rejection; claim/authorization/host/PID/lock and
deadline mismatches; lock contention and foreign-state nonmutation; worker failure;
TERM/HUP; timeout and resource-limit interruption; cleanup failure and surviving
descendants; input mutation; and fresh-output refusal. They should confirm that
failure evidence survives and that no failed or cleanup-required operation is
marked scientifically accepted. This reviewer did not run those tests.

The reused monitor documents the practical boundary of its guarantees: procfs is
sampled rather than atomic, and Python-visible deadline guards do not make OS
process creation or uninterruptible kernel I/O hard-real-time operations. The
revision should retain those limits when describing execution evidence.
