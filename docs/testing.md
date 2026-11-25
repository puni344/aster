# Verification report

**Submission verdict: NO-GO for the required live demonstration.** The local system and its deterministic workflow are implemented. No complete human-spoken call has been observed. The first Gemini inference invoked the right tool without returning usable slots; the next inference was rate-limited. ElevenLabs credentials were missing.

## Observed runs

| Run | Observation |
| --- | --- |
| Production frontend build | npm --prefix frontend run build completed TypeScript and Vite successfully. Vite warned about ignored use-client directives in Lucide modules. |
| Python suite | 17 tests passed, including production graph construction, local WebRTC audio decoding and STT-frame confirmation gating. |
| Browser suite | Edge exercised the live local transport using a synthetic input. The three tests cover dashboard navigation, call and register behavior, and error handling. See progress.md for the final run. |
| Clean local dependency install | Installed 90 locked Python distributions and 51 npm packages from local caches into an isolated copy. That build and the then-current 16-test Python suite passed. A fresh external machine or GitHub clone was not used. |
| Production screen capture | 1440×900, 1280×800 and 390×844. Document scroll width equaled viewport width in each capture. |
| Google key check | Model listing returned HTTP 200 and included gemini-2.5-flash. No credential value was displayed. |
| Live Gemini attempt 1 | Pipecat dispatched check_doctor_availability. It returned zero slots. The first probe did not retain sanitized lookup arguments, so the cause was not established. |
| Live Gemini attempt 2 | After improving doctor-name matching and supplying the clinic date to the probe, Google returned 429 RESOURCE_EXHAUSTED. No successful follow-up lookup was observed. |
| ElevenLabs | No configured key at verification time. No STT request, TTS request or successful provider audio claimed. |

## Adversarial scenarios

| Scenario | Expected behavior | Observed evidence and status |
| --- | --- | --- |
| A. Normal booking | Confirm spoken number, choose available slot, get real receipt | Verified in deterministic service and browser fixture. Human call not tested. |
| B. Incorrect readback, number correction | Block unrelated yes, invalidate old identity and require a new readback | Verified with wrong readback, interrupted readback, ambiguous response and last-digit correction cases. |
| C. Stale or unavailable time | Recheck inside transaction; return actual other slots | Verified with competing callers, past slots and preferred-time alternatives. Spoken negotiation not tested. |
| D. Switch doctor during conversation | Book only the caller's latest selection | Natural language decision change not tested. The service enforces membership in the call's offered slots. |
| E. Book and cancel in the same conversation | Same session, independent cancellation question | Verified with the same Conversation instance and browser fixture. Natural spoken conversation not tested. |
| F. Multiple visits | Return ambiguity; wrong phone cannot cancel | Verified at the service boundary. Spoken disambiguation not tested. |
| G. Interrupt assistant | Interrupted readback cannot authorize a mutation | Verified with assistant interruption flag. Physical barge-in not tested. |
| H. Ask to bypass confirmation | Model-provided confirmation cannot authorize a mutation | Verified via tool dispatch with missing confirmed speech identity. Spoken prompt variation not tested. |
| I. Concurrent booking | One active visit, one successful event | Verified with a thread barrier and separate SQLite connections. |
| J. Disconnect near commit | Committed state remains available to other tabs | Verified persistence and independent-tab updates, including reconnect. Exact disconnect-during-commit timing not tested. |
| K. Provider failure | Explain unavailability without announcing success | Verified missing-key UI and live Gemini 429 in probe. Mid-call ElevenLabs outage not tested. |
| L. Repeated book/cancel tool calls | Return original result or a truthful error; preserve event count | Verified by same- and different-request-ID checks. |
| Other failures | Recover after permission denial; isolate successive calls | Verified browser denial and per-session identity. Device unplug, autoplay rejection, prolonged silence and real-provider reconnection not tested. |

## Evidence interpretation

Production screenshots in docs/evidence start with baseline, pass1 and final. The baseline is the first greenfield implementation. The fixture-booked image shows an actual SQLite booking and a real local WebRTC connection with synthetic input and a test-only transcript. It is unsuitable as a provider demonstration. Browser teardown produced a Pipecat warning when the audio track closed; the final assertions completed.

The first browser run exposed two defects. Escape could lose its target when the end-call button disappeared, and the mic-denial flow lacked a reliable permission-state check. The implementation now handles Escape at the window, restores focus and checks both browser permission and SDK media-state errors. A screenshot of the booked fixture exposed overlap with summary counts; the desktop companion now gets its own column.

## Readiness rubric

These are internal evidence-based estimates from the build session, not NexovAI scores.

| Area | Score | Basis |
| --- | ---: | --- |
| Core voice and appointments | 14/30 | Local RTC, graph, native tool dispatch and transactions exercised. No full live speech flow. |
| Frontend craft | 20/25 | Two visual refinement passes, actual desktop/mobile renders, responsive schedule and dedicated call layout. No independent user review. |
| Engineering reliability | 16/20 | Concurrency, idempotency, rollback, correction, ownership and replay checks. Live failure coverage incomplete. |
| Real-time interaction | 6/10 | Cross-tab updates and real browser transport. Audible response and speech latency unverified. |
| Documentation | 8/10 | Setup, dependencies, file map, evidence and candidate exercises. Candidate's own description pending. |
| Demonstration readiness | 2/5 | Script prepared; required video missing. |

**66/100.** A passing suite is insufficient for submission until the required live booking succeeds.
