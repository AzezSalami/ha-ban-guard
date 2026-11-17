// Client-side pre-check of a backup file before the server-side dry run.

export type ParseResult =
  | { ok: true; data: Record<string, unknown> }
  | { ok: false; error: "invalid_json" | "not_backup" };

export function parseBackupText(text: string): ParseResult {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return { ok: false, error: "invalid_json" };
  }
  if (
    typeof data !== "object" ||
    data === null ||
    Array.isArray(data) ||
    (data as Record<string, unknown>)["format"] !== "ban_guard"
  ) {
    return { ok: false, error: "not_backup" };
  }
  return { ok: true, data: data as Record<string, unknown> };
}
