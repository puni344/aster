"""Loopback-only Playwright fixture. Never import this module in the application."""

import os
import sqlite3
import tempfile
import time
from contextlib import asynccontextmanager, closing
from pathlib import Path

from fastapi import FastAPI
from pipecat.frames.frames import (
    InputAudioRawFrame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.workers.runner import WorkerRunner

from backend import main, voice
from backend.session import Conversation
from tests.consent import perform

running = {}


class Counter(FrameProcessor):
    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            running["audio"] = running.get("audio", 0) + 1
        await self.push_frame(frame, direction)


async def fixture_voice(peer, clinic):
    transport = SmallWebRTCTransport(
        peer, TransportParams(audio_in_enabled=True, audio_out_enabled=True)
    )
    worker = PipelineWorker(
        Pipeline([transport.input(), Counter(), transport.output()])
    )
    running.update(worker=worker, session=Conversation(clinic), audio=0)

    @transport.event_handler("on_client_disconnected")
    async def end(*_):
        await worker.cancel()

    try:
        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(worker)
        await runner.run()
    finally:
        running.clear()


@asynccontextmanager
async def lifespan(app):
    with tempfile.TemporaryDirectory() as folder:
        os.environ.update(
            ASTER_DB=str(Path(folder) / "test.sqlite"),
            ELEVENLABS_API_KEY="test-only",
            GEMINI_API_KEY="test-only",
        )
        voice.build_call = fixture_voice
        async with main.lifespan(main.app):
            yield


app = FastAPI(lifespan=lifespan)


@app.get("/fixture/audio")
def audio():
    return {"frames": running.get("audio", 0)}


@app.get("/fixture/ledger")
def ledger():
    with closing(sqlite3.connect(os.environ["ASTER_DB"])) as db:
        db.row_factory = sqlite3.Row
        return [
            dict(row)
            for row in db.execute(
                "SELECT reference,slot_id,status,substr(phone,-4) AS suffix FROM appointments ORDER BY created"
            )
        ]


@app.post("/fixture/{operation}")
async def event(operation: str):
    worker = running["worker"]
    state = running["session"]
    if operation in {"partial", "final"}:
        frame = (
            InterimTranscriptionFrame("Fixture partial", "test", "sentence-1")
            if operation == "partial"
            else TranscriptionFrame(
                "Fixture final", "test", "sentence-1", finalized=True
            )
        )
        await worker.queue_frame(frame)
        return {"accepted": True}
    if operation == "book":
        state.user("9876543210")
        state.assistant("Is 9876543210 correct?")
        state.user("yes")
        slot = state.invoke(
            "check_doctor_availability",
            {"doctor": "asha", "date": "tomorrow"},
            "lookup",
        )["slots"][0]
        result = perform(
            state, "book_appointment", {"slot_id": slot["slot_id"]}, "book"
        )
        running["initial_receipt"] = result["receipt"]
    elif operation == "delayed-book-result":
        await worker.rtvi.send_server_message(
            {"type": "tool-end", "receipt": running["initial_receipt"]}
        )
        await worker.rtvi.send_server_message(
            {
                "type": "assistant-final",
                "text": "End of delayed result fixture",
                "interrupted": False,
            }
        )
        return {"sent": True}
    elif operation == "move":
        state.user("Please reschedule my visit")
        slot = state.invoke(
            "check_doctor_availability",
            {"doctor": "asha", "date": "tomorrow"},
            "new-options",
        )["slots"][0]
        result = perform(
            state, "reschedule_appointment", {"slot_id": slot["slot_id"]}, "move"
        )
    elif operation == "cancel":
        state.user("Please cancel my visit")
        question = state.invoke("cancel_appointment", {}, "lookup-cancel")
        state.assistant(question["question"])
        state.user("yes")
        result = state.invoke("cancel_appointment", {}, "cancel")
    else:
        return {}
    commit_observed_ms = time.time_ns() // 1_000_000
    await worker.rtvi.send_server_message(
        {"type": "assistant-final", "text": "Fixture transcript", "interrupted": False}
    )
    await worker.rtvi.send_server_message({"type": "tool-end", **result})
    return {**result, "commit_observed_ms": commit_observed_ms}


app.mount("/", main.app)
