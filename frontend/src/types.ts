// Shapes returned by the ban_guard/* websocket commands.

export interface Enforcement {
  enforced: boolean;
  partial: boolean;
  reason: string | null;
  protected: string | null;
  exempt: string[];
}

export interface Ban {
  ip: string;
  reason: string;
  source: "manual" | "automatic" | "imported" | "service" | "home_assistant";
  created_by: string | null;
  created_at: string;
  expires_at: string | null;
  offense: number;
  single: boolean;
  country: string | null;
  city: string | null;
  in_ip_bans_yaml: boolean;
  enforcement?: Enforcement;
}

export interface AllowEntry {
  value: string;
  comment: string;
  created_by: string | null;
  created_at: string;
  resolved: string[];
  resolved_at: string | null;
  hostname: boolean;
}

export type ActivityType =
  | "login"
  | "failed_login"
  | "allowlisted_failure"
  | "ban"
  | "unban"
  | "expired"
  | "blocked"
  | "allow"
  | "disallow"
  | "refused";

export interface ActivityEntry {
  id: number;
  ts: string;
  type: ActivityType;
  ip: string;
  path: string | null;
  user_agent: string | null;
  detail: string | null;
  user: string | null;
  country?: string | null;
}

export interface Status {
  hook: string;
  protection_enabled: boolean;
  login_logging: boolean;
  session_closing: boolean;
  open_sessions: number;
  ha_login_threshold: number | null;
  geoip: { enabled: boolean; loaded: boolean; edition: string; error: string | null };
  rdns: boolean;
  doh: boolean;
  npm: { enabled: boolean; ok?: boolean; error?: string; count?: number; synced_at?: string };
  country_rules: { allow: string[]; deny: string[] };
  under_attack: boolean;
}

export interface Overview {
  active_bans: number;
  allowlist: number;
  recent_failures: number;
  last_ban: { ip: string; reason: string; created_at: string; country: string | null } | null;
  status: Status;
  failed_logins_24h: number;
  bans_24h: number;
  blocked_24h: number;
  logins_24h: number;
  failed_logins_7d: { date: string; count: number }[];
  top_ips: { ip: string; count: number }[];
  top_countries: { country: string; count: number }[];
}

export interface History {
  ip: string;
  ban: Ban | null;
  geo: { country: string; country_name: string | null; city: string | null } | null;
  hostname: string | null;
  offenses: number;
  allowlisted: boolean;
  activity: ActivityEntry[];
}

export interface SessionInfo {
  id: string;
  ip: string;
  user: string | null;
  client_id: string | null;
  client_name: string | null;
  user_agent: string | null;
  connected_at: string;
  country: string | null;
  current: boolean;
  protected: boolean;
  allowlisted: boolean;
}

export interface Settings {
  entry_id: string;
  options: Record<string, unknown>;
  status: Status;
  requester_ip: string | null;
  npm_addon: { slug: string; name: string; state: string | null } | null;
}

export interface ImportPreview {
  bans_new: Partial<Ban>[];
  bans_existing: string[];
  bans_expired: string[];
  allow_new: { value: string; comment: string }[];
  allow_existing: { value: string; comment: string }[];
  errors: { section: string; index?: number; error: string; [key: string]: unknown }[];
  settings: Record<string, unknown>;
}

export interface Backup {
  format: "ban_guard";
  version: number;
  exported_at: string;
  bans: unknown[];
  allowlist: unknown[];
  settings: Record<string, unknown>;
}

// Minimal subset of Home Assistant's frontend `hass` object we rely on.
export interface HassConnection {
  sendMessagePromise<T>(msg: Record<string, unknown>): Promise<T>;
  subscribeMessage<T>(
    callback: (msg: T) => void,
    msg: Record<string, unknown>,
  ): Promise<() => Promise<void>>;
}

export interface Hass {
  connection: HassConnection;
  language: string;
  locale?: { language: string };
  themes?: { darkMode?: boolean };
  user?: { is_admin: boolean; name: string };
}

export interface WsError {
  code: string;
  message: string;
  translation_key?: string;
  translation_placeholders?: Record<string, string>;
}
