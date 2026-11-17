// Client-side validation; the backend re-validates everything.

const IPV4_OCTET = "(25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)";
const IPV4 = new RegExp(`^${IPV4_OCTET}(\\.${IPV4_OCTET}){3}$`);
const HOSTNAME =
  /^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))*\.?$/i;

export function isIPv4(value: string): boolean {
  return IPV4.test(value);
}

export function isIPv6(value: string): boolean {
  const text = value.split("%")[0] ?? "";
  if (!/^[0-9a-f:.]+$/i.test(text) || !text.includes(":")) return false;
  if (text.includes(":::")) return false;
  if (/^:[^:]/.test(text) || /[^:]:$/.test(text)) return false;
  const doubles = text.split("::").length - 1;
  if (doubles > 1) return false;
  let groups = text.split(":");
  const last = groups[groups.length - 1] ?? "";
  let width = 8;
  if (last.includes(".")) {
    if (!isIPv4(last)) return false;
    groups = groups.slice(0, -1);
    width = 6;
  }
  if (doubles === 0) {
    return groups.length === width && groups.every((g) => /^[0-9a-f]{1,4}$/i.test(g));
  }
  const filled = groups.filter((g) => g !== "");
  return filled.length < width && filled.every((g) => /^[0-9a-f]{1,4}$/i.test(g));
}

export function isIP(value: string): boolean {
  return isIPv4(value) || isIPv6(value);
}

export function isCIDR(value: string): boolean {
  const [addr, prefix, ...rest] = value.split("/");
  if (rest.length || addr === undefined || prefix === undefined) return false;
  if (!/^\d{1,3}$/.test(prefix)) return false;
  const bits = Number(prefix);
  if (isIPv4(addr)) return bits <= 32;
  if (isIPv6(addr)) return bits <= 128;
  return false;
}

export function isIPOrCIDR(value: string): boolean {
  const text = value.trim();
  return isIP(text) || isCIDR(text);
}

export function isHostname(value: string): boolean {
  const text = value.trim();
  return HOSTNAME.test(text) && !isIP(text) && /[a-z]/i.test(text);
}

export function isAllowValue(value: string): boolean {
  return isIPOrCIDR(value) || isHostname(value);
}

/** Split pasted text (newlines, commas, spaces) into distinct entries. */
export function splitEntries(text: string): string[] {
  return [...new Set(text.split(/[\s,;]+/).map((s) => s.trim()).filter(Boolean))];
}

const DURATION = /^(\d+)\s*([smhdw])$/i;

export function isDuration(value: string): boolean {
  const text = value.trim().toLowerCase();
  if (["permanent", "perm", "forever", "never", "0"].includes(text)) return true;
  const match = DURATION.exec(text);
  return match !== null && Number(match[1]) > 0;
}
