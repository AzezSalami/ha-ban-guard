import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Ctx } from "../context";
import { flag, formatDateTime } from "../logic/format";
import { shared } from "../styles";
import type { ActivityEntry, ActivityType } from "../types";

const TYPES: ActivityType[] = [
  "login",
  "failed_login",
  "allowlisted_failure",
  "ban",
  "unban",
  "expired",
  "blocked",
  "allow",
  "disallow",
  "refused",
];
const PAGE = 100;
const MAX_LIVE = 1000;

const TYPE_CLASS: Partial<Record<ActivityType, string>> = {
  login: "good",
  failed_login: "warn",
  allowlisted_failure: "warn",
  ban: "bad",
  blocked: "bad",
  refused: "bad",
  unban: "good",
  allow: "good",
};

@customElement("bg-activity")
export class BgActivity extends LitElement {
  @property({ attribute: false }) ctx!: Ctx;
  @state() private entries: ActivityEntry[] | null = null;
  @state() private filter: ActivityType | "all" = "all";
  @state() private live = true;
  @state() private more = true;
  private unsub: (() => Promise<void>) | null = null;
  private buffered: ActivityEntry[] = [];

  override connectedCallback(): void {
    super.connectedCallback();
    if (this.ctx) void this.start();
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    void this.unsub?.();
    this.unsub = null;
  }

  protected override firstUpdated(): void {
    if (!this.unsub) void this.start();
  }

  private async start(): Promise<void> {
    await this.load();
    if (this.unsub) return;
    try {
      this.unsub = await this.ctx.api.subscribeActivity((entry) => this.onEntry(entry));
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private onEntry(entry: ActivityEntry): void {
    if (!this.live) {
      this.buffered.push(entry);
      return;
    }
    if (this.filter !== "all" && entry.type !== this.filter) return;
    this.entries = [entry, ...(this.entries ?? [])].slice(0, MAX_LIVE);
  }

  private types(): ActivityType[] | undefined {
    return this.filter === "all" ? undefined : [this.filter];
  }

  private async load(): Promise<void> {
    try {
      const page = await this.ctx.api.activity({ limit: PAGE, types: this.types() });
      this.entries = page;
      this.more = page.length === PAGE;
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private async loadMore(): Promise<void> {
    const last = this.entries?.[this.entries.length - 1];
    if (!last) return;
    try {
      const page = await this.ctx.api.activity({
        limit: PAGE,
        before_id: last.id,
        types: this.types(),
      });
      this.entries = [...(this.entries ?? []), ...page];
      this.more = page.length === PAGE;
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private toggleLive(): void {
    this.live = !this.live;
    if (this.live && this.buffered.length) {
      const fresh = this.buffered
        .filter((e) => this.filter === "all" || e.type === this.filter)
        .reverse();
      this.entries = [...fresh, ...(this.entries ?? [])].slice(0, MAX_LIVE);
      this.buffered = [];
    }
  }

  protected override render() {
    const { t, language } = this.ctx;
    const toolbar = html`<div class="row toolbar">
      <select
        aria-label=${t("activity.filter")}
        @change=${(e: Event) => {
          this.filter = (e.target as HTMLSelectElement).value as ActivityType | "all";
          void this.load();
        }}
      >
        <option value="all">${t("activity.all")}</option>
        ${TYPES.map(
          (type) =>
            html`<option value=${type} ?selected=${this.filter === type}>
              ${t(`activity.types.${type}`)}
            </option>`,
        )}
      </select>
      <span class="spacer"></span>
      <span class="chip ${this.live ? "good" : ""}" aria-live="polite">
        ${this.live ? t("activity.live") : t("activity.paused")}
      </span>
      <button
        class="icon"
        @click=${this.toggleLive}
        aria-label=${this.live ? t("activity.pause") : t("activity.resume")}
        aria-pressed=${!this.live}
        title=${this.live ? t("activity.pause") : t("activity.resume")}
      >
        <ha-icon icon=${this.live ? "mdi:pause" : "mdi:play"}></ha-icon>
      </button>
    </div>`;
    if (this.entries === null) return html`<p class="muted">${t("common.loading")}</p>`;
    if (!this.entries.length) {
      return html`<ha-card>
        ${toolbar}
        <div class="empty">
          <ha-icon icon="mdi:timeline-clock-outline" aria-hidden="true"></ha-icon>
          <h3>${t("activity.empty_title")}</h3>
          <p>${t("activity.empty_body")}</p>
        </div>
      </ha-card>`;
    }
    return html`<ha-card>
      ${toolbar}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>${t("activity.col_time")}</th>
              <th>${t("activity.col_type")}</th>
              <th>${t("activity.col_ip")}</th>
              <th class="hide-narrow">${t("activity.col_path")}</th>
              <th class="hide-narrow">${t("activity.col_details")}</th>
            </tr>
          </thead>
          <tbody>
            ${this.entries.map(
              (e) => html`<tr>
                <td class="time">${formatDateTime(e.ts, language)}</td>
                <td>
                  <span class="chip ${TYPE_CLASS[e.type] ?? ""}">${t(`activity.types.${e.type}`)}</span>
                </td>
                <td>
                  <button
                    class="link mono"
                    @click=${() => this.ctx.openDetails(e.ip)}
                    aria-label=${t("common.details", { ip: e.ip })}
                  >
                    ${e.country ? `${flag(e.country)} ` : ""}${e.ip}
                  </button>
                </td>
                <td class="hide-narrow mono">${e.path ?? ""}</td>
                <td class="hide-narrow details">
                  ${[e.detail, e.user, e.user_agent].filter(Boolean).join(" · ")}
                </td>
              </tr>`,
            )}
          </tbody>
        </table>
      </div>
      ${this.more
        ? html`<div class="row more">
            <button @click=${this.loadMore}>${t("activity.load_more")}</button>
          </div>`
        : nothing}
    </ha-card>`;
  }

  static override styles = [
    shared,
    css`
      .toolbar {
        margin-bottom: 8px;
      }
      select {
        width: auto;
      }
      .time {
        white-space: nowrap;
        font-size: 0.85rem;
      }
      .details {
        max-width: 320px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.85rem;
        color: var(--secondary-text-color);
      }
      .link {
        border: none;
        padding: 0;
        min-height: 0;
        border-radius: 0;
        text-align: start;
      }
      .more {
        justify-content: center;
        margin-top: 12px;
      }
    `,
  ];
}
