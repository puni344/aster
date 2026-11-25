# Assignment traceability

Verification is scoped to the evidence in the third column. A locally constructed provider client does not establish live provider execution.

| Requirement and acceptance condition | Implementation | Evidence | Status |
| --- | --- | --- | --- |
| Browser start/end carries microphone audio to Python and closes the session | Call.tsx, main.py, voice.py | Edge synthetic microphone, real SDP exchange, Pipecat input-frame counter and end-call test | Verified for test media |
| Pipecat connects ElevenLabs STT, Gemini and ElevenLabs TTS in a single running conversation | voice.py | Production graph constructed; physical end-to-end call pending | Not tested live |
| ElevenLabs produces a transcript from the caller | ElevenLabsRealtimeSTTService, SpokenIdentity | Frame handling checked with constructed frames; no service credential | Not tested live |
| Gemini invokes an actual registered Pipecat tool | voice.py, tests/live_gemini.py | First live inference invoked check_doctor_availability | Verified |
| Live Gemini offers usable availability from that lookup | clinic.py and session.py | First live invocation returned zero slots; second request hit 429 | Failed live acceptance |
| ElevenLabs synthesizes and plays the agent response through the browser | ElevenLabsTTSService and remote audio element | Graph and playback binding present; no actual ElevenLabs output recorded or heard | Not tested live |
| All three exact tool declarations and handlers are registered | voice.py SPECS, registration loop and Conversation.invoke | Imported and constructed graph; deterministic dispatch tests cover all names | Verified locally |
| Resolve doctor/date and offer only available alternatives | Clinic.available | Tests for real slots, ambiguous and missing doctors, relative dates, preferred time and alternatives | Verified locally |
| Book selected slot atomically; return actual reference | Clinic.mutate, Conversation.invoke | Tests for unavailable/past slot, conflicting writers, idempotency, restart and rollback | Verified locally |
| Cancel future owned appointment and restore availability | Clinic.owned / mutate and Conversation.invoke | Tests cover wrong owner, multiple matches, explicit selection question, duplicate callback and reopened slot | Verified locally |
| Caller identified by spoken number with explicit readback | SpokenIdentity and Conversation | Interim and unrelated frames rejected, correction and interruption tests, current-call state only | Verified at frame/service level |
| Agent handles all actions naturally in one spoken conversation | runtime prompt and per-call context | Natural spoken booking, correction and cancellation require providers and a person | Not tested |
| Live transcript and call-local receipts | SDK user-input, bot-output, assistant-final and tool-end | Browser fixture drives events and real committed receipts. Evidence labeled fixture | Verified for fixture events |
| Doctors, specialties and open slots in a clean dashboard | main.tsx, clinic.py, style.css | Production screenshots at 1440, 1280 and 390 pixels wide; filters and keyboard navigation in Edge | Verified |
| Appointments update after book/cancel with no page reload | journal, SSE, snapshots, React refresh | Second browser tab observes commit; reconnect refresh and receipt checked with fixture | Verified |
| Silero VAD bonus | LLMUserAggregatorParams.vad_analyzer | Real Silero object constructed; human speech boundaries not measured | Not tested acoustically |
| Phone-style call screen, connecting/ended, timer and mute | Call.tsx | Edge RTC ready, mute/unmute, hang-up, keyboard closing and mobile screenshot | Verified for test media |
| Audio-reactive visualization, receipt, row feedback, mobile | canvas audio-level callbacks, structured receipts and CSS | Mobile width check, real booking receipt and booked slot screenshot from controlled call. Physical amplitude and animation timing not measured | Verified for UI; acoustic response not tested |
| Optional ring/end sounds | Omitted | No sound effect shipped | Not tested |
| Persistence, privacy and credential hygiene | SQLite, masked projections, .gitignore and .env.example | Restart test, masking assertion and ignored secrets/database checks | Verified locally |
| README, exact setup, environment example, learning and demo preparation | README.md and docs | Locked dependencies, clean local installation/build and test evidence | Verified locally |
| GitHub repository link | Local repository and complete source | Remote repository and publication pending | Not tested |
| Actual booking demo video of at most three minutes | docs/demo-script.md | Script prepared; recording requires successful live call | Not tested |
| Candidate's short pipeline description and ownership | docs/architecture.md and docs/interview.md | Candidate needs to review, explain and author the submission text | Not tested |
| Final submission via assigned form | Candidate action | No upload or submission made | Not tested |
