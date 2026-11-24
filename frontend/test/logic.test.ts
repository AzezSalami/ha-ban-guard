import { describe, expect, it } from "vitest";
import { parseBackupText } from "../src/logic/backup";
import {
  countdown,
  downloadName,
  flag,
  formatCountdown,
  niceCeil,
  scaleBars,
} from "../src/logic/format";
import { TRANSLATIONS, resolveLanguage, translator } from "../src/logic/i18n";
import {
  isAllowValue,
  isCIDR,
  isDuration,
  isHostname,
  isIP,
  isIPOrCIDR,
  isIPv6,
  splitEntries,
} from "../src/logic/ip";
import { DEFAULT_QUERY, ipSortKey, queryBans, toggleSort } from "../src/logic/table";
import type { Ban } from "../src/types";

describe("ip validation", () => {
  it.each(["1.2.3.4", "255.255.255.255", "::1", "2001:db8::1", "::ffff:1.2.3.4", "fe80::1%eth0"])(
    "accepts %s",
    (value) => expect(isIP(value)).toBe(true),
  );
  it.each(["1.2.3", "256.1.1.1", "1.2.3.4.5", "2001:db8:::1", "abc", "", "1::2::3"])(
    "rejects %s",
    (value) => expect(isIP(value)).toBe(false),
  );
  it("validates CIDR", () => {
    expect(isCIDR("10.0.0.0/8")).toBe(true);
    expect(isCIDR("2001:db8::/32")).toBe(true);
    expect(isCIDR("10.0.0.0/33")).toBe(false);
    expect(isCIDR("2001:db8::/129")).toBe(false);
    expect(isCIDR("10.0.0.0/")).toBe(false);
    expect(isCIDR("10.0.0.0/8/8")).toBe(false);
    expect(isCIDR("host/8")).toBe(false);
    expect(isIPOrCIDR(" 1.2.3.4 ")).toBe(true);
  });
  it("validates full IPv6 forms", () => {
    expect(isIPv6("2001:0db8:0000:0000:0000:ff00:0042:8329")).toBe(true);
    expect(isIPv6("2001:db8:0:0:0:ff00:42")).toBe(false);
    expect(isIPv6("::ffff:999.1.1.1")).toBe(false);
  });
  it("validates hostnames", () => {
    expect(isHostname("vpn.example.com")).toBe(true);
    expect(isHostname("1.2.3.4")).toBe(false);
    expect(isHostname("-bad.example")).toBe(false);
    expect(isAllowValue("home.example.org")).toBe(true);
    expect(isAllowValue("192.168.0.0/16")).toBe(true);
    expect(isAllowValue("not valid")).toBe(false);
  });
  it("splits pasted lists", () => {
    expect(splitEntries("1.2.3.4, 5.6.7.8\n1.2.3.4  10.0.0.0/8")).toEqual([
      "1.2.3.4",
      "5.6.7.8",
      "10.0.0.0/8",
    ]);
  });
  it("validates durations", () => {
    expect(isDuration("30m")).toBe(true);
    expect(isDuration("24H")).toBe(true);
    expect(isDuration("permanent")).toBe(true);
    expect(isDuration("0m")).toBe(false);
    expect(isDuration("soon")).toBe(false);
  });
});

