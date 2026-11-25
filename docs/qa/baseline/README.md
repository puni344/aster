# Baseline and failure surfaces

The worktree was clean on master at 588ef8b99fb203b512ddf5c2e59df7cf7e222718. This commit is the recoverable baseline. The application database and credential file were excluded from every destructive test. At the first clock check on 25 November it was 12:51 IST. The submission deadline is 23:00 IST. Reserve 21:30–23:00 for the candidate.

The assignment PDF requires browser voice, Pipecat, real ElevenLabs STT and TTS, LLM tool dispatch, availability, booking, cancellation, spoken phone identification and readback, a synchronized dashboard, a repository, a short candidate description and a booking video. No OTP or account login is permitted.

| Boundary | What crosses it | Authority and failure surface |
| --- | --- | --- |
| Browser → FastAPI | SDP offer, ICE candidates, localhost microphone track | Media permissions, setup timeout, browser playout and stale callbacks |
| Peer → Pipecat | Audio frames, Silero turn detection, ElevenLabs committed transcripts | Fresh Conversation and worker per peer. Interims cannot establish identity. STT can misrecognize a valid number. |
| Assistant → caller | ElevenLabs audio and aligned assistant-turn events after transport output | Completed turn and explicit caller reply required. A server event cannot prove that the listener actually heard the question. |
| Gemini → Python | Four declared tool schemas in backend/voice.py | Validate arguments and session state in backend/session.py. Only spoken phone, completed readback, and action agreement can confer authority. |
| Session → SQLite | Clinic.available, owned and mutate in backend/clinic.py | BEGIN IMMEDIATE serializes writers. A partial unique index protects confirmed slots. Appointment, journal and request result commit together. |
| SQLite → dashboard | Snapshot plus SSE change journal; RTVI receipt to initiating caller | Snapshot reads share a transaction. React replaces stale requests by request ID. A receipt version prevents delayed results overwriting a newer outcome. |
| Error/disconnect → caller | Provider error classification, worker cancellation, release of client and timers | External quota and device playback remain independent of database health. |

Exact local versions were Python 3.12.16, Node 24.19.0, Pipecat 1.17.0, aiortc 1.16.0, google-genai 3.6.1, aiohttp 3.14.5, websockets 17.4 and FastAPI 0.165.0. The ElevenLabs adapters come from Pipecat. There was no separate ElevenLabs Python SDK installed. Browser SDK 1.17.0, SmallWebRTC transport 1.11.3, React 19.3.1 and Playwright 1.65.1 were locked. The local configuration selected gemini-3.5-flash. The example file defaults to gemini-2.5-flash.

Baseline commands were the project Python running pytest -q --tb=short, npm --prefix frontend run build, npm --prefix frontend test and Ruff's E9/F63/F7/F82 checks. The permitted loopback run passed 24 Python tests in 9.94 s. Edge passed 3 tests in 23.9 s. The build and lint checks exited 0. A restricted sandbox run stalled during network testing and was excluded. Vite warned about ignored Lucide client directives. Fixture teardown logged an audio track closing warning.

The baseline screenshots are [desktop](1440.png) and [mobile](390.png), rendered from the compiled application on loopback with an isolated database. Layout widths matched at 320, 390, 768, 1024, 1280 and 1440. The new red regressions are recorded separately in this folder.
