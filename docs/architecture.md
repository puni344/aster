# Following a call

## From microphone to a committed visit

1. React reads GET /api/dashboard. FastAPI reads a consistent SQLite snapshot and returns doctors, slots, masked visits, one journal revision and missing credential names. The client subscribes to GET /api/events. Either tab can be the first to connect.
2. Try call loads the call bundle. The browser verifies configuration, requests microphone access through PipecatClient and asks SmallWebRTCTransport to connect. The client posts an SDP offer to /api/offer. SDP describes codecs and media directions. The Python handler creates an aiortc peer and returns an answer. ICE selects a reachable route. The HTTP exchange sets up the connection; audio flows over WebRTC.
3. FastAPI starts a task for that peer. build_call creates the services, LLM context, tool callbacks and a fresh Conversation. PipelineWorker installs its RTVI processor and observer. On the client-ready handshake the server queues the greeting for speech synthesis. The remote audio track is attached to an HTML audio element.
4. SmallWebRTC input sends audio frames downstream. ElevenLabsRealtimeSTTService streams PCM to Scribe. The user aggregator's Silero analyzer observes speech boundaries. In manual-commit mode the STT adapter acts on the VAD stop signal and emits committed text. Interim speech can update the transcript. SpokenIdentity accepts only finalized STT frames carrying committed ElevenLabs result metadata for identity changes.
5. The universal user aggregator collects a turn into the LLMContext. GoogleLLMService sends the context and function declarations to Gemini. A text response proceeds to ElevenLabsTTSService. A function response invokes the Python callback registered under that exact name.
6. check_doctor_availability resolves the doctor and date against the schedule. It returns a maximum of three slot IDs and records which choices were offered. book_appointment accepts an offered ID. Both mutation tools obtain the phone from the session. The model has no phone or confirmation argument with which to authorize them.
7. SQLite serializes competing writers with BEGIN IMMEDIATE. The transaction checks current availability, writes the visit, inserts a monotonic journal entry and stores the idempotency result. The partial unique index covers active reservations only. A rollback also removes the journal entry. Cancellation checks phone, booking reference, active status and future time in the update predicate.
8. The tool returns a structured receipt after commit. The callback sends a call-local RTVI server message and returns the result to Gemini. React renders the receipt and refreshes its snapshot. Independent tabs read the committed journal through SSE and refetch. The chart-free summary, roster and register therefore share a source of truth.
9. The assistant aggregator records the completed assistant turn after audio output and exposes its interrupted flag. The backend compares a spoken-number candidate with the readback and opens a one-turn confirmation challenge. A clear affirmative in the next committed user transcript confirms it. Cancellation uses a separate challenge naming a visit. A partial correction invalidates the previous identity and requires the full number again.
10. Disconnect cancels the worker. Its host task disconnects the peer in a finally block. The browser releases the SDK session, detaches the audio track and clears timers. A new component session clears transcript, receipts, mute state and identity. Interrupting a call cannot undo a transaction that already committed.

## Decisions and trade-offs

| Choice | Problem solved | Alternative and trade-off |
| --- | --- | --- |
| SmallWebRTC on loopback | Low-latency browser duplex audio without a paid relay account | WebSocket PCM needs custom capture and playout. TURN or a hosted SFU would reach more remote networks. |
| Separate STT, text LLM and TTS | The assignment requires ElevenLabs at both ends. Text and tool boundaries are observable. | A speech-to-speech model reduces stages but changes the required integration. |
| Per-peer pipeline | Memory lifetime matches the call. Overlapping callers cannot share phone confirmation. | A shared global bot would save initialization work and introduce context mixing. |
| Silero plus speech timeout | Local speech activity and bounded turn-end detection | Fixed silence alone is simpler and less selective. Thresholds need tuning with real callers and background noise. |
| Exact confirmation phrases | An unrelated yes, an interrupted readback or a model boolean cannot confirm identity | Fuzzy semantic matching accommodates more language but risks approving ambiguous turns. |
| SQLite WAL | A portable clinic demo with durable transactions and independent read connections | PostgreSQL would suit multi-host writes and requires infrastructure. SQLite serializes writers. |
| Partial unique index and journal | One active booking per slot and durable change notifications | UI checks alone race. An in-memory event bus loses notifications across restarts. |
| HTTP snapshot plus SSE | Browsers can recover by rereading committed data after reconnect | WebSockets add duplex machinery. The journal poll interval trades up to about one second of nominal notification delay for simplicity. No end-to-end latency was measured. |
| React local state | Call state and operator views stay small and inspectable | A global store or cache library adds lifecycle rules for this scope. Monotonic request counters discard stale fetch responses. |
| Same-origin production build | Simple startup and backend-only credentials | Separate hosted origins require TLS, explicit CORS configuration and network deployment. |
| System typography and CSS | Local rendering, responsive layout and a small visual vocabulary | Hosted fonts and extra UI dependencies would add network and bundle costs. |

## File map

| File | Responsibility |
| --- | --- |
| backend/main.py | FastAPI lifecycle, snapshot, journal streaming, SDP/ICE endpoints, worker cleanup and static assets. |
| backend/voice.py | Actual provider graph, STT provenance check, runtime prompt, schema definitions and RTVI bridge. |
| backend/session.py | Spoken-number parser, per-call confirmation and cancellation challenges, tool dispatch. |
| backend/clinic.py | Clinic clock, schema, fictional roster, rolling slots, transactions and public projections. |
| backend/requirements.lock | Exact resolved Python environment for this Windows build. |
| frontend/index.html and src/main.tsx | Browser entry point, navigation, authoritative data fetching, SSE, schedule, register and summary. |
| frontend/src/Call.tsx | Browser SDK lifecycle, permission handling, transcript, timer, mute, audio waveform, receipts and cleanup. |
| frontend/src/data.ts | Shared frontend contracts, clinic timezone formatting and date arithmetic. |
| frontend/src/style.css | Responsive rail, schedule, tables, companion and reduced-motion rules. |
| frontend/package.json and package-lock.json | Build/test commands and exact JavaScript dependency graph. |
| frontend/vite.config.ts, tsconfig.json and src/vite-env.d.ts | API proxy, strict type checking and Vite types. |
| tests/test_clinic.py and test_edges.py | Transaction, authorization, dates, time preferences, correction and rollback checks. |
| tests/test_voice.py | Production graph construction and a local synthetic audio peer negotiation. |
| tests/browser_server.py | Test-process-only substitute worker and temporary database for browser acceptance. |
| tests/live_gemini.py | Explicit opt-in, one-inference Gemini lookup using actual schema and dispatch. |
| frontend/playwright.config.ts and tests/reception.spec.ts | Launch the isolated browser harness and exercise the component through browser controls. |
| frontend/tests/capture.mjs | Reproducible screenshots against the running normal application. |
| .env.example and .gitignore | Local configuration template and exclusions for secrets, runtime databases and generated files. |

## Production boundary

Phone readback prevents transcription mistakes. It cannot prove a caller owns the number. This local demo has no authenticated operator roles, audit access control, encrypted database, remote-media relay or retention policy. A production deployment would need identity verification appropriate to the clinic, private operator access, protected storage, network controls, provider agreements, load testing and monitoring. Only fictional data belongs in this application.