describe("format", () => {
  it("builds flag emoji", () => {
    expect(flag("de")).toBe("🇩🇪");
    expect(flag(null)).toBe("");
    expect(flag("DEU")).toBe("");
  });
  it("computes countdowns", () => {
    const now = Date.parse("2026-01-01T00:00:00Z");
    expect(countdown(null, now)).toBeNull();
    expect(countdown("garbage", now)).toBeNull();
    expect(countdown("2025-12-31T00:00:00Z", now)?.expired).toBe(true);
    const c = countdown("2026-01-02T03:04:05Z", now)!;
    expect(c).toMatchObject({ days: 1, hours: 3, minutes: 4, seconds: 5, expired: false });
    expect(formatCountdown(c)).toBe("1d 3h");
    expect(formatCountdown({ ...c, days: 0 })).toBe("3h 04m");
    expect(formatCountdown({ ...c, days: 0, hours: 0 })).toBe("4m 05s");
  });
  it("scales bars to a nice maximum", () => {
    expect(niceCeil(0)).toBe(0);
    expect(niceCeil(7)).toBe(10);
    expect(niceCeil(13)).toBe(20);
    expect(niceCeil(230)).toBe(250);
    expect(scaleBars([0, 5, 10]).ratios).toEqual([0, 0.5, 1]);
    expect(scaleBars([0, 0]).ratios).toEqual([0, 0]);
  });
  it("names downloads", () => {
    expect(downloadName("ban_guard", new Date("2026-03-04T05:06:07Z"))).toBe(
      "ban_guard-2026-03-04-05-06-07.json",
    );
  });
});

function ban(partial: Partial<Ban>): Ban {
  return {
    ip: "1.2.3.4",
    reason: "",
    source: "manual",
    created_by: null,
    created_at: "2026-01-01T00:00:00Z",
    expires_at: null,
    offense: 0,
    single: true,
    country: null,
    city: null,
    in_ip_bans_yaml: true,
    ...partial,
  };
}

describe("ban table", () => {
  const bans = [
    ban({ ip: "10.0.0.10", reason: "ssh brute force", country: "DE" }),
    ban({ ip: "10.0.0.2", source: "automatic", expires_at: "2026-02-01T00:00:00Z" }),
    ban({ ip: "2001:db8::/32", single: false, created_at: "2026-01-05T00:00:00Z" }),
  ];
  it("sorts IPs numerically", () => {
    expect(ipSortKey("10.0.0.2") < ipSortKey("10.0.0.10")).toBe(true);
    expect(ipSortKey("2001:db8::1") < ipSortKey("2001:db8::2")).toBe(true);
    const result = queryBans(bans, { ...DEFAULT_QUERY, sort: "ip", dir: "asc" });
    expect(result.map((b) => b.ip)).toEqual(["10.0.0.2", "10.0.0.10", "2001:db8::/32"]);
  });
  it("filters by search, source and kind", () => {
    expect(queryBans(bans, { ...DEFAULT_QUERY, search: "SSH de" }).map((b) => b.ip)).toEqual([
      "10.0.0.10",
    ]);
    expect(queryBans(bans, { ...DEFAULT_QUERY, source: "automatic" })).toHaveLength(1);
    expect(queryBans(bans, { ...DEFAULT_QUERY, kind: "temporary" })).toHaveLength(1);
    expect(queryBans(bans, { ...DEFAULT_QUERY, kind: "permanent" })).toHaveLength(2);
    expect(queryBans(bans, { ...DEFAULT_QUERY, kind: "network" })).toHaveLength(1);
  });
  it("sorts by expiry with permanent last", () => {
    const result = queryBans(bans, { ...DEFAULT_QUERY, sort: "expires_at", dir: "asc" });
    expect(result[0]!.ip).toBe("10.0.0.2");
  });
  it("sorts by created, country and source", () => {
    expect(queryBans(bans, DEFAULT_QUERY)[0]!.ip).toBe("2001:db8::/32");
    expect(queryBans(bans, { ...DEFAULT_QUERY, sort: "country", dir: "asc" })[0]!.ip).toBe(
      "10.0.0.10",
    );
    expect(queryBans(bans, { ...DEFAULT_QUERY, sort: "source", dir: "asc" })[0]!.ip).toBe(
      "10.0.0.2",
    );
  });
  it("toggles sort direction", () => {
    const q = toggleSort(DEFAULT_QUERY, "ip");
    expect(q).toMatchObject({ sort: "ip", dir: "asc" });
    expect(toggleSort(q, "ip").dir).toBe("desc");
    expect(toggleSort(q, "created_at").dir).toBe("desc");
  });
});

