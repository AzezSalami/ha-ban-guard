// Pure formatting helpers (unit tested).

/** Regional-indicator flag emoji for an ISO 3166-1 alpha-2 code. */
export function flag(country: string | null | undefined): string {
  if (!country || !/^[A-Za-z]{2}$/.test(country)) return "";
  const base = 0x1f1e6;
  const upper = country.toUpperCase();
  return String.fromCodePoint(
    base + upper.charCodeAt(0) - 65,
    base + upper.charCodeAt(1) - 65,
  );
}

export interface Countdown {
  expired: boolean;
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
}

export function countdown(expiresAt: string | null, now: number): Countdown | null {
  if (!expiresAt) return null;
  const ms = Date.parse(expiresAt) - now;
  if (Number.isNaN(ms)) return null;
  if (ms <= 0) return { expired: true, days: 0, hours: 0, minutes: 0, seconds: 0 };
  const total = Math.floor(ms / 1000);
  return {
    expired: false,
    days: Math.floor(total / 86400),
    hours: Math.floor((total % 86400) / 3600),
    minutes: Math.floor((total % 3600) / 60),
    seconds: total % 60,
  };
}

/** Compact "2d 4h", "3h 12m", "4m 05s". */
export function formatCountdown(c: Countdown): string {
  if (c.days > 0) return `${c.days}d ${c.hours}h`;
  if (c.hours > 0) return `${c.hours}h ${String(c.minutes).padStart(2, "0")}m`;
  return `${c.minutes}m ${String(c.seconds).padStart(2, "0")}s`;
}

export function formatDateTime(iso: string | null, language: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(language, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

/** Bar heights (0..1) for a series, using a "nice" rounded maximum. */
export function scaleBars(values: number[]): { ratios: number[]; max: number } {
  const peak = Math.max(0, ...values);
  const max = niceCeil(peak);
  return { ratios: values.map((v) => (max === 0 ? 0 : v / max)), max };
}

export function niceCeil(value: number): number {
  if (value <= 0) return 0;
  const exponent = Math.floor(Math.log10(value));
  const base = 10 ** exponent;
  for (const step of [1, 2, 2.5, 5, 10]) {
    if (value <= step * base) return step * base;
  }
  return 10 * base;
}

/** Compact time since an ISO timestamp: "45s", "12m", "3h 05m", "2d 4h". */
export function formatElapsed(fromIso: string, now: number): string {
  const ms = now - Date.parse(fromIso);
  if (Number.isNaN(ms)) return "";
  const total = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, "0")}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${total}s`;
}

export function downloadName(prefix: string, now: Date): string {
  const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-");
  return `${prefix}-${stamp}.json`;
}
