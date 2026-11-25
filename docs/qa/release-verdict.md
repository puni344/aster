# Release verdict — 25 November 2026

**NO-GO for unconditional submission under the specified gates.** The implemented application completed a browser booking and cancellation with real ElevenLabs STT, Gemini Flash-Lite tool calls and ElevenLabs TTS. The caller input was synthetic. The physical-microphone acceptance recording and candidate-led corrected readback remain outstanding.

## What an evaluator can verify

The successful call booked Dr Asha Menon for 26 November at 09:00 IST. Aster spoke reference AS-FEC6CFEF and the companion displayed it. A separate, read-only SQLite connection observed one confirmed row and journal event. In the same conversation, Aster requested cancellation confirmation, cancelled that reference and displayed its cancelled receipt. A second read checked the two journal entries, the cancelled row and the reopened 09:00 slot through the production dashboard endpoint. [Browser transcript](evidence/live-final.txt) · [Sanitized tool trace](evidence/verified-tool-trace.txt) · [Booking row](evidence/live-ledger-observation.json) · [Cancellation and open slot](evidence/live-ledger-final.json)

| Evidence category | Result |
| --- | --- |
| Deterministic backend | 87 passed, 0 failed, 0 skipped. Combined statement/branch coverage 87%. [pytest](evidence/pytest.txt) · [Coverage](evidence/coverage.txt) |
| Property and concurrency | 100 phone-format examples, 100 invalid length examples and 120 passing generated state-machine examples. Synchronized groups of 2, 10 and 50 writers each left exactly one active appointment. Concurrent snapshot reads were consistent with the journal. |
| Fault and mutation | Process death before commit left no partial rows. Death after commit left one recoverable booking. Lock contention, rollback, stale acknowledgement and cancellation races passed. Six targeted mutations were detected in disposable copies. [Mutation results](evidence/mutations.txt) |
| Simulated conversations | 8/8 scripted cases passed their row, identity, slot and receipt expectations. These cases are included in the backend count. [Scenario definitions](../../tests/conversations.json) |
| Frontend | 2 unit tests and 7 Edge integration tests passed. The TypeScript/Vite production build and Ruff passed. The browser suite checked two tabs, raw fixture SQLite rows, receipt ordering, input denial and an unanswered permission prompt. [Browser results](evidence/browser.txt) · [Unit results](evidence/frontend-unit.txt) · [Build](evidence/build.txt) |
| Real LLM lookup | Original Flash probe returned HTTP 429. One Flash-Lite cardiology lookup succeeded with three independently verified slots. Flash-Lite is now the default. [Lookup trace](evidence/flash-lite.txt) |
| Real STT corpus | 9/9 synthetic clips finalized. The final parser matched 4/4 independently specified phone targets, including a correction. No human accent claim. [Phone and latency results](performance.md) |
| Real browser voice | Two availability calls on the original model ended at Gemini quota. Three Flash-Lite book-and-cancel trials ran during repair. Trial 1 repeated the slot question, trial 2 repeated phone collection, and the final trial completed both actions. End-to-end success for that protocol was 1/3 across revisions and 1/1 on the final tested revision. [Trial 1](evidence/live-book-cancel.txt) · [Trial 2](evidence/live-turn-retest.txt) · [Final call](evidence/live-final.txt) |
| Physical microphone | Zero candidate microphone trials were independently observed in this review. Physical barge-in, audible corrected readback and the video remain open. [Manual acceptance script](manual-voice-tests.md) |
| Installation and evidence | Fresh Windows environment installed 94 Python packages using copy mode, npm ci and production build succeeded, and 10 isolated smoke tests passed. Six widths had no document overflow. [Install](evidence/clean-install.txt) · [Viewport measurements](evidence/viewports.txt) · [Secret scan](evidence/credential-scan.txt) |

## Scope and remaining work

The [334-case scenario inventory](scenario-matrix.csv) records 181 passes within the stated evidence level, 131 not run, 21 blocked and one inapplicable unsupported-rescheduling case. The counts describe distinct requirements and often point to shared executable tests. They are separate from process test counts. The live calls above add provider-level evidence to the core workflow. Untested cases and broad guarantees remain open. [Invariant coverage](invariants.md) · [Known limitations](limitations.md)

The release work fixed wrong-slot authorization, misleading cached receipts, ambiguous phone handling, unrelated-answer confirmation, split affirmative transcripts and stale receipt rendering. [Defect register](defect-register.md) · [Initial architecture and baseline](baseline/README.md) · [Upstream research](upstream-failure-research.md)

[Desktop before](baseline/1440.png) · [Desktop after](evidence/screenshots/1440.png) · [Mobile before](baseline/390.png) · [Mobile after](evidence/screenshots/390.png) · [Fixture cancellation screenshot](evidence/screenshots/fixture-cancelled.png) · [Exact reproduction commands](test-results.md)

The submission deadline is 23:00 IST. The remaining candidate steps are the real-microphone acceptance trial, the booking video of at most three minutes, a pipeline explanation in the candidate's own words, and submission through the assignment form. Verify that the evaluator can access the private repository.
