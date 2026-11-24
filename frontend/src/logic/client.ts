// Short, human description of a session's client (unit tested).

export interface ClientInfo {
  /** "Home Assistant iOS app", "Chrome on Windows", ... */
  label: string;
  /** "app" | "browser" | "other" – picks the icon. */
  kind: "app" | "browser" | "other";
}

const APPS: [RegExp, string][] = [
  [/home-assistant\.io\/iOS/i, "Home Assistant iOS app"],
  [/home-assistant\.io\/android/i, "Home Assistant Android app"],
  [/home-assistant\.io\/macOS/i, "Home Assistant macOS app"],
];

const BROWSERS: [RegExp, string][] = [
  [/Edg(?:e|A|iOS)?\//, "Edge"],
  [/OPR\//, "Opera"],
  [/SamsungBrowser\//, "Samsung Internet"],
  [/Firefox\/|FxiOS\//, "Firefox"],
  [/Chrome\/|CriOS\//, "Chrome"],
  [/Safari\//, "Safari"],
];

const SYSTEMS: [RegExp, string][] = [
  [/iPhone|iPad|iPod/, "iOS"],
  [/Android/, "Android"],
  [/Windows/, "Windows"],
  [/Mac OS X|Macintosh/, "macOS"],
  [/CrOS/, "ChromeOS"],
  [/Linux/, "Linux"],
];

function first(table: [RegExp, string][], text: string): string | null {
  for (const [pattern, name] of table) if (pattern.test(text)) return name;
  return null;
}

export function describeClient(
  clientId: string | null | undefined,
  clientName: string | null | undefined,
  userAgent: string | null | undefined,
): ClientInfo {
  const id = clientId ?? "";
  const agent = userAgent ?? "";
  const app = first(APPS, id) ?? (/Home ?Assistant\/[\d.]+/i.test(agent) ? "Home Assistant app" : null);
  if (app) return { label: app, kind: "app" };
  const browser = first(BROWSERS, agent);
  const system = first(SYSTEMS, agent);
  if (browser) return { label: system ? `${browser} on ${system}` : browser, kind: "browser" };
  if (clientName) return { label: clientName, kind: "other" };
  if (id) {
    try {
      return { label: new URL(id).host || id, kind: "other" };
    } catch {
      return { label: id, kind: "other" };
    }
  }
  return { label: agent ? agent.slice(0, 40) : "", kind: "other" };
}
