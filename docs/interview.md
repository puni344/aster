# Candidate practice

Trace a call with the implementation open. For each answer, point at a code path or run a check. These are study notes generated with AI. Personal review and demonstration should be described in your own words.

1. **Where does a call begin?** Try call mounts Call.tsx, checks server configuration, initializes PipecatClient devices and connects via the offer endpoint.
2. **Why is SDP needed?** The browser and aiortc exchange codecs, ICE information and media directions so their peer connections can negotiate media.
3. **What carries sound and what carries text?** WebRTC carries the audio tracks. The data channel carries RTVI messages. The HTTP offer and answer are signaling.
4. **What is a Pipecat frame?** A typed item passed between processors. Audio, committed transcription, TTS requests and interruption signals have different frame classes and handling.
5. **Where does VAD run?** The user aggregator owns the Silero analyzer. An end-of-speech event allows the ElevenLabs adapter to commit its current audio in manual mode.
6. **What separates interim captions from identity evidence?** SpokenIdentity checks finalized TranscriptionFrame objects with committed ElevenLabs metadata. Rendering an interim string cannot confirm a caller.
7. **Where are tools declared?** voice.py creates FunctionSchema declarations, wraps them in ToolsSchema and registers matching callbacks on GoogleLLMService.
8. **Who chooses a tool and who decides success?** Gemini requests an action. Conversation checks session state and Clinic returns a committed result or an error.
9. **How would you debug an empty availability result?** Inspect sanitized doctor/date/time inputs, clinic timezone, the rolling window, doctor normalization and actual free slots. The first live probe invoked the tool but returned no slots.
10. **Can an unrelated yes confirm a phone number?** Only a pending challenge from a matching, uninterrupted readback accepts the next clear affirmative. The challenge is consumed on the next user turn.
11. **What happens after a correction?** The confirmed number and pending cancellation are cleared. A new candidate must be fully read back and confirmed.
12. **What if two callers book the same slot?** Independent SQLite connections acquire a write transaction before checking and writing. The partial unique index enforces one active visit for the slot.
13. **How do retries behave?** A request ID scopes a stored result to its session and identity. Repeating a booking of the same held slot for the same number returns its real reference without another journal event.
14. **How does cancellation choose among visits?** Lookup uses the confirmed phone and future active visits. Several matches require selection. The selected visit gets a separate confirmation question.
15. **What if event insertion fails?** The transaction rolls back. test_rollback forces this failure and checks both the journal and caller visits.
16. **What if the original tab closes just after commit?** The event remains in SQLite. The dashboard reads the committed journal and refreshes independently of the call-local receipt.
17. **How does the browser recover missed updates?** EventSource reconnects, Last-Event-ID supports replay, and onopen refreshes a complete snapshot. A request counter prevents older responses replacing newer ones.
18. **How do you distinguish a real signal from a decorative waveform?** Audio-level callbacks supply samples to the canvas. Reduced motion renders a level bar. No speech is synthesized in the frontend.
19. **What did browser integration tests actually prove?** Synthetic microphone frames reached a real local Pipecat transport. The fixture used deterministic tool calls and emitted structured events. Provider transcription, synthetic speech playback and natural conversation require a separate live test.
20. **What would you change first for deployment?** Establish trusted identity and operator access, protect patient data, configure TLS and remote WebRTC connectivity, then load-test the database and add operational monitoring. The demo's phone-only identification is an assignment constraint.

For the later mock interview, begin with question 1, answer aloud and open the referenced file. Advance only after explaining both the data path and one way to observe a failure.
