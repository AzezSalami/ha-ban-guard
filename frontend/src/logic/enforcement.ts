// Human-readable enforcement status for a ban (unit tested).
import type { Translate } from "./i18n";
import type { Ban, Enforcement } from "../types";

export type EnforcementLevel = "ok" | "partial" | "off";

export interface EnforcementInfo {
  level: EnforcementLevel;
  /** Short chip text, empty when the ban is fully enforced. */
  label: string;
  /** One sentence explaining why, empty when fully enforced. */
  detail: string;
}

export function describeEnforcement(e: Enforcement | undefined, t: Translate): EnforcementInfo {
  if (!e || (e.enforced && !e.partial)) return { level: "ok", label: "", detail: "" };
  const reason = e.reason ?? "unknown";
  let detail: string;
  if (reason.startsWith("hook_")) {
    detail = t("enforcement.reasons.hook", { status: reason.slice("hook_".length) });
  } else {
    const key = `enforcement.reasons.${reason}`;
    const text = t(key, { protected: e.protected ?? "", exempt: e.exempt.join(", ") });
    detail = text === key ? t("enforcement.reasons.unknown") : text;
  }
  return e.enforced
    ? { level: "partial", label: t("enforcement.partial"), detail }
    : { level: "off", label: t("enforcement.not_enforced"), detail };
}

/** Bans that are not, or only partly, applied. */
export function needsAttention(ban: Ban): boolean {
  return !!ban.enforcement && (!ban.enforcement.enforced || ban.enforcement.partial);
}
