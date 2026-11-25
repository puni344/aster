import {
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { createRoot } from "react-dom/client";
import {
  Asterisk,
  CalendarDays,
  CalendarCheck2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  LayoutDashboard,
  Phone,
  Stethoscope,
  Clock3,
} from "lucide-react";
const Call = lazy(() => import("./Call").then((m) => ({ default: m.Call })));
import { clinicDay, dateLabel, shift, time, type Snapshot } from "./data";
import "./style.css";

const pages = ["Reception", "Doctors", "Appointments"] as const;
const icons = [LayoutDashboard, Stethoscope, CalendarCheck2];
function App() {
  const [page, setPage] = useState<(typeof pages)[number]>("Reception"),
    [day, setDay] = useState(() => clinicDay());
  const [state, setState] = useState<Snapshot>(),
    [filter, setFilter] = useState("All specialties"),
    [call, setCall] = useState(false);
  const [error, setError] = useState(""),
    [online, setOnline] = useState(false),
    [highlight, setHighlight] = useState({ reference: "", id: 0 });
  const request = useRef(0),
    first = useRef(true),
    revision = useRef(0);
  const refresh = useCallback(async () => {
    const id = ++request.current;
    try {
      const r = await fetch("/api/dashboard?day=" + day);
      if (!r.ok) throw Error();
      const data: Snapshot = await r.json();
      if (id !== request.current) return;
      if (first.current) {
        first.current = false;
        if (
          data.today === day &&
          !data.doctors.some((d) => d.slots.some((s) => s.status === "Open"))
        ) {
          setDay(shift(day, 1));
          return;
        }
      }
      revision.current = data.revision;
      setState(data);
      setError("");
    } catch {
      if (id === request.current)
        setError("The clinic schedule could not be loaded.");
    }
  }, [day]);
  useEffect(() => {
    void refresh();
    return () => {
      request.current++;
    };
  }, [refresh]);
  useEffect(() => {
    const stream = new EventSource("/api/events?after=" + revision.current);
    stream.onopen = () => {
      setOnline(true);
      void refresh();
    };
    stream.onerror = () => setOnline(false);
    stream.onmessage = (e) => {
      const change = JSON.parse(e.data);
      if (change.id <= revision.current) return;
      setHighlight({ reference: change.reference, id: change.id });
      void refresh();
    };
    const focus = () => void refresh();
    window.addEventListener("focus", focus);
    const clock = setInterval(focus, 60000);
    return () => {
      stream.close();
      clearInterval(clock);
      window.removeEventListener("focus", focus);
    };
  }, [refresh]);
  const doctors = state?.doctors ?? [],
    visits = state?.appointments ?? [],
    shown = doctors.filter(
      (d) => filter === "All specialties" || d.specialty === filter,
    );
  const register =
    page === "Reception"
      ? visits.filter(
          (v) => v.start.startsWith(day) && v.status === "Confirmed",
        )
      : visits;
  const open = doctors.reduce(
    (n, d) => n + d.slots.filter((s) => s.status === "Open").length,
    0,
  );
  const booked = visits.filter(
    (v) => v.start.startsWith(day) && v.status === "Confirmed",
  ).length;
  const schedule = (
    <section className="paper schedule">
      <div className="sectionHead">
        <div>
          <h2>Doctor availability</h2>
        </div>
        <select
          aria-label="Filter by specialty"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option>All specialties</option>
          {doctors.map((d) => (
            <option key={d.id}>{d.specialty}</option>
          ))}
        </select>
      </div>
      <div className="daybar">
        <CalendarDays size={16} />
        <strong>{dateLabel(day, true)}</strong>
        <div className="dateButtons">
          <button
            aria-label="Previous date"
            disabled={day <= clinicDay()}
            onClick={() => setDay(shift(day, -1))}
          >
            <ChevronLeft />
          </button>
          <button
            aria-label="Next date"
            disabled={day >= shift(clinicDay(), 30)}
            onClick={() => setDay(shift(day, 1))}
          >
            <ChevronRight />
          </button>
        </div>
      </div>
      <div className="roster">
        {shown.map((d, i) => (
          <div className="doctor" key={d.id}>
            <div className={"initials tint" + (i % 3)}>
              {d.name
                .split(" ")
                .slice(1)
                .map((n) => n[0])
                .join("")}
            </div>
            <div className="doctorInfo">
              <strong>{d.name}</strong>
              <small>{d.specialty}</small>
            </div>
            <div className="slotArea">
              <div className="slots">
                {d.slots.map((s) => (
                  <span
                    title={s.status}
                    aria-label={time(s.start) + " " + s.status}
                    className={s.status.toLowerCase()}
                    key={s.id}
                  >
                    {time(s.start)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="legend">
        <i /> Open <i className="reserved" /> Booked <i className="off" />{" "}
        Elapsed <span>All times IST</span>
      </div>
    </section>
  );
  const appointments = (
    <section className="paper register">
      <div className="sectionHead">
        <div>
          <h2>{page === "Reception" ? "Scheduled visits" : "Appointments"}</h2>
        </div>
        <span className="count">
          {register.filter((v) => v.status === "Confirmed").length} active
        </span>
      </div>
      {!register.length ? (
        <div className="empty">
          <ClipboardList size={26} />
          <div>
            <strong>No appointments yet</strong>
            <small>
              {page === "Reception"
                ? dateLabel(day, true)
                : "The clinic register is empty."}
            </small>
          </div>
        </div>
      ) : (
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                {[
                  "Doctor",
                  "Scheduled for",
                  "Caller",
                  "Reference",
                  "Status",
                ].map((v) => (
                  <th key={v}>{v}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {register.map((v) => (
                <tr
                  key={
                    v.reference === highlight.reference
                      ? v.reference + highlight.id
                      : v.reference
                  }
                  className={
                    v.reference === highlight.reference ? "changed" : ""
                  }
                >
                  <td>{v.name}</td>
                  <td>
                    {dateLabel(v.start)} · {time(v.start)}
                  </td>
                  <td>{v.phone}</td>
                  <td>{v.reference}</td>
                  <td className={"visitStatus " + v.status}>{v.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
  return (
    <div className={"shell" + (call ? " calling" : "")}>
      <aside className="rail">
        <div className="brand">
          <Asterisk strokeWidth={2.3} />
          aster
        </div>
        <nav aria-label="Workspace">
          {pages.map((p, i) => {
            const Icon = icons[i];
            return (
              <button
                key={p}
                aria-current={p === page ? "page" : undefined}
                onClick={() => setPage(p)}
              >
                <Icon size={18} />
                {p}
              </button>
            );
          })}
        </nav>
        <div className="railEnd">
          <span className="clinicMark">AC</span>
          <div>
            Aster Clinic<small>Demo environment</small>
          </div>
        </div>
      </aside>
      <main>
        <div className="clinicLine">
          <strong>Aster Clinic</strong>
          <span className="sync">
            <i className={online && !error ? "connected" : ""} />
            {error ? "Refresh needed" : online ? "Synced" : "Reconnecting"}
          </span>
        </div>
        <header className="pageHead">
          <div>
            <div className="clinicDate">
              {dateLabel(clinicDay(), true)} · {clinicDay().slice(0, 4)}
            </div>
            <h1>
              {page === "Reception"
                ? "Reception desk"
                : page === "Doctors"
                  ? "Doctor schedule"
                  : "Appointment register"}
            </h1>
          </div>
          <button
            className="primary"
            disabled={call}
            onClick={() => setCall(true)}
          >
            <Phone size={16} />
            {call ? "Companion open" : "Try call"}
          </button>
        </header>
        {error && (
          <div role="alert" className="error">
            {error} <button onClick={() => void refresh()}>Retry</button>
          </div>
        )}
        {state?.date !== day ? (
          !error && <p aria-live="polite">Loading clinic schedule…</p>
        ) : (
          <>
            {page === "Reception" && (
              <>
                <section
                  className="metrics"
                  aria-label={"Schedule summary for " + day}
                >
                  {[
                    [Stethoscope, doctors.length, "Doctors on roster"],
                    [Clock3, open, "Open slots"],
                    [CalendarCheck2, booked, "Booked visits"],
                  ].map(([I, n, label]) => {
                    const Icon = I as typeof Phone;
                    return (
                      <div key={String(label)}>
                        <span>
                          <Icon size={15} />
                          {String(label)}
                        </span>
                        <strong>{String(n)}</strong>
                      </div>
                    );
                  })}
                  <small>
                    {dateLabel(day)}
                    <br />
                    Schedule
                  </small>
                </section>
                <div className="worklist">
                  {schedule}
                  {appointments}
                </div>
              </>
            )}
            {page === "Doctors" && schedule}
            {page === "Appointments" && appointments}
          </>
        )}
      </main>
      {call && (
        <Suspense fallback={<p role="status">Opening companion…</p>}>
          <Call close={() => setCall(false)} committed={(receipt) => {
            const scheduledDay=receipt.start.slice(0,10);
            if (scheduledDay!==day) setDay(scheduledDay);
            else void refresh();
          }} />
        </Suspense>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
