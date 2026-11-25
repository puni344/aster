# Upstream failure research

Reports were read from GitHub on 25 November 2026. The installed server is Pipecat 1.17.0. The issue state describes the tracker. A closed issue alone does not establish that a fix shipped in the installed wheel. Where the installed adapter or a runtime test supplied evidence, the last column identifies it. No production dependency was upgraded for this review.

| Source | Reported version | Tracker | Aster applicability, reproduction and disposition |
| --- | --- | --- | --- |
| [#1355](https://github.com/pipecat-ai/pipecat/issues/1355) | Unspecified in version field | closed | ElevenLabs alignment and interruptions. Browser fixture covers ordered final rendering. Multiple overlapping acoustic interruptions remain untested. |
| [#1361](https://github.com/pipecat-ai/pipecat/issues/1361) | Unspecified in version field | closed | Second report of the same interruption ordering symptom. Do not count these as two reproduced defects. |
| [#3862](https://github.com/pipecat-ai/pipecat/issues/3862) | Unspecified in version field | closed | Committed STT without the final flag. Installed manual-commit adapter sets finalized. Frame test and padded live call both produced a final. |
| [#4027](https://github.com/pipecat-ai/pipecat/issues/4027) | 0.0.105 | closed | TTS could block following frames following a socket error. High-latency TTS fault not reproduced. Keep the call error and teardown paths bounded. |
| [#4124](https://github.com/pipecat-ai/pipecat/issues/4124) | 0.0.107 | closed | Mute in mid-speech could strand VAD in speaking state. Tested mute UI while idle. Acoustic mid-turn mute remains open for manual testing. |
| [#4316](https://github.com/pipecat-ai/pipecat/issues/4316) | 0.0.102 / 1.0.0 discussed | closed | Duplicated alignment text. Same ElevenLabs model family. Exact duplicated alignment payload not reproduced. |
| [#4996](https://github.com/pipecat-ai/pipecat/issues/4996) | 1.5.0 discussed | closed | Played words lost on interruption. Aster rejects incomplete assistant turns. Simulated interrupted consent tested. Speaker playout is unverified. |
| [#5005](https://github.com/pipecat-ai/pipecat/issues/5005) | Unspecified in version field | open | Watchdog and mute can drop turn boundaries. Relevant to Silero pipeline. Idle mute tested only. Exact upstream timing not exercised. |
| [#5196](https://github.com/pipecat-ai/pipecat/issues/5196) | Unspecified in version field | closed | Paired STT finals when language detection is enabled. Aster uses adapter defaults with language detection off. Installed source suppresses the plain commit in paired mode. App also deduplicates exact final frames. |
| [#5197](https://github.com/pipecat-ai/pipecat/issues/5197) | 1.6.0 / 1.7.0 discussed | closed | Stale partial may reopen a turn. Browser now suppresses a partial carrying an already-final timestamp. Provider-level phantom VAD turn not reproduced. |
| [#5240](https://github.com/pipecat-ai/pipecat/issues/5240) | Unspecified in version field | closed | VAD speech without usable STT. Report describes Deepgram. Same class of silence can affect Aster. Equivalent live-provider condition untested. |
| [#5271](https://github.com/pipecat-ai/pipecat/issues/5271) | 1.2.0 through 1.7.0+ per report | closed | Early TTS context closure could stall output. Padded live sample produced remote PCM. This does not reproduce that race. |
| [#5823](https://github.com/pipecat-ai/pipecat/issues/5823) | 1.9.0 | open | Tool completion while the user speaks can lose the next LLM turn. Relevant. Confirmed database state can be recovered independently. Exact Pipecat race untested. |
| [#3290](https://github.com/pipecat-ai/pipecat/issues/3290) | 0.0.98 | closed | Parallel Gemini function calls rejected. Current live attempts failed for quota before dispatch. No conclusion about this specific 400. |
| [#3557](https://github.com/pipecat-ai/pipecat/issues/3557) | 0.0.100 | closed | Missing Gemini thought signatures. Installed adapter contains thought-signature handling. Multiple-call live compatibility remains unverified. |
| [#3273](https://github.com/pipecat-ai/pipecat/issues/3273) | 0.0.85+ (affects all versions with parallel tool execution) | closed | Parallel tool coroutine scheduling. Database concurrency tested separately. Framework dispatch ordering not independently reproduced. |
| [#4607](https://github.com/pipecat-ai/pipecat/issues/4607) | 1.3.0 | closed | WebSocket retry can fail after reconnect. Browser and application can signal a provider failure. Upstream double network failure not reproduced. |
| [#1570](https://github.com/pipecat-ai/pipecat/issues/1570) | Unspecified in version field | closed | Remote peer cannot finish ICE. Aster uses loopback and an empty ICE server list. Edge loopback verified. Cross-network WebRTC remains out of scope for local delivery. |

## Comparable implementations

- LiveKit front desk checks the selected slot and interruption state before the calendar write. Its evaluation can check the final calendar. Aster now tests the exact selected slot against independent SQLite rows. [Front desk agent](https://github.com/livekit/agents/blob/main/examples/frontdesk/agent.py)
- The Pipecat restaurant reservation example separates offered alternatives and confirmation. Aster tests declining the first offer and accepting the second. [Restaurant reservation](https://github.com/pipecat-ai/pipecat-flows/blob/main/examples/restaurant_reservation.py)
- The Pipecat food order example explicitly transitions to review and allows revision. Aster tests withdrawal, a changed slot and a changed doctor between proposal and execution. [Food ordering](https://github.com/pipecat-ai/pipecat-flows/blob/main/examples/food_ordering.py)
- The patient intake example retains collected information in per-flow state. Aster creates a new conversation for each peer and tests starting a new call after a completed fixture call. [Patient intake](https://github.com/pipecat-ai/pipecat-flows/blob/main/examples/patient_intake.py)
- The dental template documents timezone and timeout constraints at the calendar boundary. Aster exercises IST month and year rollovers and process death around SQLite commit. This source is an implementation brief. [Dental template](https://github.com/vossashtonai/pipecat-voice-agent-template/blob/main/examples/dental-clinic.md)
- The roof scheduling demo documents a Python booking tool that writes to Supabase. The accessible project description was reviewed. The raw agent code URL did not resolve during this review. [Roof scheduling demo](https://github.com/visaoenhance/livekit-agents-ui-demo)

## Test design references

The generated model checks live rows after every transition. The transaction tests use independent connections and a separate process that exits around commit. [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html) · [SQLite transactions](https://www.sqlite.org/lang_transaction.html)

Gemini proposes operations. Python validates the fields and spoken consent. Only a committed mutation may produce a structured receipt. [Google function calling](https://ai.google.dev/gemini-api/docs/function-calling) · [OWASP prompt-injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)

Browser fixtures, synthetic voice input and human observations have separate evidence categories. [Pipecat browser SDK](https://github.com/pipecat-ai/pipecat-client-web) · [Pipecat](https://docs.pipecat.ai/) · [ElevenLabs](https://elevenlabs.io/docs/)
