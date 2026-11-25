"""Construct the production graph without starting any provider sockets."""

import asyncio

from backend.clinic import Clinic


def test_production_graph(tmp_path, monkeypatch):
    from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection

    from backend.voice import build_call

    monkeypatch.setenv("ELEVENLABS_API_KEY", "unused-construction-test")
    monkeypatch.setenv("GEMINI_API_KEY", "unused-construction-test")

    async def check():
        peer = SmallWebRTCConnection(ice_servers=[])
        run = build_call(peer, Clinic(tmp_path / "voice.sqlite"))
        run.close()
        await peer.disconnect()

    asyncio.run(check())


def test_smallwebrtc_offer_and_audio():
    from aiortc import (
        AudioStreamTrack,
        RTCConfiguration,
        RTCPeerConnection,
        RTCSessionDescription,
    )
    from pipecat.transports.smallwebrtc.request_handler import (
        SmallWebRTCRequest,
        SmallWebRTCRequestHandler,
    )

    async def check():
        browser = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        handler = SmallWebRTCRequestHandler(ice_servers=[])
        received = asyncio.Event()
        peers = []

        async def attached(peer):
            peers.append(peer)

            @peer.event_handler("connected")
            async def connected(peer):
                received.set()

            await peer.connect()

        try:
            browser.addTrack(AudioStreamTrack())
            browser.addTransceiver("video", direction="recvonly")
            browser.createDataChannel("chat")
            await browser.setLocalDescription(await browser.createOffer())
            answer = await handler.handle_web_request(
                SmallWebRTCRequest(browser.localDescription.sdp, "offer"), attached
            )
            await browser.setRemoteDescription(
                RTCSessionDescription(sdp=answer["sdp"], type="answer")
            )
            await asyncio.wait_for(received.wait(), 12)
            frame = await asyncio.wait_for(peers[0].audio_input_track().recv(), 5)
            assert frame.samples > 0
        finally:
            await browser.close()
            await handler.close()

    asyncio.run(check())


def test_identity_processor_accepts_only_committed_stt(tmp_path):
    from unittest.mock import AsyncMock

    from pipecat.frames.frames import InterimTranscriptionFrame, TranscriptionFrame
    from pipecat.processors.frame_processor import FrameDirection

    from backend.session import Conversation
    from backend.voice import SpokenIdentity

    async def check():
        state = Conversation(Clinic(tmp_path / "identity.sqlite"))
        notify = AsyncMock()
        tap = SpokenIdentity(state, notify)
        tap.push_frame = AsyncMock()

        async def send(frame):
            await tap.process_frame(frame, FrameDirection.DOWNSTREAM)

        await send(InterimTranscriptionFrame("9876543210", "caller", "ts"))
        assert state.pending is None
        await send(TranscriptionFrame("9876543210", "caller", "ts", finalized=True))
        assert state.pending is None

        def committed(text):
            return TranscriptionFrame(
                text,
                "caller",
                "ts",
                result={"message_type": "committed_transcript"},
                finalized=True,
            )

        await send(committed("9876543210"))
        assert state.pending == "+919876543210"
        state.assistant("Is 9876543210 correct?")
        await send(committed("yes"))
        assert state.masked.endswith("3210")
        await send(committed("9876543210"))
        assert state.masked.endswith("3210")
        assert notify.await_count == 2

    asyncio.run(check())


def test_rtvi_reports_gemini_quota_before_generic_error():
    from unittest.mock import AsyncMock, Mock

    from pipecat.frames.frames import ErrorFrame

    from backend.voice import GoogleLLMService, ReceptionRTVI

    async def check():
        rtvi = ReceptionRTVI()
        rtvi.send_server_message = AsyncMock()
        frame = ErrorFrame(
            error="429 RESOURCE_EXHAUSTED", processor=Mock(spec=GoogleLLMService)
        )
        await rtvi._send_error_frame(frame)
        rtvi.send_server_message.assert_awaited_once_with(
            {"type": "provider-error", "provider": "Gemini", "reason": "quota"}
        )

    asyncio.run(check())
