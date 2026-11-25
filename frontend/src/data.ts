export interface Visit {
  reference: string;
  status: "Confirmed" | "Cancelled";
  phone: string;
  start: string;
  name: string;
  specialty: string;
}
export type CallEvent =
  | { type: "tool-start" }
  | { type: "tool-end"; receipt?: Visit | null }
  | { type: "assistant-final"; text: string; interrupted: boolean }
  | { type: "identity"; masked: string | null }
  | {
      type: "provider-error";
      reason?: "quota" | "credentials" | "unavailable";
    };

export interface Doctor {
  id: string;
  name: string;
  specialty: string;
  duration: number;
  slots: { id: string; start: string; status: string }[];
}
export interface Snapshot {
  date: string;
  today: string;
  revision: number;
  missing: string[];
  appointments: Visit[];
  doctors: Doctor[];
}
export const time = (value: string) =>
  new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
export const dateLabel = (value: string, full = false) =>
  new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    weekday: full ? "long" : undefined,
    day: "numeric",
    month: full ? "long" : "short",
  }).format(new Date(value.length === 10 ? value + "T12:00:00+05:30" : value));
export function shift(value: string, days: number) {
  const d = new Date(value + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
export function clinicDay() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}