describe("i18n", () => {
  it("falls back to English", () => {
    expect(resolveLanguage("en-GB")).toBe("en");
    expect(resolveLanguage("xx")).toBe("en");
    expect(resolveLanguage(undefined)).toBe("en");
    const t = translator("de");
    expect(t("tabs.bans")).toBe("Bans");
    expect(t("bans.banned", { ip: "1.2.3.4" })).toBe("Banned 1.2.3.4.");
    expect(t("bans.banned", {})).toBe("Banned {ip}.");
    expect(t("missing.key")).toBe("missing.key");
    expect(t("tabs")).toBe("tabs");
  });
  it("has no empty strings", () => {
    const walk = (node: unknown): void => {
      if (typeof node === "string") expect(node.trim()).not.toBe("");
      else Object.values(node as object).forEach(walk);
    };
    walk(TRANSLATIONS["en"]);
  });
});

describe("backup parsing", () => {
  it("rejects invalid JSON and foreign files", () => {
    expect(parseBackupText("{")).toEqual({ ok: false, error: "invalid_json" });
    expect(parseBackupText("[]")).toEqual({ ok: false, error: "not_backup" });
    expect(parseBackupText('{"format":"other"}')).toEqual({ ok: false, error: "not_backup" });
  });
  it("accepts a backup", () => {
    const result = parseBackupText('{"format":"ban_guard","version":1}');
    expect(result.ok).toBe(true);
  });
});

import { describeEnforcement, needsAttention } from "../src/logic/enforcement";

describe("enforcement", () => {
  const t = translator("en");
  const base = { enforced: true, partial: false, reason: null, protected: null, exempt: [] };

  it("is silent when fully enforced or unknown", () => {
    expect(describeEnforcement(base, t)).toEqual({ level: "ok", label: "", detail: "" });
    expect(describeEnforcement(undefined, t).level).toBe("ok");
    expect(needsAttention(ban({}))).toBe(false);
    expect(needsAttention(ban({ enforcement: base }))).toBe(false);
  });

  it("explains an admin-protected address", () => {
    const info = describeEnforcement(
      { ...base, enforced: false, reason: "protected_admin", protected: "198.51.100.9/32" },
      t,
    );
    expect(info.level).toBe("off");
    expect(info.label).toBe("Not enforced");
    expect(info.detail).toContain("administrator used 198.51.100.9/32");
  });

  it("explains partial ranges, inactive hooks and unknown reasons", () => {
    const partial = describeEnforcement(
      { ...base, partial: true, reason: "partial", exempt: ["10.0.0.5", "10.0.0.6"] },
      t,
    );
    expect(partial).toMatchObject({ level: "partial", label: "Partly exempt" });
    expect(partial.detail).toContain("10.0.0.5, 10.0.0.6");
    expect(
      describeEnforcement({ ...base, enforced: false, reason: "hook_ip_ban_disabled" }, t).detail,
    ).toContain("ip_ban_disabled");
    expect(describeEnforcement({ ...base, enforced: false, reason: "new_thing" }, t).detail).toBe(
      "Ban Guard cannot apply this ban right now.",
    );
    expect(describeEnforcement({ ...base, enforced: false }, t).level).toBe("off");
  });

  it("filters bans that need attention", () => {
    const off = ban({ ip: "1.1.1.1", enforcement: { ...base, enforced: false, reason: "allowlisted" } });
    const partial = ban({ ip: "10.0.0.0/8", enforcement: { ...base, partial: true, reason: "partial" } });
    const fine = ban({ ip: "2.2.2.2", enforcement: base });
    const rows = queryBans([off, partial, fine], { ...DEFAULT_QUERY, kind: "unenforced" });
    expect(rows.map((b) => b.ip).sort()).toEqual(["1.1.1.1", "10.0.0.0/8"]);
  });
});
