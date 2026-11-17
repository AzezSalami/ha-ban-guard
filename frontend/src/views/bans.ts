import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { errorMessage } from "../api";
import type { Ctx } from "../context";
import { countdown, flag, formatCountdown, formatDateTime } from "../logic/format";
import { isDuration, isIPOrCIDR, splitEntries } from "../logic/ip";
import {
  type BanKind,
  type BanQuery,
  type BanSortKey,
  DEFAULT_QUERY,
  queryBans,
  toggleSort,
} from "../logic/table";
import { shared } from "../styles";
import type { Ban } from "../types";

const SOURCES: (Ban["source"] | "all")[] = [
  "all",
  "manual",
  "automatic",
  "service",
  "imported",
  "home_assistant",
];
const KINDS: BanKind[] = ["all", "permanent", "temporary", "network"];

@customElement("bg-bans")
export class BgBans extends LitElement {
  @property({ attribute: false }) ctx!: Ctx;
  @property({ type: Number }) revision = 0;
  @state() private bans: Ban[] | null = null;
  @state() private query: BanQuery = { ...DEFAULT_QUERY };
  @state() private selected = new Set<string>();
  @state() private now = Date.now();
  @state() private adding = false;
  @state() private form = { ips: "", reason: "", duration: "permanent" };
  @state() private formError = "";
  @state() private busy = false;
  private ticker: number | undefined;

