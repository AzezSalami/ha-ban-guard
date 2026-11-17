// Search, filter and sort for the bans table (unit tested).
import type { Ban } from "../types";

export type BanSortKey = "ip" | "created_at" | "expires_at" | "source" | "country";
export type SortDir = "asc" | "desc";
export type BanKind = "all" | "permanent" | "temporary" | "network";

export interface BanQuery {
  search: string;
  source: Ban["source"] | "all";
  kind: BanKind;
  sort: BanSortKey;
  dir: SortDir;
}

export const DEFAULT_QUERY: BanQuery = {
  search: "",
  source: "all",
  kind: "all",
  sort: "created_at",
  dir: "desc",
};

function matches(ban: Ban, needle: string): boolean {
  if (!needle) return true;
  const haystack = [ban.ip, ban.reason, ban.country ?? "", ban.city ?? "", ban.created_by ?? ""]
    .join(" ")
    .toLowerCase();
  return needle
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((term) => haystack.includes(term));
}

function kindOf(ban: Ban, kind: BanKind): boolean {
  switch (kind) {
    case "permanent":
      return ban.expires_at === null;
    case "temporary":
      return ban.expires_at !== null;
    case "network":
      return !ban.single;
    default:
      return true;
  }
}

/** Numeric sort key for IPv4/IPv6 so 10.0.0.2 sorts before 10.0.0.10. */
export function ipSortKey(ip: string): string {
  const addr = ip.split("/")[0] ?? ip;
  if (addr.includes(".") && !addr.includes(":")) {
    return "4" + addr.split(".").map((o) => o.padStart(3, "0")).join("");
  }
  const [head = "", tail = ""] = addr.split("::");
  const h = head ? head.split(":") : [];
  const t = tail ? tail.split(":") : [];
  const fill = addr.includes("::") ? Array(8 - h.length - t.length).fill("0") : [];
  return "6" + [...h, ...fill, ...t].map((g) => g.padStart(4, "0")).join("");
}

function compare(a: Ban, b: Ban, key: BanSortKey): number {
  switch (key) {
    case "ip":
      return ipSortKey(a.ip).localeCompare(ipSortKey(b.ip));
    case "expires_at": {
      // Permanent bans sort last in ascending order.
      const av = a.expires_at ? Date.parse(a.expires_at) : Number.POSITIVE_INFINITY;
      const bv = b.expires_at ? Date.parse(b.expires_at) : Number.POSITIVE_INFINITY;
      return av === bv ? 0 : av < bv ? -1 : 1;
    }
    case "created_at":
      return Date.parse(a.created_at) - Date.parse(b.created_at);
    case "country":
      if (a.country === b.country) return 0;
      if (a.country === null) return 1;
      if (b.country === null) return -1;
      return a.country.localeCompare(b.country);
    case "source":
      return a.source.localeCompare(b.source);
  }
}

export function queryBans(bans: Ban[], q: BanQuery): Ban[] {
  const filtered = bans.filter(
    (ban) =>
      matches(ban, q.search.trim()) &&
      (q.source === "all" || ban.source === q.source) &&
      kindOf(ban, q.kind),
  );
  const factor = q.dir === "asc" ? 1 : -1;
  return filtered.sort(
    (a, b) => factor * compare(a, b, q.sort) || ipSortKey(a.ip).localeCompare(ipSortKey(b.ip)),
  );
}

export function toggleSort(q: BanQuery, key: BanSortKey): BanQuery {
  if (q.sort === key) return { ...q, dir: q.dir === "asc" ? "desc" : "asc" };
  return { ...q, sort: key, dir: key === "ip" || key === "country" ? "asc" : "desc" };
}
