"""Opt-in synthetic audio corpus evaluation against ElevenLabs' real-time STT endpoint."""

import asyncio
import base64
import json
import os
import re
import wave
from pathlib import Path
from time import perf_counter

import aiohttp
import numpy as np
from dotenv import load_dotenv
from websockets.asyncio.client import connect

from backend.session import number

CORPUS = Path(".tools/qa-audio")


def words(text):
    return re.findall(
        r"[a-z0-9]+", text.lower().replace("dr.", "doctor").replace("p.m.", "p m")
    )


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(
                min(previous[j] + 1, current[-1] + 1, previous[j - 1] + (left != right))
            )
        previous = current
    return previous[-1]


def pcm(path):
    with wave.open(str(path)) as wav:
        assert wav.getsampwidth() == 2 and wav.getnchannels() == 1
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
    at = np.arange(round(len(samples) * 16000 / rate)) * rate / 16000
    return (
        np.rint(np.interp(at, np.arange(len(samples)), samples)).astype("<i2").tobytes()
    )


async def main():
    load_dotenv()
    headers = {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}
    async with (
        aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as session,
        session.get(
            "https://api.elevenlabs.io/v1/user/subscription", headers=headers
        ) as response,
    ):
        if response.status != 200:
            raise SystemExit(
                f"Free allocation could not be verified (HTTP {response.status})"
            )
        quota = await response.json()
    if (
        quota.get("tier") != "free"
        or quota["character_limit"] - quota["character_count"] < 1000
    ):
        raise SystemExit("Free allocation guard stopped the audio probe")
    cases = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8-sig"))
    samples = [pcm(CORPUS / (case["id"] + ".wav")) for case in cases]
    if len(cases) > 9 or sum(map(len, samples)) > 45 * 32000:
        raise SystemExit("Corpus exceeds the short-probe limit")
    url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime&audio_format=pcm_16000&commit_strategy=manual"
    results = []
    async with connect(
        url, additional_headers=headers, open_timeout=10, close_timeout=2
    ) as ws:
        for case, data in zip(cases, samples, strict=True):
            # Stream at real time and commit explicitly. No raw provider logs.
            for offset in range(0, len(data), 6400):
                chunk = data[offset : offset + 6400]
                await ws.send(
                    json.dumps(
                        {
                            "message_type": "input_audio_chunk",
                            "audio_base_64": base64.b64encode(chunk).decode(),
                            "sample_rate": 16000,
                            "commit": False,
                        }
                    )
                )
                await asyncio.sleep(len(chunk) / 32000)
            end = perf_counter()
            await ws.send(
                json.dumps(
                    {
                        "message_type": "input_audio_chunk",
                        "audio_base_64": "",
                        "sample_rate": 16000,
                        "commit": True,
                    }
                )
            )
            async with asyncio.timeout(8):
                while True:
                    event = json.loads(await ws.recv())
                    kind = event.get("message_type", "")
                    if kind == "committed_transcript":
                        break
                    if "error" in kind or "quota" in kind:
                        raise SystemExit("STT stopped: " + kind)
            actual = event["text"]
            expected = case["reference"]
            result = {
                "id": case["id"],
                "reference": expected,
                "transcript": actual,
                "words": len(words(expected)),
                "word_edits": edit_distance(words(expected), words(actual)),
                "commit_to_final_ms": round((perf_counter() - end) * 1000),
            }
            if case["id"] in {"phone", "slow-phone", "fast-phone", "correction"}:
                expected_phone = (
                    "+919876543211" if case["id"] == "correction" else "+919876543210"
                )
                result["phone_exact"] = number(actual) == expected_phone
            results.append(result)
            print(json.dumps(result), flush=True)
    assert len(results) == len(cases)


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), 75))
