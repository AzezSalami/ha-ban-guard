import { LitElement, css, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { errorMessage } from "../api";
import type { Ctx } from "../context";
import { describeClient } from "../logic/client";
import { flag, formatDateTime, formatElapsed } from "../logic/format";
import { shared } from "../styles";
import type { SessionInfo } from "../types";

/** Live list of open, authenticated sessions (app and browser connections). */
@customElement("bg-sessions")
export class BgSessions extends LitElement {
  @property({ attribute: false }) ctx!: Ctx;
  @property({ type: Number }) revision = 0;
  @state() private sessions: SessionInfo[] | null = null;
  @state() private available = true;
  @state() private now = Date.now();
  @state() private busy = new Set<string>();
  private ticker: number | undefined;

  override connectedCallback(): void {
    super.connectedCallback();
    this.ticker = window.setInterval(() => (this.now = Date.now()), 30_000);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearInterval(this.ticker);
  }

  protected override updated(changed: Map<string, unknown>): void {
    if (changed.has("revision") || changed.has("ctx")) void this.load();
  }

  private async load(): Promise<void> {
    try {
      const result = await this.ctx.api.sessions();
      this.sessions = result.sessions;
      this.available = result.available;
      this.now = Date.now();
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private setBusy(id: string, on: boolean): void {
    const next = new Set(this.busy);
    if (on) next.add(id);
    else next.delete(id);
    this.busy = next;
  }

  private who(s: SessionInfo): string {
    return s.user ?? this.ctx.t("sessions.unknown_user");
  }

  private async disconnect(s: SessionInfo): Promise<void> {
    const { t } = this.ctx;
    const client = describeClient(s.client_id, s.client_name, s.user_agent).label;
    const ok = await this.ctx.confirm({
      title: t("sessions.confirm_disconnect_title", { user: this.who(s) }),
      body: t("sessions.confirm_disconnect_body", { client, ip: s.ip }),
      confirm: t("sessions.disconnect"),
      destructive: true,
    });
    if (!ok) return;
    this.setBusy(s.id, true);
    try {
      await this.ctx.api.disconnect(s.id);
      this.ctx.toast({ message: t("sessions.disconnected", { user: this.who(s), ip: s.ip }) });
      await this.load();
    } catch (err) {
      this.ctx.toast({ message: errorMessage(err, t) });
    } finally {
      this.setBusy(s.id, false);
    }
  }

  private async ban(s: SessionInfo): Promise<void> {
    const { t } = this.ctx;
    const ok = await this.ctx.confirm({
      title: t("sessions.confirm_ban_title", { ip: s.ip }),
      body: t("sessions.confirm_ban_body", { ip: s.ip }),
      confirm: t("bans.add"),
      destructive: true,
    });
    if (!ok) return;
    this.setBusy(s.id, true);
    try {
      await this.ctx.api.ban(s.ip, t("sessions.ban_reason"), "permanent");
      this.ctx.toast({ message: t("bans.banned", { ip: s.ip }) });
      await this.load();
    } catch (err) {
      this.ctx.toast({ message: errorMessage(err, t) });
    } finally {
      this.setBusy(s.id, false);
    }
  }

  private actions(s: SessionInfo) {
    const { t } = this.ctx;
    if (s.current) return html`<span class="chip good">${t("sessions.this_session")}</span>`;
    const busy = this.busy.has(s.id);
    return html`<div class="row actions">
      <button
        ?disabled=${busy}
        @click=${() => this.disconnect(s)}
        aria-label=${t("sessions.disconnect_label", { user: this.who(s), ip: s.ip })}
      >
        ${t("sessions.disconnect")}
      </button>
      ${s.protected || s.allowlisted
        ? html`<span class="chip" title=${t("sessions.cannot_ban_help")}>
            ${s.protected ? t("sessions.protected") : t("sessions.allowlisted")}
          </span>`
        : html`<button
            class="danger"
            ?disabled=${busy}
            @click=${() => this.ban(s)}
            aria-label=${t("sessions.ban_label", { ip: s.ip })}
          >
            ${t("sessions.ban")}
          </button>`}
    </div>`;
  }

  protected override render() {
    const { t, language } = this.ctx;
    if (this.sessions === null) return html`<p class="muted">${t("common.loading")}</p>`;
    if (!this.available) {
      return html`<ha-card class="empty">
        <ha-icon icon="mdi:lan-disconnect" aria-hidden="true"></ha-icon>
        <h3>${t("sessions.unavailable_title")}</h3>
        <p>${t("sessions.unavailable_body")}</p>
      </ha-card>`;
    }
    const users = new Set(this.sessions.map((s) => s.user ?? "?")).size;
    return html`<ha-card>
      <div class="row toolbar">
        <span class="muted">
          ${t("sessions.summary", { count: this.sessions.length, users })}
        </span>
        <span class="spacer"></span>
        <button @click=${this.load}>${t("sessions.refresh")}</button>
      </div>
      ${this.sessions.length
        ? html`<div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>${t("sessions.col_user")}</th>
                  <th>${t("sessions.col_ip")}</th>
                  <th>${t("sessions.col_client")}</th>
                  <th>${t("sessions.col_connected")}</th>
                  <th><span class="sr-only">${t("sessions.col_actions")}</span></th>
                </tr>
              </thead>
              <tbody>
                ${this.sessions.map((s) => {
                  const client = describeClient(s.client_id, s.client_name, s.user_agent);
                  return html`<tr class=${s.current ? "current" : ""}>
                    <td class="user">${this.who(s)}</td>
                    <td class="ip">
                      <button
                        class="link mono"
                        @click=${() => this.ctx.openDetails(s.ip)}
                        aria-label=${t("common.details", { ip: s.ip })}
                      >
                        ${s.country ? `${flag(s.country)} ` : ""}${s.ip}
                      </button>
                    </td>
                    <td class="client" title=${s.user_agent ?? ""}>
                      <ha-icon
                        class="client-icon"
                        aria-hidden="true"
                        icon=${client.kind === "app"
                          ? "mdi:cellphone"
                          : client.kind === "browser"
                            ? "mdi:web"
                            : "mdi:devices"}
                      ></ha-icon>
                      ${client.label || t("common.unknown")}
                    </td>
                    <td class="time" title=${formatDateTime(s.connected_at, language)}>
                      ${t("sessions.for", { time: formatElapsed(s.connected_at, this.now) })}
                    </td>
                    <td class="act">${this.actions(s)}</td>
                  </tr>`;
                })}
              </tbody>
            </table>
          </div>`
        : html`<div class="empty">
            <ha-icon icon="mdi:devices" aria-hidden="true"></ha-icon>
            <h3>${t("sessions.empty_title")}</h3>
            <p>${t("sessions.empty_body")}</p>
          </div>`}
      <p class="help">${t("sessions.privacy")}</p>
    </ha-card>`;
  }

  static override styles = [
    shared,
    css`
      .toolbar {
        margin-bottom: 8px;
      }
      .link {
        border: none;
        padding: 0;
        min-height: 0;
        border-radius: 0;
        text-align: start;
      }
      .client-icon {
        --mdc-icon-size: 18px;
        color: var(--secondary-text-color);
        margin-inline-end: 4px;
      }
      .actions {
        justify-content: flex-end;
        flex-wrap: nowrap;
      }
      tr.current td {
        background: var(--secondary-background-color);
      }
      /* Phones: one card per session instead of a wide table. */
      @media (max-width: 600px) {
        thead {
          display: none;
        }
        table,
        tbody {
          display: block;
        }
        tr {
          display: grid;
          grid-template-columns: 1fr auto;
          grid-template-areas: "user time" "ip ip" "client client" "act act";
          gap: 2px 8px;
          padding: 10px 4px;
          border-bottom: 1px solid var(--divider-color);
        }
        tr.current {
          background: var(--secondary-background-color);
        }
        td {
          border: none;
          padding: 0;
          background: none !important;
        }
        td.user {
          grid-area: user;
          font-weight: 500;
        }
        td.time {
          grid-area: time;
          color: var(--secondary-text-color);
          font-size: 0.85rem;
        }
        td.ip {
          grid-area: ip;
        }
        td.ip .mono {
          word-break: normal;
        }
        td.client {
          grid-area: client;
          color: var(--secondary-text-color);
          font-size: 0.85rem;
        }
        td.act {
          grid-area: act;
          padding-top: 6px;
        }
        .actions {
          justify-content: flex-start;
        }
      }
    `,
  ];
}

