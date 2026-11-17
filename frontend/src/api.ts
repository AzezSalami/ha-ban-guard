// Typed wrappers around the ban_guard/* websocket commands.
import type {
  ActivityEntry,
  ActivityType,
  AllowEntry,
  Backup,
  Ban,
  Hass,
  History,
  ImportPreview,
  Overview,
  Settings,
  Status,
  WsError,
} from "./types";
import type { Translate } from "./logic/i18n";

export class Api {
  constructor(private readonly hass: Hass) {}

  private call<T>(type: string, data: Record<string, unknown> = {}): Promise<T> {
    return this.hass.connection.sendMessagePromise<T>({ type: `ban_guard/${type}`, ...data });
  }

  overview(): Promise<Overview> {
    return this.call("overview");
  }

  async bans(): Promise<Ban[]> {
    return (await this.call<{ bans: Ban[] }>("bans")).bans;
  }

  async ban(ip: string, reason: string, duration: string): Promise<Ban> {
    return (await this.call<{ ban: Ban }>("ban", { ip, reason, duration })).ban;
  }

  async unban(ips: string[]): Promise<Record<string, unknown>[]> {
    return (await this.call<{ removed: Record<string, unknown>[] }>("unban", { ips })).removed;
  }

  restore(bans: Record<string, unknown>[]): Promise<void> {
    return this.call("restore", { bans });
  }

  async allowlist(): Promise<AllowEntry[]> {
    return (await this.call<{ allowlist: AllowEntry[] }>("allowlist")).allowlist;
  }

  async allow(value: string, comment: string): Promise<AllowEntry> {
    return (await this.call<{ entry: AllowEntry }>("allow", { value, comment })).entry;
  }

  async disallow(value: string): Promise<AllowEntry> {
    return (await this.call<{ entry: AllowEntry }>("disallow", { value })).entry;
  }

  async activity(opts: {
    limit?: number;
    before_id?: number;
    ip?: string;
    types?: ActivityType[];
  }): Promise<ActivityEntry[]> {
    return (await this.call<{ entries: ActivityEntry[] }>("activity", opts)).entries;
  }

  subscribeActivity(cb: (entry: ActivityEntry) => void): Promise<() => Promise<void>> {
    return this.hass.connection.subscribeMessage<{ entry: ActivityEntry }>(
      (msg) => cb(msg.entry),
      { type: "ban_guard/subscribe_activity" },
    );
  }

  subscribeUpdates(cb: () => void): Promise<() => Promise<void>> {
    return this.hass.connection.subscribeMessage(() => cb(), {
      type: "ban_guard/subscribe_updates",
    });
  }

  history(ip: string): Promise<History> {
    return this.call("history", { ip });
  }

  exportBackup(): Promise<Backup> {
    return this.call("export");
  }

  importBackup(
    data: unknown,
    dryRun: boolean,
    includeSettings: boolean,
  ): Promise<{ dry_run: boolean; preview: ImportPreview }> {
    return this.call("import", { data, dry_run: dryRun, include_settings: includeSettings });
  }

  settings(): Promise<Settings> {
    return this.call("settings");
  }

  npmSync(): Promise<Status["npm"]> {
    return this.call("npm_sync");
  }
}

/** Turn a websocket error into a translated, user-readable message. */
export function errorMessage(err: unknown, t: Translate): string {
  const ws = err as Partial<WsError> | undefined;
  const key = ws?.translation_key ?? ws?.code;
  if (key) {
    const text = t(`errors.${key}`, ws?.translation_placeholders ?? {});
    if (text !== `errors.${key}`) return text;
  }
  const message = ws?.message ?? (err instanceof Error ? err.message : String(err));
  return t("common.error", { message });
}
