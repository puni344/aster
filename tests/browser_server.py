"""Loopback-only Playwright fixture. Never import this module in the application."""

import os
import tempfile
from contextlib import asynccontextmanager
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
        result = state.invoke("book_appointment", {"slot_id": slot["slot_id"]}, "book")
    elif operation == "cancel":
        question = state.invoke("cancel_appointment", {}, "lookup-cancel")
        state.assistant(question["question"])
        state.user("yes")
        result = state.invoke("cancel_appointment", {}, "cancel")
    else:
        return {}
    await worker.rtvi.send_server_message(
        {"type": "assistant-final", "text": "Fixture transcript", "interrupted": False}
    )
    await worker.rtvi.send_server_message({"type": "tool-end", **result})
    return result


app.mount("/", main.app)
