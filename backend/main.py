import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel, Field

from .clinic import Clinic, clinic_now

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
logger.remove()
logger.add(sys.stderr, level="WARNING", diagnose=False, backtrace=False)


def missing():
    return [
        key for key in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY") if not os.getenv(key)
    ]


@asynccontextmanager
async def lifespan(app):
    app.state.clinic = Clinic(os.getenv("ASTER_DB", str(ROOT / "aster.sqlite")))
    app.state.handler = None
    app.state.calls = set()
    yield
    if app.state.handler:
        await app.state.handler.close()
    tasks = list(app.state.calls)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Aster Reception", lifespan=lifespan)


@app.get("/api/dashboard")
def dashboard(day: date | None = None):
    return {
        **app.state.clinic.snapshot(day or clinic_now().date()),
        "missing": missing(),
    }


@app.get("/api/events")
async def events(
    request: Request, after: int = Query(default=0, ge=0, le=9223372036854775807)
):
    async def stream():
        last = request.headers.get("last-event-id", "")
        cursor = max(after, int(last) if last.isdigit() and len(last) < 19 else 0, 0)
        while not await request.is_disconnected():
            rows = await asyncio.to_thread(app.state.clinic.changes, cursor)
            for row in rows:
                cursor = row["id"]
                yield f"id: {cursor}\ndata: {json.dumps(row)}\n\n"
            if not rows:
                yield ": heartbeat\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


class Offer(BaseModel):
    sdp: str = Field(min_length=1, max_length=128000)
    type: str = Field(pattern="^offer$")
    pc_id: str | None = None
    restart_pc: bool = False


@app.post("/api/offer")
async def offer(body: Offer):
    if missing():
        raise HTTPException(503, "Voice configuration missing: " + ", ".join(missing()))
    from pipecat.transports.smallwebrtc.request_handler import (
        SmallWebRTCRequest,
        SmallWebRTCRequestHandler,
    )

    from .voice import build_call

    if not app.state.handler:
        app.state.handler = SmallWebRTCRequestHandler(ice_servers=[])

    async def start(peer):
        async def run():
            try:
                await build_call(peer, app.state.clinic)
            finally:
                await peer.disconnect()

        task = asyncio.create_task(run())
        app.state.calls.add(task)
        task.add_done_callback(app.state.calls.discard)

    return await app.state.handler.handle_web_request(
        SmallWebRTCRequest(**body.model_dump()), start
    )


class Candidate(BaseModel):
    candidate: str = Field(max_length=4096)
    sdp_mid: str = Field(max_length=128)
    sdp_mline_index: int = Field(ge=0, le=128)


class Candidates(BaseModel):
    pc_id: str
    candidates: list[Candidate] = Field(max_length=128)


@app.patch("/api/offer")
async def patch(body: Candidates):
    from pipecat.transports.smallwebrtc.request_handler import (
        IceCandidate,
        SmallWebRTCPatchRequest,
    )

    if not app.state.handler:
        raise HTTPException(404, "Call ended")
    await app.state.handler.handle_patch_request(
        SmallWebRTCPatchRequest(
            body.pc_id, [IceCandidate(**c.model_dump()) for c in body.candidates]
        )
    )
    return {"ok": True}


if (ROOT / "frontend/dist").is_dir():
    app.mount(
        "/", StaticFiles(directory=ROOT / "frontend/dist", html=True), name="dashboard"
    )
