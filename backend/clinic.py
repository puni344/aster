"""SQLite owns the schedule and its monotonic change journal."""

import json
import re
import sqlite3
from contextlib import closing, contextmanager
from datetime import date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Asia/Kolkata")
DOCTORS = [
    ("asha", "Dr Asha Menon", "General medicine", 20),
    ("arjun", "Dr Arjun Rao", "Cardiology", 30),
    ("meera", "Dr Meera Shah", "Dermatology", 20),
    ("kabir", "Dr Kabir Sen", "Pediatrics", 20),
    ("nisha", "Dr Nisha Iyer", "Orthopedics", 30),
    ("dev", "Dr Dev Malhotra", "ENT", 20),
]


def clinic_now():
    return datetime.now(ZONE)


def resolve_day(value):
    today = clinic_now().date()
    if not value or value.lower() == "today":
        return today
    if value.lower() == "tomorrow":
        return today + timedelta(days=1)
    return date.fromisoformat(value)


VISITS = """SELECT a.reference,a.status,a.phone,s.start,s.id AS slot_id,d.name,d.specialty
           FROM appointments a JOIN slots s ON a.slot_id=s.id JOIN doctors d ON s.doctor=d.id"""


def public(row):
    result = dict(row)
    result["phone"] = "•••• " + result["phone"][-4:]
    return result


