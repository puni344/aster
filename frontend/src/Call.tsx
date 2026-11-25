import { useEffect, useRef, useState } from "react";
import { Headset, Mic, MicOff, PhoneOff, X, TicketCheck } from "lucide-react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import { acceptReceipt, dateLabel, time, type CallEvent, type Visit } from "./data";

interface Line {
  id: number;
  who: string;
  text: string;
  interrupted?: boolean;
}
export function Call({
  close,
  committed,
}: {
  close: () => void;
  committed: (receipt: Visit) => void;
}) {
  const [status, setStatus] = useState("Preparing call"),
    [error, setError] = useState(""),
    [muted, setMuted] = useState(false);
  const [lines, setLines] = useState<Line[]>([]),
    [partial, setPartial] = useState(""),
    [botDraft, setBotDraft] = useState("");
  const [receipts, setReceipts] = useState<Visit[]>([]),
    [identity, setIdentity] = useState("Caller");
  const [since, setSince] = useState(0),
    [elapsed, setElapsed] = useState(0),
    [retry, setRetry] = useState(0),
    [blocked, setBlocked] = useState(false);
  const audio = useRef<HTMLAudioElement>(null),
    client = useRef<PipecatClient | null>(null),
    wave = useRef<HTMLCanvasElement>(null);
  const feed = useRef<HTMLDivElement>(null),
    stick = useRef(true),
    dialog = useRef<HTMLElement>(null);
  const stop = useRef<() => Promise<void>>(async () => {}),
    ending = useRef(false);
  const notify = useRef(committed);
  notify.current = committed;
  useEffect(() => {
    const before = document.activeElement as HTMLElement;
    dialog.current?.focus();
    return () => before?.focus();
  }, []);
  useEffect(() => {
    if (!since) return;
    const i = setInterval(
      () => setElapsed(Math.floor((Date.now() - since) / 1000)),
      500,
    );
    return () => clearInterval(i);
  }, [since]);
  useEffect(() => {
    if (stick.current && feed.current)
      feed.current.scrollTop = feed.current.scrollHeight;
  }, [lines, partial, botDraft, receipts]);
  useEffect(() => {
    let alive = true,
      seq = 0,
      pc: PipecatClient | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const seen = new Set<string>();
    const finalTurns = new Set<string>();
    const receiptRevisions = new Map<string, number>();
    const controller = new AbortController();
    const ok = () => alive && !ending.current;
    const release = async () => {
      clearTimeout(timer);
      controller.abort();
      if (audio.current) audio.current.srcObject = null;
      if (pc) {
        const old = pc;
        pc = undefined;
        client.current = null;
        await old.disconnect().catch(() => {});
      }
    };
    stop.current = async () => {
      ending.current = true;
      setStatus("Ending");
      await release();
      if (alive) {
        setSince(0);
        setStatus("Ended");
      }
    };
    const fail = (reason: string) => {
      if (ok()) {
        ending.current = true;
        setError(reason);
        setSince(0);
        setStatus("Call unavailable");
        void release();
      }
    };
    const levels = Array<number>(48).fill(0);
    const level = (n: number) => {
      const canvas = wave.current;
      if (!ok() || !canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      levels.shift();
      levels.push(Math.min(1, Math.max(0, n)));
      ctx.clearRect(0, 0, 144, 24);
      ctx.fillStyle = "#446f50";
      const reduced = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
      if (reduced) {
        ctx.fillRect(0, 10, 144 * levels[47], 4);
        return;
      }
      levels.forEach((v, i) => {
        const h = Math.max(1, Math.sqrt(v) * 23);
        ctx.fillRect(i * 3, (24 - h) / 2, 2, h);
      });
    };
    const start = async () => {
      ending.current = false;
      setError("");
      setMuted(false);
      setLines([]);
      setReceipts([]);
      setPartial("");
      setBotDraft("");
      setIdentity("Caller");
      setElapsed(0);
      setBlocked(false);
      setStatus("Preparing call");
      try {
        timer = setTimeout(() => fail("Call setup timed out. Check microphone access and try again."), 35000);
        const res = await fetch("/api/dashboard", { signal: controller.signal });
        if (!res.ok) throw Error("Clinic service is unavailable.");
        const missing = (await res.json()).missing as string[];
        if (!ok()) return;
        if (missing.length)
          throw Error(
            "Configure " +
              missing.join(" and ") +
              " in the backend .env and restart the clinic server.",
          );
        if (!navigator.mediaDevices?.getUserMedia)
          throw Error(
            "Open the clinic on localhost or HTTPS to use a microphone.",
          );
        setStatus("Requesting microphone");
        const permission = await navigator.permissions
          ?.query({ name: "microphone" as PermissionName })
          .catch(() => undefined);
        if (!ok()) return;
        if (permission?.state === "denied")
          throw Error("Microphone permission denied.");
        pc = new PipecatClient({
          transport: new SmallWebRTCTransport({
            iceServers: [],
            waitForICEGathering: true,
          }),
          enableMic: true,
          enableCam: false,
          callbacks: {
            onMediaStateChanged: (s) => {
              if (s.mic.state === "error")
                fail(
                  s.mic.reason === "blocked"
                    ? "Microphone permission was denied. Allow microphone access and retry."
                    : "Microphone unavailable. Check your input device and retry.",
                );
            },
            onBotReady: () => {
              if (ok()) {
                clearTimeout(timer);
                setSince(Date.now());
                setStatus("Listening");
              }
            },
            onDisconnected: () => {
              if (ok())
                fail("The connection closed. Start a new call to reconnect.");
            },
            onError: () =>
              fail(
                "The call connection failed. Start a new call to reconnect.",
              ),
            onTrackStarted: (track, p) => {
              if (
                ok() &&
                !p?.local &&
                track.kind === "audio" &&
                audio.current
              ) {
                audio.current.srcObject = new MediaStream([track]);
                audio.current.play().catch(() => { if (ok()) setBlocked(true); });
              }
            },
            onLocalAudioLevel: level,
            onRemoteAudioLevel: level,
            onBotStartedSpeaking: () => {
              if (ok()) setStatus("Receptionist speaking");
            },
            onBotStoppedSpeaking: () => {
              if (ok()) setStatus("Listening");
            },
            onUserInput: (d) => {
              if (!ok()) return;
              if (!d.final) {
                if (!finalTurns.has(d.timestamp)) setPartial(d.text);
                return;
              }
              if (!d.text.trim()) return;
              finalTurns.add(d.timestamp);
              setPartial("");
              const key = d.timestamp + d.text;
              if (!seen.has(key)) {
                seen.add(key);
                const line = { id: ++seq, who: "Caller", text: d.text };
                setLines((old) => [...old, line]);
              }
            },
            onBotOutput: (d) => {
              if (ok() && d.text)
                setBotDraft(d.spoken_progress?.accumulated_text || d.text);
            },
            onServerMessage: (d: CallEvent) => {
              if (!ok()) return;
              if (d.type === "provider-error")
                fail(
                  d.reason === "quota"
                    ? (d.provider ?? "Voice service") +
                        " reached its usage limit. Start a new call when quota is available."
                    : d.reason === "credentials"
                      ? (d.provider ?? "Voice service") +
                        " rejected its credentials. Check the backend configuration."
                      : "A voice provider stopped responding. Try again when service is available.",
                );
              if (d.type === "identity") setIdentity(d.masked || "Caller");
              if (d.type === "assistant-final") {
                const line = {
                  id: ++seq,
                  who: "Aster",
                  text: d.text,
                  interrupted: d.interrupted,
                };
                setBotDraft("");
                setLines((old) => [...old, line]);
              }
              if (d.type === "tool-start")
                setStatus("Checking appointment desk");
              if (d.type === "tool-end") {
                setStatus("Listening");
                const receipt = d.receipt;
                if (receipt) {
                  if (!acceptReceipt(receiptRevisions, receipt)) return;
                  setReceipts((old) => [
                    ...old.filter((v) => v.reference !== receipt.reference),
                    receipt,
                  ]);
                  notify.current(receipt);
                }
              }
            },
          },
        });
        client.current = pc;
        const connecting = pc;
        await connecting.initDevices();
        if (!ok()) {
          await connecting.disconnect();
          return;
        }
        setStatus("Connecting");
        clearTimeout(timer);
        timer = setTimeout(
          () =>
            fail(
              "The receptionist did not connect. Check provider access and try again.",
            ),
          35000,
        );
        await connecting.connect({
          webrtcRequestParams: {
            endpoint: new URL("/api/offer", window.location.origin).href,
          },
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        fail(
          /permission|denied|notallowed/i.test(msg)
            ? "Microphone permission was denied. Allow microphone access and retry."
            : /notfound|device not found/i.test(msg)
              ? "No microphone was found. Connect one and retry."
              : msg,
        );
      }
    };
    void start();
    return () => {
      alive = false;
      void release();
    };
  }, [retry]);
  useEffect(() => {
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [close]);
  const done = !!error || status === "Ended";
  return (
    <aside
      className="companion"
      role="dialog"
      aria-label="Live call companion"
      tabIndex={-1}
      ref={dialog}
    >
      <header>
        <span>
          <Headset size={18} /> Call companion
        </span>
        <button aria-label="Close call companion" onClick={close}>
          <X size={18} />
        </button>
      </header>
      <div className="callIdentity">
        <h2>Aster Reception</h2>
        <p role="status">
          {status}{" "}
          {since
            ? " · " +
              Math.floor(elapsed / 60) +
              ":" +
              String(elapsed % 60).padStart(2, "0")
            : ""}
        </p>
        {since > 0 && (
          <>
            <small>{identity}</small>
            <canvas
              aria-label="Live audio amplitude"
              role="img"
              width="144"
              height="24"
              ref={wave}
            />
          </>
        )}
      </div>
      <div
        className="transcript"
        ref={feed}
        onScroll={() => {
          const f = feed.current;
          if (f)
            stick.current = f.scrollHeight - f.scrollTop - f.clientHeight < 40;
        }}
      >
        {(!error || lines.length > 0) && <h3>Live transcript</h3>}
        {!error && !lines.length && !partial && !botDraft && (
          <p className="hint">
            Conversation will appear here when the call connects.
          </p>
        )}
        {lines.map((l) => (
          <p
            key={l.id}
            className={l.who === "Caller" ? "callerLine" : "agentLine"}
          >
            <b>{l.who}</b>
            {l.text}
            {l.interrupted && <em>Interrupted</em>}
          </p>
        ))}
        {partial && (
          <p className="callerLine draft">
            <b>Caller</b>
            {partial}
          </p>
        )}
        {botDraft && (
          <p className="agentLine draft">
            <b>Aster</b>
            {botDraft}
          </p>
        )}
        {error && (
          <div className="callError" role="alert">
            <h3>
              {error.includes(".env")
                ? "Voice setup required"
                : "Call could not continue"}
            </h3>
            <p>{error}</p>
          </div>
        )}
      </div>
      {receipts.length > 0 && (
        <section className="outcomes" aria-label="Appointment receipts">
          {receipts.map((v) => (
            <article className="receipt" key={v.reference + v.status}>
              <TicketCheck size={20} />
              <b>{v.previous_start ? "Rescheduled" : v.status}</b>
              <strong>{v.name}</strong>
              <span>{v.specialty}</span>
              {v.previous_start && (
                <small>
                  Previously {dateLabel(v.previous_start)} at{" "}
                  {time(v.previous_start)}
                </small>
              )}
              <strong>{dateLabel(v.start)} · {time(v.start)} IST
              </strong>
              <small>{v.reference}</small>
            </article>
          ))}
        </section>
      )}
      <audio ref={audio} autoPlay />
      {blocked && (
        <button
          onClick={() => audio.current?.play().then(() => setBlocked(false))}
        >
          Enable speaker
        </button>
      )}
      <footer>
        {done ? (
          <button className="primary" onClick={() => setRetry((n) => n + 1)}>
            {error ? "Start a new call" : "Call again"}
          </button>
        ) : (
          <>
            <button
              disabled={!since}
              aria-pressed={muted}
              onClick={() => {
                client.current?.enableMic(muted);
                setMuted(!muted);
              }}
            >
              {muted ? <MicOff size={16} /> : <Mic size={16} />}{" "}
              {muted ? "Unmute" : "Mute"}
            </button>
            <button className="hangup" onClick={() => void stop.current()}>
              <PhoneOff size={16} /> End call
            </button>
          </>
        )}
      </footer>
    </aside>
  );
}
