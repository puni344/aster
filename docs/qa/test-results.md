# Reproducing the checks

From the repository root in PowerShell, install backend/requirements.lock and tests/requirements-qa.txt into Python 3.12. Use Node 24 with npm and run npm --prefix frontend ci. For a uv-created environment without pip on OneDrive, run uv pip install --link-mode copy --python .venv/Scripts/python.exe -r backend/requirements.lock -r tests/requirements-qa.txt.

| Check | Command |
| --- | --- |
| Fast consent smoke | .venv/Scripts/python -m pytest -q tests/test_conversations.py tests/test_release.py |
| All deterministic backend checks | .venv/Scripts/python -m coverage run --branch --source=backend -m pytest -q --hypothesis-show-statistics |
| Coverage and lint | .venv/Scripts/python -m coverage report -m and .venv/Scripts/ruff check backend tests |
| Independent generated sequences, crashes and contention | .venv/Scripts/python -m pytest -q tests/test_properties.py tests/test_interactions.py |
| Frontend unit and compile | npm --prefix frontend run test:unit then npm --prefix frontend run build |
| Browser integration | npm --prefix frontend test |
| Mutation quality | .venv/Scripts/python -m tests.mutations |
| Credential scan | .venv/Scripts/python -m tests.scan_credentials |
| SQLite measurements | .venv/Scripts/python -m tests.benchmark |
| Live Gemini, single opt-in lookup | .venv/Scripts/python -m tests.live_gemini --case 0 (case 1 tests cardiology and case 2 ENT) |
| Offline synthetic corpus generation | powershell.exe -NoProfile -File tests/make-audio-fixtures.ps1 |
| Real STT, bounded and opt-in | .venv/Scripts/python -m tests.live_stt_corpus |
| Offline rescore of retained sample | .venv/Scripts/python -m tests.score_stt docs/qa/evidence/synthetic-stt.jsonl |
| Start a disposable desk | Set ASTER_DB to a new local SQLite path and run .venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8023 --no-access-log |
| Real dashboard screenshots | node frontend/tests/qa-viewport.mjs |
| Full provider browser probe, opt-in | Set ASTER_BASE_URL to the disposable desk origin. Run node frontend/tests/live-audio.mjs with the absolute path to a fictional WAV with a silent lead-in. |

Mode A replays eight cases in tests/conversations.json in a fresh SQLite database per case. The harness permits one lookup and at most two booking calls. It checks exact row count, owner, slot, reference and event count after each scenario. Mode B uses actual Pipecat/Gemini dispatch and independently checks returned slot IDs against SQLite. Mode C supplies a synthetic microphone to Edge and measures actual received audio and final transcript. Mode C does not establish human microphone behavior.

The browser suite uses a separate temporary database, a locally negotiated real WebRTC connection and a fixture worker. Only the test application provides the fixture routes. Its booking and cancellation tests read the actual SQLite ledger through a test-only observer. Production imports no fixture worker or scripted transcripts.

The clean Windows install used a fresh isolated source copy, 94 locked runtime/QA packages and npm ci. The first uv hardlink attempt failed with OneDrive error 396 and left incomplete package metadata. A new venv using file copies succeeded, built the production frontend and passed all 10 HTTP and conversation smoke tests. Remote clean-clone installation and the hosted CI runner remain untested.
The real-model lookup probe accepted three row-verified cardiology slots from gemini-3.5-flash-lite. The originally configured gemini-3.5-flash returned 429. Flash-Lite is now the local and example default. The original release model remains selectable through GEMINI_MODEL. [Independent lookup trace](evidence/flash-lite.txt) · [Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing/)

For the opt-in browser conversation, generate caller clips with powershell.exe -NoProfile -File tests/make-caller.ps1. Start a separate production app with a fresh fictional ASTER_DB on port 8024 or set ASTER_LIVE_DESK to a different loopback origin. Run node frontend/tests/live-book-cancel.mjs. The caller audio is injected at getUserMedia. Recognition, model turns, function dispatch, writes, synthesized responses, transport and rendering use production components. The script refuses a nonempty register. It limits turns and repeated prompts. Production clinicians and real phone numbers do not belong in this probe.

The first hosted Windows run completed 84 tests and reached its 20-minute timeout in the same-process RTC test. The revised test uses loopback ICE addresses and bounded negotiation and teardown. The targeted local test passed in 1.92 seconds. [Original hosted run](https://github.com/puni344/aster/actions/runs/45656332719).
