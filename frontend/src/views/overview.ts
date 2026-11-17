import { LitElement, css, html, nothing, svg } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Ctx } from "../context";
import { flag, formatDateTime, scaleBars } from "../logic/format";
import { shared } from "../styles";
import type { Overview } from "../types";

@customElement("bg-overview")
export class BgOverview extends LitElement {
  @property({ attribute: false }) ctx!: Ctx;
  @property({ type: Number }) revision = 0;
  @state() private data: Overview | null = null;
  @state() private failed = false;

  protected override updated(changed: Map<string, unknown>): void {
    if (changed.has("revision") || changed.has("ctx")) void this.load();
  }

  private async load(): Promise<void> {
    try {
      this.data = await this.ctx.api.overview();
      this.failed = false;
    } catch (err) {
      this.failed = true;
      this.ctx.error(err);
    }
  }

  private card(label: string, value: number, icon: string, tab?: string) {
    const content = html`<ha-icon .icon=${icon} aria-hidden="true"></ha-icon>
      <div>
        <div class="value">${value}</div>
        <div class="muted">${label}</div>
      </div>`;
    return tab
      ? html`<button class="card stat" @click=${() => this.ctx.navigate(tab)}>${content}</button>`
      : html`<div class="card stat">${content}</div>`;
  }

  private chart(data: Overview) {
    const { t, language } = this.ctx;
    const series = data.failed_logins_7d;
    const { ratios } = scaleBars(series.map((d) => d.count));
    const width = 340;
    const height = 140;
    const barWidth = width / series.length;
    const day = new Intl.DateTimeFormat(language, { weekday: "short" });
    return html`<figure>
      <svg viewBox="0 0 ${width} ${height + 24}" role="img" aria-label=${t("overview.chart_title")}>
        <line x1="0" y1=${height} x2=${width} y2=${height} class="axis"></line>
        ${series.map((point, i) => {
          const h = Math.max((ratios[i] ?? 0) * height, point.count ? 2 : 0);
          const x = i * barWidth + barWidth * 0.2;
          const label = t("overview.chart_label", { date: point.date, count: point.count });
          return svg`<g>
            <title>${label}</title>
            <rect x=${x} y=${height - h} width=${barWidth * 0.6} height=${h} rx="3" class="bar"></rect>
            <text x=${x + barWidth * 0.3} y=${height + 16} class="tick">${day.format(new Date(`${point.date}T12:00:00`))}</text>
            ${point.count
              ? svg`<text x=${x + barWidth * 0.3} y=${height - h - 4} class="count">${point.count}</text>`
              : nothing}
          </g>`;
        })}
      </svg>
      <figcaption class="sr-only">
        ${series.map((p) => t("overview.chart_label", { date: p.date, count: p.count })).join(", ")}
      </figcaption>
    </figure>`;
  }

  protected override render() {
    const { t, language } = this.ctx;
    const d = this.data;
    if (!d) {
      return this.failed
        ? html`<div class="card empty">
            <button @click=${this.load}>${t("common.retry")}</button>
          </div>`
        : html`<p class="muted">${t("common.loading")}</p>`;
    }
    const geo = d.status.geoip.loaded;
    return html`
      <div class="stats">
        ${this.card(t("overview.active_bans"), d.active_bans, "mdi:shield-lock", "bans")}
        ${this.card(t("overview.bans_24h"), d.bans_24h, "mdi:shield-alert", "activity")}
        ${this.card(t("overview.failed_24h"), d.failed_logins_24h, "mdi:account-alert", "activity")}
        ${this.card(t("overview.blocked_24h"), d.blocked_24h, "mdi:cancel", "activity")}
        ${this.card(t("overview.allowlist"), d.allowlist, "mdi:playlist-check", "allowlist")}
      </div>
      <div class="grid">
        <ha-card class="chart">
          <h2>${t("overview.chart_title")}</h2>
          ${this.chart(d)}
        </ha-card>
        <ha-card>
          <h2>${t("overview.top_ips")}</h2>
          ${d.top_ips.length
            ? html`<ol class="list">
                ${d.top_ips.map(
                  (row) => html`<li>
                    <button
                      class="link mono"
                      @click=${() => this.ctx.openDetails(row.ip)}
                      aria-label=${t("common.details", { ip: row.ip })}
                    >
                      ${row.ip}
                    </button>
                    <span class="muted">${t("overview.attempts", { count: row.count })}</span>
                  </li>`,
                )}
              </ol>`
            : html`<p class="muted">${t("overview.no_offenders")}</p>`}
        </ha-card>
        <ha-card>
          <h2>${t("overview.top_countries")}</h2>
          ${!geo
            ? html`<p class="muted">${t("overview.countries_need_geoip")}</p>`
            : d.top_countries.length
              ? html`<ol class="list">
                  ${d.top_countries.map(
                    (row) => html`<li>
                      <span>${flag(row.country)} ${row.country}</span>
                      <span class="muted">${t("overview.attempts", { count: row.count })}</span>
                    </li>`,
                  )}
                </ol>`
              : html`<p class="muted">${t("overview.no_offenders")}</p>`}
          ${d.last_ban
            ? html`<h2 class="last">${t("overview.last_ban")}</h2>
                <button class="link mono" @click=${() => this.ctx.openDetails(d.last_ban?.ip ?? "")}>
                  ${flag(d.last_ban.country)} ${d.last_ban.ip}
                </button>
                <div class="muted">
                  ${formatDateTime(d.last_ban.created_at, language)} · ${d.last_ban.reason}
                </div>`
            : nothing}
        </ha-card>
      </div>
    `;
  }

  static override styles = [
    shared,
    css`
      .stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin-bottom: 12px;
      }
      .stat {
        display: flex;
        gap: 12px;
        align-items: center;
        text-align: start;
        width: 100%;
        color: inherit;
        font-weight: normal;
        border-radius: var(--ha-card-border-radius, 12px);
      }
      .stat ha-icon {
        color: var(--primary-color);
        --mdc-icon-size: 32px;
      }
      .value {
        font-size: 1.8rem;
        font-weight: 500;
        line-height: 1.1;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 12px;
      }
      figure {
        margin: 0;
      }
      svg {
        width: 100%;
        height: auto;
      }
      .bar {
        fill: var(--primary-color);
      }
      .axis {
        stroke: var(--divider-color);
      }
      .tick,
      .count {
        font-size: 10px;
        text-anchor: middle;
        fill: var(--secondary-text-color);
      }
      .list {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .list li {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 6px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .link {
        border: none;
        padding: 0;
        min-height: 0;
        border-radius: 0;
        text-align: start;
      }
      .last {
        margin-top: 16px;
      }
    `,
  ];
}