class Clinic:
    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS doctors(id TEXT PRIMARY KEY,name TEXT,specialty TEXT,duration INTEGER);
            CREATE TABLE IF NOT EXISTS slots(id TEXT PRIMARY KEY,doctor TEXT REFERENCES doctors,start TEXT);
            CREATE TABLE IF NOT EXISTS appointments(reference TEXT PRIMARY KEY,slot_id TEXT REFERENCES slots,
                phone TEXT NOT NULL,status TEXT CHECK(status IN ('Confirmed','Cancelled')),created TEXT,cancelled TEXT);
            CREATE UNIQUE INDEX IF NOT EXISTS held_slot ON appointments(slot_id) WHERE status='Confirmed';
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, reference TEXT, status TEXT, created TEXT);
            CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, result TEXT NOT NULL);
            """)
            db.executemany("INSERT OR IGNORE INTO doctors VALUES(?,?,?,?)", DOCTORS)
            db.commit()

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @contextmanager
    def transaction(self, write=False):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db

    def seed(self, day):
        if not clinic_now().date() <= day <= clinic_now().date() + timedelta(days=30):
            return
        with self.transaction() as db:
            if db.execute(
                "SELECT 1 FROM slots WHERE start LIKE ? LIMIT 1", (f"{day}%",)
            ).fetchone():
                return
        with self.transaction(True) as db:
            for index, (doctor, _, _, _) in enumerate(DOCTORS):
                for hour in (9, 10, 11, 14, 15, 16):
                    start = datetime.combine(day, time(hour, (index % 3) * 10), ZONE)
                    db.execute(
                        "INSERT OR IGNORE INTO slots VALUES(?,?,?)",
                        (f"{doctor}-{day}-{hour}", doctor, start.isoformat()),
                    )

    def snapshot(self, day):
        self.seed(day)
        now = clinic_now().isoformat()
        with self.transaction() as db:
            doctors = [
                dict(r) for r in db.execute("SELECT * FROM doctors ORDER BY rowid")
            ]
            for doctor in doctors:
                doctor["slots"] = [
                    dict(r)
                    for r in db.execute(
                        """SELECT s.id,s.start,
                    CASE WHEN a.reference IS NOT NULL THEN 'Booked' WHEN s.start<=? THEN 'Past' ELSE 'Open' END AS status
                    FROM slots s LEFT JOIN appointments a ON a.slot_id=s.id AND a.status='Confirmed'
                    WHERE s.doctor=? AND s.start LIKE ? ORDER BY s.start""",
                        (now, doctor["id"], f"{day}%"),
                    )
                ]
            visits = [
                public(r) for r in db.execute(VISITS + " ORDER BY s.start,a.created")
            ]
            revision = db.execute("SELECT coalesce(max(id),0) FROM events").fetchone()[
                0
            ]
            return {
                "date": str(day),
                "today": str(clinic_now().date()),
                "doctors": doctors,
                "appointments": visits,
                "revision": revision,
            }

    def changes(self, after):
        with self.transaction() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM events WHERE id>? ORDER BY id LIMIT 100", (after,)
                )
            ]

    def available(self, doctor="", specialty="", date="", preferred_time=""):
        try:
            day = resolve_day(date)
        except ValueError:
            return {"error": "INVALID_DATE"}

        today = clinic_now().date()
        if day < today or day > today + timedelta(days=30):
            return {
                "error": "DATE_OUT_OF_RANGE",
                "first_date": str(today),
                "last_date": str(today + timedelta(days=30)),
            }
        if preferred_time and not re.fullmatch(
            r"(?:[01]\d|2[0-3]):[0-5]\d", preferred_time
        ):
            return {"error": "INVALID_TIME"}

        def name_key(value):
            return " ".join(
                token
                for token in re.findall(r"[a-z]+", value.casefold())
                if token not in {"doctor", "dr"}
            )

        query = name_key(doctor)

        def matches(day):
            return [
                d
                for d in self.snapshot(day)["doctors"]
                if query in name_key(d["name"])
                and specialty.strip().lower() in d["specialty"].lower()
            ]

        doctors = matches(day)
        if not doctors:
            return {"error": "DOCTOR_NOT_FOUND", "specialties": [d[2] for d in DOCTORS]}
        if doctor and len(doctors) > 1:
            return {
                "error": "AMBIGUOUS_DOCTOR",
                "choices": [d["name"] for d in doctors],
            }

        def choices(doctors):
            return [
                {"slot_id": s["id"], "start": s["start"], "doctor": d["name"]}
                for d in doctors
                for s in d["slots"]
                if s["status"] == "Open"
            ]

        slots = choices(doctors)
        if preferred_time and slots:
            selected = [s for s in slots if s["start"][11:16] == preferred_time]
            requested = time.fromisoformat(preferred_time)
            minute = requested.hour * 60 + requested.minute

            def distance(slot):
                stamp = datetime.fromisoformat(slot["start"])
                return abs(stamp.hour * 60 + stamp.minute - minute)

            return {
                "slots": selected[:3],
                "alternatives": [] if selected else sorted(slots, key=distance)[:3],
            }
        return {
            "slots": slots[:3],
            "alternatives": []
            if slots
            else choices(matches(max(day, clinic_now().date()) + timedelta(days=1)))[
                :3
            ],
        }

    def receipt(self, reference, phone):
        with self.transaction() as db:
            row = db.execute(
                VISITS + " WHERE a.reference=? AND a.phone=?", (reference, phone)
            ).fetchone()
            return public(row) if row else None

    def owned(self, phone):
        with self.transaction() as db:
            return [
                public(r)
                for r in db.execute(
                    VISITS
                    + " WHERE a.phone=? AND a.status='Confirmed' AND s.start>? ORDER BY s.start",
                    (phone, clinic_now().isoformat()),
                )
            ]

    def mutate(
        self,
        action,
        target,
        phone,
        request,
        *,
        reference=None,
        source=None,
        additional=False,
    ):
        with self.transaction(True) as db:
            now = clinic_now().isoformat()
            previous = db.execute(
                "SELECT result FROM requests WHERE id=?", (request,)
            ).fetchone()
            if previous:
                return json.loads(previous[0])
            previous_start = None
            if action in {"book", "move"}:
                slot = db.execute(
                    "SELECT * FROM slots WHERE id=? AND start>?", (target, now)
                ).fetchone()
                if not slot:
                    return {"error": "SLOT_UNAVAILABLE"}
                taken = db.execute(
                    "SELECT reference,phone FROM appointments WHERE slot_id=? AND status='Confirmed'",
                    (target,),
                ).fetchone()
                if action == "move":
                    ref = reference
                    visit = db.execute(
                        VISITS
                        + " WHERE a.reference=? AND a.phone=? AND a.status='Confirmed' AND s.start>?",
                        (ref, phone, now),
                    ).fetchone()
                    if not visit:
                        return {"error": "APPOINTMENT_NOT_FOUND"}
                    changed = visit["slot_id"] != target
                    if changed and visit["slot_id"] != source:
                        return {
                            "error": "APPOINTMENT_CHANGED",
                            "instruction": "Look up the current visit and confirm which time to move.",
                        }
                    if taken and taken["reference"] != ref:
                        return {"error": "SLOT_UNAVAILABLE"}
                    if changed:
                        previous_start = visit["start"]
                        db.execute(
                            "UPDATE appointments SET slot_id=? WHERE reference=?",
                            (target, ref),
                        )
                else:
                    if taken and taken["phone"] != phone:
                        return {"error": "SLOT_UNAVAILABLE"}
                    if not taken and not additional:
                        existing = db.execute(
                            VISITS
                            + " WHERE a.phone=? AND a.status='Confirmed' AND s.doctor=? AND substr(s.start,1,10)=?",
                            (phone, slot["doctor"], slot["start"][:10]),
                        ).fetchall()
                        if existing:
                            return {
                                "error": "EXISTING_VISIT",
                                "choices": [public(v) for v in existing],
                                "instruction": "If moving the existing visit use reschedule_appointment. For a separate visit ask the caller to say they want an additional appointment.",
                            }
                    ref = (
                        taken["reference"] if taken else "AS-" + uuid4().hex[:8].upper()
                    )
                    changed = not taken
                    if changed:
                        db.execute(
                            "INSERT INTO appointments VALUES(?,?,?,'Confirmed',?,NULL)",
                            (ref, target, phone, now),
                        )
            elif action == "cancel":
                ref = target
                changed = db.execute(
                    """UPDATE appointments SET status='Cancelled',cancelled=? WHERE reference=? AND phone=?
                       AND status='Confirmed' AND (? IS NULL OR slot_id=?) AND slot_id IN (SELECT id FROM slots WHERE start>?)""",
                    (now, ref, phone, source, source, now),
                ).rowcount
                if not changed:
                    return {"error": "APPOINTMENT_NOT_FOUND"}
            else:
                raise ValueError("Unknown appointment action")
            receipt = public(
                db.execute(VISITS + " WHERE a.reference=?", (ref,)).fetchone()
            )
            if previous_start:
                receipt["previous_start"] = previous_start
            if changed:
                db.execute(
                    "INSERT INTO events(reference,status,created) VALUES(?,?,?)",
                    (ref, "Rescheduled" if previous_start else receipt["status"], now),
                )
            result = {"receipt": receipt}
            db.execute(
                "INSERT INTO requests VALUES(?,?)", (request, json.dumps(result))
            )
        return result
