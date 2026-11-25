# Dependency and provider research

Resolved on Windows with CPython 3.12.16, Node 24.19.0 and npm 11.17.0. The system default Python was 3.10.11. A project-local uv installation supplied the tested interpreter. Host inventory reported an i5-1235U, 12 logical processors, 16,835,268,608 bytes of RAM and about 240 GB free on C: at inspection.

| Component | Observed version or selection | Verification |
| --- | --- | --- |
| pipecat-ai | 1.17.0 with webrtc, silero, elevenlabs and google extras | Imported the real services and constructed the full graph. |
| Pipecat browser client / SmallWebRTC transport | 1.17.0 / 1.11.3 | Read installed TypeScript declarations and exercised the signaling route in Edge. |
| aiortc / ONNX Runtime | 1.16.0 / 1.32.0 | Local SDP exchange and decoded audio frame test. Constructed the Silero analyzer. |
| FastAPI / Uvicorn | 0.165.0 / 0.54.0 | Served dashboard, SSE and signaling on loopback. |
| Gemini | Google GenAI SDK 3.6.1, gemini-2.5-flash | Google accepted the key and listed the model. See live inference results in testing.md. |
| ElevenLabs | Pipecat realtime STT and streaming WebSocket TTS, eleven_flash_v2_5 | Installed adapters, signatures and graph confirmed. Account access unverified. |
| Vite | 8.3.8 | Production bundle and TypeScript check ran. Exact JS dependency tree is in package-lock.json. |

The implementation follows the framework's current worker and universal context APIs. The worker installs RTVI by default and publishes readiness after the client handshake. The aggregator emits assistant-turn text with an interruption flag. The realtime STT adapter emits a committed TranscriptionFrame with provider result metadata. The code uses manual commit at the VAD speech boundary. [Pipecat documentation index](https://docs.pipecat.ai/llms.txt) · [Framework source](https://github.com/pipecat-ai/pipecat) · [ElevenLabs STT adapter](https://docs.pipecat.ai/api-reference/server/services/stt/elevenlabs) · [ElevenLabs TTS adapter](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs)

SmallWebRTC handles peer media, its data channel and offer/answer negotiation. The browser calls initDevices, connects with webrtcRequestParams, binds the remote audio track and handles RTVI user input, bot output and server-message events. [Server transport](https://docs.pipecat.ai/api-reference/server/services/transport/small-webrtc) · [Browser client](https://github.com/pipecat-ai/pipecat-client-web) · [Browser transports](https://github.com/pipecat-ai/pipecat-client-web-transports)

Gemini generates a named tool request with structured arguments. Pipecat dispatches to a registered callback. The application supplies the result to the callback and the model can continue the turn. [Gemini adapter](https://docs.pipecat.ai/api-reference/server/services/llm/google) · [Pipecat function calling](https://docs.pipecat.ai/pipecat/learn/function-calling) · [Google function calling](https://ai.google.dev/gemini-api/docs/function-calling)

Available models, quotas and speech-service entitlements depend on the account. No paid subscription or hosted infrastructure was enabled. Free-tier access was confirmed by the user for Gemini only. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing) · [ElevenLabs API pricing](https://elevenlabs.io/pricing/api) · [ElevenLabs documentation](https://elevenlabs.io/docs/)
