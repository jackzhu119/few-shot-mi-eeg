# CPU launch deadline correction

Continued `8b0395b16b8855c759f75dccc88cd66384da214a` on the existing research
branch. A final static review found that the CPU launcher's consumer timeout was
calculated before `Popen`, but its monotonic deadline was initialized only after
process startup and the fsynced start receipt. That intervening time was omitted
from the consumer limit and could overrun the approved absolute window.

This delivery corrects that operational timing boundary only. The CSP scientific
consumer remains byte-identical at
`ebc866734add9769c7b881332cb9362badaa0f6bf401bc2c6dfa717b645960f3`;
source inputs, science, threads, tolerances and accepted18 remain unchanged.
The handoff wording is also corrected: only `numpy.linalg.LinAlgError` during
`model.fit` is a recorded unavailable estimator attempt. Replay, prediction,
storage/hash/integrity and unexpected failures stop the invocation.

The independent remaining36 static review found no new blocking defect in the
fixed startup, identity, fresh-balance, timeout or receipt/resume checks. Its
contract remains exactly
`4352d0215e7338d7865975ed197fbf3e275fd860a0cab255de9d5617a034699f`.
The proposed limit remains three hours and USD1, with actual cost authorization
and absolute times null. The source HTTPS manifest remains disabled; enabling
restoration and binding the resulting manifest/contract digests requires the
already specified separate parent review. No current billing observation or
future top-up is inferred from the earlier snapshot.

No new scientific task, real CSP fit, GPU fit, checkpoint/EEG numerical load,
query, Pod operation, credential change or paper1 work is included. All16
original untracked files and seven protected scientific files were byte-checked
against the preceding preflight record. Parent execution authorization remains
pending; software review and tests cannot supply it.

The corrected launcher binds the elapsed deadline before process construction.
After receiving the child handle, an alarm bounds interruptible start-receipt
writes and monitoring with the original remaining time. Preflight and the claim
write are also bounded; an external active alarm is refused before claim creation
and preserved. Resource-triggered child stopping occurs once outside the consumer
alarm, avoiding repeated TERM grace. Both original wall and monotonic limits cap
monitoring and cleanup. OS process construction and uninterruptible kernel I/O
cannot be promised a hard userspace bound; time is never renewed when they return.

Final launcher SHA256:
`dae980fc8c685b3902921c51020b28452d52889faf5b0f6da0f41d8c638f34b6`.
Final CPU operation contract SHA256:
`7b94420fabbdd8878cf14b26a1ca5039061552f8225c9719b2a7d3baf29af42a`.
Only its launcher pin changed; resource/scientific limits and closed authorization
fields are unchanged. The new detached checksum binds those exact proposal bytes.

All44 CPU operation tests passed in0.49s, including six new deadline/cleanup cases;
scoped Ruff and diff checks passed. Children were inert sleep/exit processes or
mocks, never the scientific consumer. The implementer also reproduced the delayed
startup regression against the preceding version: it failed as expected because
that version continued monitoring after the synthetic elapsed budget expired.
The final independent static review found no remaining blocking issue.

The actual CPU metadata/resource preflight passed and stayed
`execution_authorized=false`; its full output is `metadata_preflight_run01.json`.
`parent_review_request.json` binds the unchanged18 ledger and separate CPU/36
review requirements. Neither a parent acknowledgement nor an authorization file
has been created. The previous141-test delivery is preserved; no unrelated
scientific test suite or experiment was repeated.
