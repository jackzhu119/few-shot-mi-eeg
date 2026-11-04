# Independent P2 code review and saved-output verification

**PASS for the final saved outputs and repaired phase boundary.** The original run01 exception, its code bytes, 362 prior completed cells and private model identities remain preserved.

## Scientific core

Kumar's four main arms share fixed H21 CAR-effective coordinates and one MNE CSP4/Ledoit–Wolf/full-rank plus LDA lsqr/automatic-shrinkage core. BNCI retains its original 22-coordinate inputs and fixed 0.1 CSP/LDA core. Direct comparisons of all nine BNCI Full and all nine BNCI EA saved vectors found no differences from their historical counterparts. Diagonal coordinates are explicitly fixed; source and current-support references are separate, and the query reference remains fixed. Trial RMS changes one scalar per trial and uses no batch reference.

## Actual independent checks

- 576 cell records comprise 396 completed matched main fits, 148 completed EA phase fits and 32 original undefined phase cells.
- 544 unique claims correspond exactly to the 544 completed models. Undefined cells have no fit claim.
- All 362 original completed-cell file SHAs and corresponding model identities are unchanged across continuation.
- All 544 private model files were read in full and their SHA256 values match the output records.
- Scalar/exact-confusion replay of all 544 saved label, decision and probability records passed 5,440 numeric checks; the maximum difference was 3.3306690738754696e-16. Probabilities are finite and within [0,1], and their class-1 threshold decisions agree with the saved predictions. Balanced NLL uses clipping at 1e-7; Brier uses the class-balanced, single-coordinate binary definition.
- All 180 original Full phase rows were checked for support/query identity hashes and counts. All 148 originally defined cells are complete. All 32 undefined-query-missing-class statuses and class counts remain undefined and unfitted.
- The model-state statements combine saved runtime unchanged-state flags with independently checked private-file hashes. No second forward was performed.

## Original boundary and repair

Run01 stopped after 362 fits because a 20-left/0-right query at sub-11/ses-4 had no historical Full predictions. The corrected wrapper checks the original Full status and common IDs/counts before claiming a fit. It also honors the other original undefined statuses instead of weakening the valid-cell join. The initial failure was real and is retained. Continuation computed only 182 unattempted fits, including 42 phase fits. The scientific core SHA remained unchanged.

Actual time from first dispatch to final exit 0, including the pause, was 443.599036 seconds, within 7,200 seconds. The runner's monotonic guard is per process; this observed elapsed-time check does not establish a persistent cross-process deadline guard. These completed outputs require no further execution.

Only non-scientific storage/hash fault and undefined-phase tests were run by this reviewer: **3 passed, 13 deselected in 0.25 s**. They used dummy fit callbacks, not real EEG or scientific fitting. Full synthetic-fit test results remain identified as the implementer's existing record. This reviewer did not edit production code.

Exact source hashes, claims/receipt linkage, counts, actual test output and scope are in `P2_CODE_REVIEW.json`. Historical results and the P1 independent check remain unchanged.
