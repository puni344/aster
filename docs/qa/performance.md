# Performance and audio evidence

| Boundary | Scope | n | Measured result |
| --- | --- | ---: | --- |
| Availability service call | Seeded temporary SQLite, includes two snapshot queries where applicable | 100 | median 7.59 ms, p95 13.98 ms |
| Successful booking transaction | Local service call including commit and connection close | 100 | median 7.27 ms, p95 12.29 ms |
| Successful cancellation transaction | Same local run | 100 | median 9.04 ms, p95 12.64 ms |
| Click to remote WebRTC track attachment | Production browser, padded synthetic input | 1 | 5,053 ms |
| Explicit STT commit to committed transcript | Real ElevenLabs WebSocket, synthetic files, manual commits | 9 | median 355 ms, range 335–591 ms |
| Commit observed by fixture to second tab's confirmed-row assertion | Includes SSE polling, HTTP refresh, React rendering and Playwright assertion | 1 | 920 ms |
| Hangup click to Ended assertion | Browser fixture | 1 | 98 ms |

The slowest measured boundary was establishing the live remote track. The benchmark includes 200 committed mutations and independently verified 100 cancelled rows, zero active rows and 200 events. [All transaction samples](evidence/performance.json) · [Browser trace](evidence/browser.txt) · [Live audio trace](evidence/padded-live-call.txt)

Provisional local targets are under 100 ms at p95 for the SQLite operation and under 2 seconds for a second-tab refresh. No reliable measurements of human speech-end to STT, transcript to first Gemini output, tool result to first synthesized audio or speech-end to first reply were obtained. STT explicit commit and end of human speech are different boundaries.

## Synthetic speech

An offline Microsoft David Desktop voice generated nine fictional files. The corpus included normal, slow and fast phone readouts, a correction, doctor name, specialty, time, confirmation, refusal and interruption language. Scribe v2 Realtime finalized all nine. The doctor and relative day were transcribed correctly in the single availability clip. No live model interpreted that clip's calendar date in this benchmark.

The four phone transcripts, rescored against independently specified literal numbers with the final application parser, matched **4/4**. The correction exposed a parser defect. A phrase naming the last digit followed by the entire number had previously been concatenated into an invalid number. The fix checks the correction digit against the full replacement. The original live script compared parsed expected and observed text, which could misleadingly equate two invalid parses. Use the independent offline rescore for this metric. [Retained fictional transcripts](evidence/synthetic-stt.jsonl) · [Independent phone targets and scores](evidence/stt-score.json) · [Red regression](baseline/corrected-full.txt)

With the documented lexical normalization, 45 word edits across 70 reference words give 64.3% word error rate. A perfectly recognized ten-digit phone rendered as one numeric token counts as ten lexical edits in this measurement. Use phone exact match to assess the business risk. One voice and four numbers/readings do not establish accuracy across accents, noisy rooms or hardware.

The first browser sample repeated a short WAV immediately at connection and transcribed “Tomorrow, tomorrow.” No nonzero greeting audio was observed. The second used a silent lead-in and produced the full intended availability request and a remote audio peak of 0.1584. Both calls ended with the Gemini quota message. Two trials, zero completed browser conversations. Human microphone trials in this review: zero.

A later Flash-Lite trial passed a real browser booking and cancellation. The two quota failures above refer to the original Flash model. See [the release verdict](release-verdict.md) for every live attempt.
