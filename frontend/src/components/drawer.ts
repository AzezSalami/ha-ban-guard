import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import type { Ctx } from "../context";
import { describeEnforcement } from "../logic/enforcement";
import { flag, formatDateTime } from "../logic/format";
import { shared } from "../styles";
import type { History } from "../types";

/** Side sheet with everything known about one address. */
@customElement("bg-drawer")
export class BgDrawer extends LitElement {
  @property({ attribute: false }) ctx!: Ctx;
  @property() ip: string | null = null;
  @property({ type: Number }) revision = 0;
  @state() private data: History | null = null;
  @query("dialog") private dialog!: HTMLDialogElement;

  protected override updated(changed: Map<string, unknown>): void {
    if (changed.has("ip")) {
      this.data = null;
      if (this.ip) {
        if (!this.dialog.open) this.dialog.showModal();
        void this.load();
      } else if (this.dialog.open) {
        this.dialog.close();
      }
    } else if (changed.has("revision") && this.ip) {
      void this.load();
    }
  }

  private async load(): Promise<void> {
    if (!this.ip) return;
    try {
      this.data = await this.ctx.api.history(this.ip);
    } catch (err) {
      this.ctx.error(err);
      this.close();
    }
  }

  private close(): void {
    this.ip = null;
    this.dispatchEvent(new CustomEvent("closed"));
  }

  private async unban(allowlist: boolean): Promise<void> {
    const { t } = this.ctx;
    const ip = this.data?.ip;
    if (!ip) return;
    const ok = await this.ctx.confirm({
      title: t("bans.confirm_unban_title", { count: 1 }),
      body: t("bans.confirm_unban_body", { list: ip }),
      confirm: allowlist ? t("drawer.allowlist_it") : t("bans.unban"),
      destructive: true,
    });
    if (!ok) return;
    try {
      const removed = await this.ctx.api.unban([ip]);
      if (allowlist) await this.ctx.api.allow(ip, "");
      this.ctx.toast({
        message: t("bans.unbanned", { count: 1 }),
        actionLabel: t("common.undo"),
        action: async () => {
          try {
            if (allowlist) await this.ctx.api.disallow(ip);
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

  protected override render() {
    const { t, language } = this.ctx;
    const d = this.data;
    return html`<dialog aria-labelledby="dh" @close=${() => this.ip && this.close()}>
      <header class="row">
        <h2 id="dh" class="mono">${this.ip ?? ""}</h2>
        <span class="spacer"></span>
        <button class="icon" @click=${this.close} aria-label=${t("common.close")}>
          <ha-icon icon="mdi:close"></ha-icon>
        </button>
      </header>
      ${!d
        ? html`<p class="muted">${t("common.loading")}</p>`
        : html`<dl>
              <dt>${t("drawer.location")}</dt>
              <dd>
                ${d.geo
                  ? `${flag(d.geo.country)} ${[d.geo.city, d.geo.country_name ?? d.geo.country]
                      .filter(Boolean)
                      .join(", ")}`
                  : t("common.unknown")}
              </dd>
              <dt>${t("drawer.hostname")}</dt>
              <dd class="mono">${d.hostname ?? t("drawer.rdns_off")}</dd>
              <dt>${t("drawer.offenses")}</dt>
              <dd>${d.offenses}</dd>
              <dt>${t("drawer.allowlisted")}</dt>
              <dd>${d.allowlisted ? t("common.yes") : t("common.no")}</dd>
              <dt>${t("drawer.ban")}</dt>
              <dd>
                ${d.ban
                  ? html`${d.ban.reason || t(`bans.source_${d.ban.source}`)} ·
                    ${d.ban.expires_at
                      ? formatDateTime(d.ban.expires_at, language)
                      : t("common.permanent")}`
                  : t("common.none")}
              </dd>
              ${d.ban && describeEnforcement(d.ban.enforcement, t).level !== "ok"
                ? html`<dt>${t("drawer.enforcement")}</dt>
                    <dd class="warn-text">
                      ${describeEnforcement(d.ban.enforcement, t).label}:
                      ${describeEnforcement(d.ban.enforcement, t).detail}
                    </dd>`
                : nothing}
            </dl>
            ${d.ban
              ? html`<div class="row">
                  <button class="danger" @click=${() => this.unban(false)}>
                    ${t("bans.unban")}
                  </button>
                  <button @click=${() => this.unban(true)}>${t("drawer.allowlist_it")}</button>
                </div>`
              : nothing}
            <h2 class="history">${t("drawer.history")}</h2>
            ${d.activity.length
              ? html`<ol class="timeline">
                  ${d.activity.map(
                    (e) => html`<li>
                      <span class="chip">${t(`activity.types.${e.type}`)}</span>
                      <span class="muted">${formatDateTime(e.ts, language)}</span>
                      ${e.path ? html`<div class="mono small">${e.path}</div>` : nothing}
                      ${e.detail ? html`<div class="small">${e.detail}</div>` : nothing}
                    </li>`,
                  )}
                </ol>`
              : html`<p class="muted">${t("drawer.no_history")}</p>`}`}
    </dialog>`;
  }

  static override styles = [
    shared,
    css`
      dialog {
        margin: 0 0 0 auto;
        height: 100vh;
        max-height: 100vh;
        width: min(440px, 100vw);
        border: none;
        padding: 16px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        box-shadow: -4px 0 24px rgba(0, 0, 0, 0.25);
      }
      dialog::backdrop {
        background: rgba(0, 0, 0, 0.3);
      }
      h2 {
        margin: 0;
      }
      dl {
        display: grid;
        grid-template-columns: max-content 1fr;
        gap: 8px 16px;
        margin: 16px 0;
      }
      dt {
        color: var(--secondary-text-color);
      }
      dd {
        margin: 0;
      }
      .history {
        margin-top: 24px;
      }
      .warn-text {
        color: var(--warning-color);
      }
      .timeline {
        list-style: none;
        padding: 0;
        margin: 8px 0 0;
      }
      .timeline li {
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .small {
        font-size: 0.8rem;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
    `,
  ];
}
