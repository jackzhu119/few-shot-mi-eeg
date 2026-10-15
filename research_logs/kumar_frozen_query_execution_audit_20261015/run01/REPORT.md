# Actual accepted54 always-frozen query evaluation

The separately authorized query-only operation ran exactly once at fixed
commit `d34703ca5bccf7a5b88a91c2ffb2cba893f7cec8`, with contract SHA256
`fb3a429776e77a4ee8de96c8c7f2a833a4d311cedd8f0a9bcec3d0c6e8df225a`.
It completed all54 checkpoints and exited0. No source model was retrained,
no optimizer was constructed, and no support update or new strategy was used.
Original source accepted54 remains unchanged; acceptance of this new query
evaluation is pending the parent's actual readback and confirmation.

## Actual authorization, host and execution

The user relayed dot's actual decision issued2026-10-15T09:14:00Z for the
immutable09:14–11:14UTC window. External authorization SHA256 is
`137c42df93f99992e2a04603f0107fb6e02554ed3150566b6a57446069649dca`.
It binds this commit/contract, all54 original identities and the actually
observed host `94346a2083c4`, boot_id
`02e1dd56-6faf-45ed-b710-a28705535fb6`, pid1_start_ticks `54`.
Only query evaluation is permitted; training, optimizer, parameter/BN/
normalization changes, support access, new strategies and new resources remain
false. The frozen contract's `execution_enabled` flag was not changed.

The existing metadata check passed before raw query access. All54 original
archives were fully downloaded through the existing private R2 client and
verified:12,636,160bytes,54objects,0failures. All1189 input files totaling
1,043,686,331bytes passed full SHA256 before dispatch. The live memory, disk,
host, clean fixed checkout, exclusive claim and shared CPU lock gates passed.
No new environment or credentials were created and no Pod was operated.

Launcher PID23665 was dispatched09:22:19.414178UTC; worker PID23678 actually
started09:22:19.606977UTC. The launcher finished its receipt at
09:23:38.573155UTC; the outer dispatcher observed exit0 at
09:23:38.857527UTC. Worker start to launcher receipt completion was78.966178s;
this is not a separately measured exact inference-only duration. The deadline
was never reset. There was no retry, resume, cleanup signal or limit stop.
Both process identities were absent at the independent post-exit check.

The monitor retained312 discrete complete-process-tree samples, with actual
spacing0.252339–0.266983s. Maximum observed RSS was500,076,544bytes; minimum
cgroup headroom5,630,373,888bytes and host available9,224,253,440bytes. These
are sampled observations, not an assertion of continuous visibility between
samples. The original2GiB RSS/1GiB headroom/3GiB preflight/2GiB disk gates
and30-second deadline cleanup reserve were retained.

## Completeness and independent checks

All54 models evaluated the exact4290 included query events across18 published
participants and three seeds:12,870 prediction rows and324 seed/session metric
records. Source query contributes360 unique events; target query3930. All30
partial query exclusions remain excluded without replacements. All six sessions
per model, all seeds and all participants remain. There are76 original output
files /4,667,559bytes, including18 participant completion records.

Three separate audits were completed without a second model forward:

- Identity audit:8,026checks,0failures. All54 original archives and807 members
  (753 payloads plus54 manifests), checkpoint opaque-byte hashes and361 frozen
  metadata dependencies match. All1189 raw inputs were independently rehashed
  after execution and match the manifest, prelaunch and worker-before records.
- Numerical audit:203,421checks, maximum observed arithmetic difference0.
  Independently reconstructed every label/argmax/confusion/recall/BA, all seed,
  session and participant means, all aggregate fields and six fixed participant
  bootstrap summaries using10,000resamples/seed42.
- Operation audit:actual authorization/window/host, claim/lock, original pins,
  launch/exit, resource samples,76 output hashes and final completeness passed.

For each of54 models, the runtime parameter/BN/normalization state digest
before and after prediction equals the accepted archive's frozen-state digest.
The independent auditors bound those recorded digests to the original checkpoint
and result bytes; they did not pretend to reconstruct transient process memory
or rerun the model. No original archive, input, ledger, scientific configuration,
numerical thread setting or1e-7 source-replay tolerance changed.

## Frozen scientific readout

All three seeds were averaged within participant/session before averaging five
target sessions within participant. Source query is separate. These are
exploratory follow-up results given previously exposed test identities.

| Cohort | Target BA | 95% participant-bootstrap interval | Source-query BA |
| --- | ---: | ---: | ---: |
| Development6 | 52.3087% | 48.4301%–57.3582% | 52.7778% |
| Fixed remaining12 | 51.5783% | 49.0800%–54.5125% | 52.9167% |
| All18, secondary | 51.8218% | 49.5930%–54.3590% | 52.8704% |

The always-frozen cross-session baseline is close to chance; each target cohort
interval includes50%. This is not a newly performed formal chance hypothesis
test. There are16 class-collapsed model/session results across7 models and7
participants:2source-query and14target-query instances. All remain in the
reported means. No query rule, participant exclusion or best seed was selected.

This run supports a weak source-only neural baseline under the frozen small
source-data protocol; it does not establish a task-aware gate, adaptive benefit,
clinical effect or human skill retention. The original CPU primary comparison
is unchanged, and no new CPU-baseline contrast was calculated here.

## Preserved failures, private archive and pending acceptance

The first read-only operation-auditor attempt hit a schema TypeError by treating
`failed_files` as an integer instead of its actual list. Its correction receipt
is preserved; only the audit schema check changed. There was no scientific
failure/retry. Immutable executed audit scripts retain two harmless E702
formatting findings; the scoped non-formatting check and exact validation
commands are recorded separately. No executed evidence bytes were rewritten.

The original worker/launcher flags still say independently_audited=false,
R2_full_GET_verified=false and accepted=false because they are historical
producer evidence. Later audit/R2 stages are recorded separately. Full private
result/evidence R2 GET counts, exact object list, bytes and failures are in
`r2_full_get_receipt.json` after the actual transfer, with an independent closing
comparison. `parent_acknowledgement_request.json` requests actual review of this
query operation, not another acceptance or execution of the54 source fits.
No parent confirmation is fabricated and no further experiment is released.