  override connectedCallback(): void {
    super.connectedCallback();
    this.ticker = window.setInterval(() => {
      this.now = Date.now();
    }, 1000);
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
      this.bans = await this.ctx.api.bans();
      const keys = new Set(this.bans.map((b) => b.ip));
      this.selected = new Set([...this.selected].filter((ip) => keys.has(ip)));
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private async unban(ips: string[]): Promise<void> {
    const { t } = this.ctx;
    const ok = await this.ctx.confirm({
      title: t("bans.confirm_unban_title", { count: ips.length }),
      body: t("bans.confirm_unban_body", {
        list: ips.slice(0, 10).join(", ") + (ips.length > 10 ? " …" : ""),
      }),
      confirm: t("bans.unban"),
      destructive: true,
    });
    if (!ok) return;
    try {
      const removed = await this.ctx.api.unban(ips);
      this.selected = new Set();
      this.ctx.toast({
        message: t("bans.unbanned", { count: removed.length }),
        actionLabel: t("common.undo"),
        action: async () => {
          try {
            await this.ctx.api.restore(removed);
          } catch (err) {
            this.ctx.error(err);
          }
        },
      });
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private async submit(ev: Event): Promise<void> {
    ev.preventDefault();
    const { t } = this.ctx;
    const ips = splitEntries(this.form.ips);
    const bad = ips.find((ip) => !isIPOrCIDR(ip));
    if (!ips.length || bad !== undefined) {
      this.formError = t("bans.invalid_ip", { value: bad ?? "" });
      return;
    }
    if (!isDuration(this.form.duration)) {
      this.formError = t("bans.invalid_duration");
      return;
    }
    this.busy = true;
    this.formError = "";
    try {
      for (const ip of ips) {
        await this.ctx.api.ban(ip, this.form.reason, this.form.duration);
      }
      this.adding = false;
      this.ctx.toast({ message: t("bans.banned", { ip: ips.join(", ") }) });
      this.form = { ips: "", reason: "", duration: "permanent" };
    } catch (err) {
      this.formError = errorMessage(err, t);
    } finally {
      this.busy = false;
    }
  }

  private toggle(ip: string, on: boolean): void {
    const next = new Set(this.selected);
    if (on) next.add(ip);
    else next.delete(ip);
    this.selected = next;
  }

  private header(key: BanSortKey, label: string, cls = "") {
    const active = this.query.sort === key;
    const sort = active ? (this.query.dir === "asc" ? "ascending" : "descending") : "none";
    return html`<th aria-sort=${sort} class=${cls}>
      <button
        @click=${() => (this.query = toggleSort(this.query, key))}
        aria-label=${this.ctx.t("bans.sort_by", { column: label })}
      >
        ${label}${active ? (this.query.dir === "asc" ? " ▲" : " ▼") : ""}
      </button>
    </th>`;
  }

  private expiry(ban: Ban) {
    const { t } = this.ctx;
    const c = countdown(ban.expires_at, this.now);
    if (!c) return html`<span class="chip">${t("common.permanent")}</span>`;
    if (c.expired) return html`<span class="chip">${t("common.expired")}</span>`;
    return html`<span class="chip warn" title=${formatDateTime(ban.expires_at, this.ctx.language)}>
      ${formatCountdown(c)}
    </span>`;
  }

  private renderDialog() {
    const { t } = this.ctx;
    return html`<bg-dialog
      .open=${this.adding}
      .heading=${t("bans.add_title")}
      @closed=${() => (this.adding = false)}
    >
      <form id="ban-form" @submit=${this.submit}>
        <label for="ips">${t("bans.ip_label")}</label>
        <textarea
          id="ips"
          rows="2"
          required
          aria-describedby="ips-help"
          .value=${this.form.ips}
          @input=${(e: Event) =>
            (this.form = { ...this.form, ips: (e.target as HTMLTextAreaElement).value })}
        ></textarea>
        <div class="help" id="ips-help">${t("bans.ip_help")}</div>
        <label for="reason">${t("bans.reason_label")}</label>
        <input
          id="reason"
          maxlength="200"
          .value=${this.form.reason}
          @input=${(e: Event) =>
            (this.form = { ...this.form, reason: (e.target as HTMLInputElement).value })}
        />
        <label for="duration">${t("bans.duration_label")}</label>
        <input
          id="duration"
          list="durations"
          aria-describedby="duration-help"
          .value=${this.form.duration}
          @input=${(e: Event) =>
            (this.form = { ...this.form, duration: (e.target as HTMLInputElement).value })}
        />
        <datalist id="durations">
          ${["1h", "24h", "7d", "30d", "permanent"].map((d) => html`<option value=${d}></option>`)}
        </datalist>
        <div class="help" id="duration-help">${t("bans.duration_help")}</div>
        ${this.formError
          ? html`<div class="error" role="alert">${this.formError}</div>`
          : nothing}
      </form>
      <button slot="actions" @click=${() => (this.adding = false)}>
        ${t("common.cancel")}
      </button>
      <button
        slot="actions"
        class="primary"
        type="submit"
        form="ban-form"
        ?disabled=${this.busy}
      >
        ${t("bans.add")}
      </button>
    </bg-dialog>`;
  }

  protected override render() {
    const { t, language } = this.ctx;
    if (this.bans === null) return html`<p class="muted">${t("common.loading")}</p>`;
    const rows = queryBans(this.bans, this.query);
    const allSelected = rows.length > 0 && rows.every((b) => this.selected.has(b.ip));
    const toolbar = html`<div class="row toolbar">
      <input
        type="search"
        class="search"
        placeholder=${t("common.search")}
        aria-label=${t("common.search")}
        .value=${this.query.search}
        @input=${(e: Event) =>
          (this.query = { ...this.query, search: (e.target as HTMLInputElement).value })}
      />
      <select
        aria-label=${t("bans.filter_source")}
        @change=${(e: Event) =>
          (this.query = {
            ...this.query,
            source: (e.target as HTMLSelectElement).value as BanQuery["source"],
          })}
      >
        ${SOURCES.map(
          (s) =>
            html`<option value=${s} ?selected=${this.query.source === s}>
              ${t(`bans.source_${s}`)}
            </option>`,
        )}
      </select>
      <select
        aria-label=${t("bans.filter_kind")}
        @change=${(e: Event) =>
          (this.query = { ...this.query, kind: (e.target as HTMLSelectElement).value as BanKind })}
      >
        ${KINDS.map(
          (k) =>
            html`<option value=${k} ?selected=${this.query.kind === k}>
              ${t(`bans.kind_${k}`)}
            </option>`,
        )}
      </select>
      <span class="spacer"></span>
      ${this.selected.size
        ? html`<button class="danger" @click=${() => this.unban([...this.selected])}>
            ${t("bans.unban_selected", { count: this.selected.size })}
          </button>`
        : nothing}
      <button class="primary" @click=${() => (this.adding = true)}>
        ${t("bans.add")}
      </button>
    </div>`;

    if (!this.bans.length) {
      return html`<ha-card class="empty">
          <ha-icon icon="mdi:shield-check-outline" aria-hidden="true"></ha-icon>
          <h3>${t("bans.empty_title")}</h3>
          <p>${t("bans.empty_body")}</p>
          <button class="primary" @click=${() => (this.adding = true)}>${t("bans.add")}</button>
        </ha-card>
        ${this.renderDialog()}`;
    }

    return html`<ha-card>
        ${toolbar}
        <div class="muted count">
          ${t("bans.count", { shown: rows.length, total: this.bans.length })}
        </div>
        ${rows.length
          ? html`<div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>
                      <input
                        type="checkbox"
                        .checked=${allSelected}
                        aria-label=${t("bans.select_all")}
                        @change=${(e: Event) => {
                          const on = (e.target as HTMLInputElement).checked;
                          this.selected = on ? new Set(rows.map((b) => b.ip)) : new Set();
                        }}
                      />
                    </th>
                    ${this.header("ip", t("bans.col_ip"))}
                    ${this.header("country", t("bans.col_country"), "hide-narrow")}
                    <th class="hide-narrow">${t("bans.col_reason")}</th>
                    ${this.header("source", t("bans.col_source"), "hide-narrow")}
                    ${this.header("created_at", t("bans.col_created"), "hide-narrow")}
                    ${this.header("expires_at", t("bans.col_expires"))}
                    <th><span class="sr-only">${t("bans.unban")}</span></th>
                  </tr>
                </thead>
                <tbody>
                  ${rows.map(
                    (ban) => html`<tr>
                      <td>
                        <input
                          type="checkbox"
                          .checked=${this.selected.has(ban.ip)}
                          aria-label=${t("bans.select_one", { ip: ban.ip })}
                          @change=${(e: Event) =>
                            this.toggle(ban.ip, (e.target as HTMLInputElement).checked)}
                        />
                      </td>
                      <td>
                        <button
                          class="link mono"
                          @click=${() => this.ctx.openDetails(ban.ip)}
                          aria-label=${t("common.details", { ip: ban.ip })}
                        >
                          ${ban.ip}
                        </button>
                      </td>
                      <td class="hide-narrow" title=${ban.city ?? ""}>
                        ${ban.country ? `${flag(ban.country)} ${ban.country}` : ""}
                      </td>
                      <td class="hide-narrow reason">${ban.reason}</td>
                      <td class="hide-narrow">
                        <span class="chip">${t(`bans.source_${ban.source}`)}</span>
                      </td>
                      <td class="hide-narrow">${formatDateTime(ban.created_at, language)}</td>
                      <td>${this.expiry(ban)}</td>
                      <td>
                        <button
                          class="icon"
                          @click=${() => this.unban([ban.ip])}
                          aria-label=${`${t("bans.unban")} ${ban.ip}`}
                          title=${t("bans.unban")}
                        >
                          <ha-icon icon="mdi:lock-open-variant-outline"></ha-icon>
                        </button>
                      </td>
                    </tr>`,
                  )}
                </tbody>
              </table>
            </div>`
          : html`<p class="muted empty">${t("bans.no_match")}</p>`}
      </ha-card>
      ${this.renderDialog()}`;
  }

  static override styles = [
    shared,
    css`
      .toolbar {
        margin-bottom: 8px;
      }
      .search {
        flex: 1 1 200px;
        width: auto;
      }
      select {
        width: auto;
      }
      .count {
        font-size: 0.8rem;
        margin-bottom: 4px;
      }
      .link {
        border: none;
        padding: 0;
        min-height: 0;
        border-radius: 0;
        text-align: start;
      }
      .reason {
        max-width: 240px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      textarea {
        resize: vertical;
      }
    `,
  ];
}
