import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { errorMessage } from "../api";
import type { Ctx } from "../context";
import { shared } from "../styles";
import type { Settings } from "../types";

@customElement("bg-settings")
export class BgSettings extends LitElement {
  @property({ attribute: false }) ctx!: Ctx;
  @property({ attribute: false }) settings: Settings | null = null;
  @state() private syncing = false;

  private openOptions(): void {
    // The integration page hosts the options flow ("Configure").
    history.pushState(null, "", "/config/integrations/integration/ban_guard");
    window.dispatchEvent(new CustomEvent("location-changed"));
  }

  private async sync(): Promise<void> {
    const { t } = this.ctx;
    this.syncing = true;
    try {
      const status = await this.ctx.api.npmSync();
      this.ctx.toast({
        message: status.ok
          ? t("settings.npm_synced", { count: status.count ?? 0 })
          : t("settings.npm_failed", { error: status.error ?? "?" }),
      });
    } catch (err) {
      this.ctx.toast({ message: errorMessage(err, t) });
    } finally {
      this.syncing = false;
    }
  }

  private item(label: string, value: unknown) {
    return html`<div class="item">
      <dt>${label}</dt>
      <dd>${value}</dd>
    </div>`;
  }

  protected override render() {
    const { t } = this.ctx;
    const s = this.settings;
    if (!s) return html`<p class="muted">${t("common.loading")}</p>`;
    const o = s.options;
    const onOff = (v: unknown) => (v ? t("settings.on") : t("settings.off"));
    const geo = s.status.geoip;
    const outbound: string[] = [];
    if (geo.enabled) outbound.push("download.db-ip.com (GeoIP)");
    if (s.status.rdns && !s.status.doh) outbound.push(t("settings.rdns"));
    if (s.status.doh) outbound.push(String(o["doh_url"] ?? ""));
    if (s.status.npm.enabled) outbound.push(String(o["npm_url"] ?? ""));
    return html`<ha-card>
      <p class="muted">${t("settings.intro")}</p>
      ${s.requester_ip
        ? html`<p><ha-icon icon="mdi:account-lock"></ha-icon>
            ${t("settings.your_ip", { ip: s.requester_ip })}</p>`
        : nothing}
      <dl>
        ${this.item(
          t("settings.protection"),
          o["protection_enabled"]
            ? t("settings.protection_value", {
                threshold: String(o["threshold"]),
                window: String(o["window_minutes"]),
                ladder: String(o["escalation"]),
              })
            : t("settings.off"),
        )}
        ${this.item(t("settings.notifications"), onOff(o["notify_persistent"]))}
        ${this.item(
          t("settings.logging"),
          t("settings.logging_value", {
            days: String(o["log_retention_days"]),
            entries: String(o["log_max_entries"]),
          }),
        )}
        ${this.item(
          t("settings.geoip"),
          !geo.enabled
            ? t("settings.off")
            : geo.error
              ? t("settings.geoip_error", { error: geo.error })
              : geo.loaded
                ? t("settings.geoip_loaded", { edition: geo.edition })
                : t("settings.geoip_loading"),
        )}
        ${this.item(t("settings.rdns"), onOff(s.status.rdns))}
        ${this.item(t("settings.doh"), onOff(s.status.doh))}
        ${this.item(
          t("settings.countries"),
          t("settings.countries_value", {
            allow: s.status.country_rules.allow.join(", ") || t("common.none"),
            deny: s.status.country_rules.deny.join(", ") || t("common.none"),
          }),
        )}
        ${this.item(t("settings.npm"), onOff(s.status.npm.enabled))}
      </dl>
      ${s.npm_addon
        ? html`<p class="muted">${t("settings.npm_detected", { name: s.npm_addon.name })}</p>`
        : nothing}
      <h2>${t("settings.privacy")}</h2>
      ${outbound.length
        ? html`<ul>
            ${outbound.map((o) => html`<li class="mono">${o}</li>`)}
          </ul>`
        : html`<p class="muted">${t("settings.privacy_none")}</p>`}
      <div class="row">
        <button class="primary" @click=${this.openOptions}>
          <ha-icon icon="mdi:cog"></ha-icon> ${t("settings.open_options")}
        </button>
        ${s.status.npm.enabled
          ? html`<button ?disabled=${this.syncing} @click=${this.sync}>
              ${t("settings.npm_sync")}
            </button>`
          : nothing}
      </div>
    </ha-card>`;
  }

  static override styles = [
    shared,
    css`
      dl {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 12px;
        margin: 16px 0;
      }
      .item {
        padding: 12px;
        border-radius: 8px;
        background: var(--secondary-background-color);
      }
      dt {
        font-size: 0.8rem;
        color: var(--secondary-text-color);
      }
      dd {
        margin: 4px 0 0;
      }
      button ha-icon {
        --mdc-icon-size: 18px;
      }
    `,
  ];
}
