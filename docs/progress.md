# Aster progress · 24 November 2026 IST

**Resume point:** the local application is built and served at http://127.0.0.1:8000. The next acceptance gate is a genuine spoken booking. Configure ELEVENLABS_API_KEY locally, confirm realtime STT and streaming TTS entitlement, and use a Gemini model with available free quota. Restart the backend. The candidate still needs to record and submit the demonstration.

| Build step | Implementation and observed check |
| --- | --- |
| Requirements and host | Read both identical master prompts and the assignment PDF. Started in an empty Git repository. Windows, i5-1235U, approximately 16 GB RAM, Node 24.19.0. Isolated Python 3.12.16 installed. |
| Research and graph | Read official SDK docs and inspected the installed implementation. Created backend/voice.py with the three required function declarations, ElevenLabs WebSockets, Gemini, Silero and SmallWebRTC. Constructed the graph in a native Windows test. |
| Business workflow | Implemented rolling SQLite slots, partial unique index, transaction journal, retry handling, caller ownership and call-local confirmation based on committed speech. Tests exercise independent connections and forced rollback. |
| Operational UI | Implemented React/Vite schedule filters, register, call companion, transcript, audio-level canvas, receipts and cross-tab updates. The only normal call path constructs the provider worker. |
| Screen inspection | Captured the first greenfield render at three sizes. Refined hierarchy, removed redundant labels and moved the empty register into the working area. Inspected phone and desktop again, separated failed-call guidance from transcript content and gave the desktop companion its own column. Reviewed final screenshots and a clearly labeled fixture receipt. |
| Browser failure recovery | Initial browser suite had one pass and two failures. Fixed lost Escape handling after hang-up and missing microphone-permission handling. Browser coverage now includes permission denial, synthetic browser audio, mute, transcript finalization/deduplication, receipts, cancellation and disconnected-tab recovery. |
| Provider evidence | Gemini model listing HTTP 200. First free-tier inference invoked the correct native tool but returned no slots. Added doctor-title normalization and aligned the smoke test's date with the clinic. Second authorized inference failed with 429 RESOURCE_EXHAUSTED. Cause of the first empty result was not confirmed. ElevenLabs live verification remains blocked. |
| Installation and final tests | Installed locked dependencies in an isolated copy, built the production bundle and passed its then-current 16 Python tests. Final working-tree suite: 17 Python tests passed. Playwright: 3 passed. All three captured viewport widths matched document widths. |
| Submission preparation | README, research, architecture and file map, requirements matrix, evidence report, 20 interview questions and timed demo outline are present. The user must provide the candidate-authored description and live recording. |

## Commands exercised

```powershell
.\.venv\Scripts\python -m pytest -q
npm --prefix frontend run build
npm --prefix frontend test
node frontend/tests/capture.mjs baseline
node frontend/tests/capture.mjs pass1
node frontend/tests/capture.mjs final
.\.venv\Scripts\python -m tests.live_gemini
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Use the requirements matrix to separate local verification from live-provider acceptance. No actual patient information, raw audio or transcripts were saved by the application. No video, hosted repository or submission receipt is claimed.

Final hygiene check: Ruff passed. A filename-filtered scan of 35 candidate text files found zero matches for the checked Google-key, ElevenLabs-key and private-key patterns. Git ignored the real .env, SQLite database, installed dependencies and build output. The live working tree still lacked ELEVENLABS_API_KEY. A local code checkpoint is prepared for the next review phase; publication is pending.
25 November 2026: The local free-tier Gemini 3.5 Flash probe invoked check_doctor_availability for Dr Asha Menon on 26 November and returned three slots from the isolated SQLite schedule. Selected gemini-3.5-flash in the local environment. End-to-end spoken booking still needs verification.
25 November review: corrected the reported duplicate, implemented transactional rescheduling with stable references and added service and browser regressions. See docs/reschedule-review.md for the prioritized visual audit and provider evidence. A live Edge test verified non-silent remote audio and the correct ElevenLabs transcript before a Gemini 429.

Release hardening completed locally with an independently checked provider-backed synthetic booking and cancellation. See [current gates and evidence](qa/release-verdict.md). Human microphone acceptance is outstanding.
