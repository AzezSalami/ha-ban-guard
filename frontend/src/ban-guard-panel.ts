import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import { Api, errorMessage } from "./api";
import "./components/dialog";
import type { BgConfirm } from "./components/dialog";
import "./components/drawer";
import "./components/toast";
import type { BgToast } from "./components/toast";
import type { Ctx } from "./context";
import { type Translate, translator } from "./logic/i18n";
import { shared } from "./styles";
import type { Hass, Settings } from "./types";
import "./views/activity";
import "./views/allowlist";
import "./views/backup";
import "./views/bans";
import "./views/overview";
import "./views/sessions";
import "./views/settings";

const TABS = [
  { id: "overview", icon: "mdi:view-dashboard-outline" },
  { id: "bans", icon: "mdi:shield-lock-outline" },
  { id: "allowlist", icon: "mdi:playlist-check" },
  { id: "activity", icon: "mdi:timeline-clock-outline" },
  { id: "sessions", icon: "mdi:devices" },
  { id: "settings", icon: "mdi:cog-outline" },
  { id: "backup", icon: "mdi:swap-vertical" },
] as const;
type TabId = (typeof TABS)[number]["id"];

@customElement("ban-guard-panel")
export class BanGuardPanel extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ type: Boolean }) narrow = false;
  @state() private tab: TabId = "overview";
  @state() private revision = 0;
  @state() private details: string | null = null;
  @state() private settings: Settings | null = null;
  @query("bg-confirm") private confirmEl!: BgConfirm;
  @query("bg-toast") private toastEl!: BgToast;

  private api: Api | null = null;
  private ctx: Ctx | null = null;
  private language = "";
  private unsub: (() => Promise<void>) | null = null;
  private refreshTimer: number | undefined;

  override connectedCallback(): void {
    super.connectedCallback();
    const fromHash = location.hash.slice(1) as TabId;
    if (TABS.some((tab) => tab.id === fromHash)) this.tab = fromHash;
    if (this.hass) void this.subscribe();
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    void this.unsub?.();
    this.unsub = null;
    window.clearTimeout(this.refreshTimer);
  }

  protected override willUpdate(changed: Map<string, unknown>): void {
    if (!changed.has("hass") || !this.hass) return;
    const language = this.hass.locale?.language ?? this.hass.language ?? "en";
    const firstTime = this.api === null;
    if (firstTime || language !== this.language) {
      this.language = language;
      this.api ??= new Api(this.hass);
      this.ctx = this.makeCtx(this.api, translator(language));
    }
    if (firstTime) {
      void this.subscribe();
      void this.loadSettings();
    }
  }

  private makeCtx(api: Api, t: Translate): Ctx {
    return {
      hass: this.hass,
      api,
      t,
      language: this.language,
      confirm: (o) =>
        this.confirmEl.ask({
          ...o,
          confirm: o.confirm ?? t("common.confirm"),
          cancel: o.cancel ?? t("common.cancel"),
        }),
      toast: (o) => this.toastEl.show(o),
      error: (err) => this.toastEl.show({ message: errorMessage(err, t) }),
      openDetails: (ip) => (this.details = ip),
      navigate: (tab) => this.select(tab as TabId),
    };
  }

  private async subscribe(): Promise<void> {
    if (this.unsub || !this.api) return;
    try {
      this.unsub = await this.api.subscribeUpdates(() => this.scheduleRefresh());
    } catch {
      // Not fatal: views still load on demand.
    }
  }

  /** Coalesce bursts of updates (e.g. during an attack) into one refresh. */
  private scheduleRefresh(): void {
    if (this.refreshTimer !== undefined) return;
    this.refreshTimer = window.setTimeout(() => {
      this.refreshTimer = undefined;
      this.revision += 1;
    }, 750);
  }

  private async loadSettings(): Promise<void> {
    try {
      if (this.api) this.settings = await this.api.settings();
    } catch (err) {
      this.ctx?.error(err);
    }
  }

  private select(tab: TabId): void {
    this.tab = tab;
    history.replaceState(null, "", `#${tab}`);
    if (tab === "settings") void this.loadSettings();
  }

  private onTabKey(ev: KeyboardEvent): void {
    const index = TABS.findIndex((tab) => tab.id === this.tab);
    let next: number;
    if (ev.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (ev.key === "ArrowLeft") next = (index - 1 + TABS.length) % TABS.length;
    else if (ev.key === "Home") next = 0;
    else if (ev.key === "End") next = TABS.length - 1;
    else return;
    ev.preventDefault();
    const target = TABS[next]?.id ?? "overview";
    this.select(target);
    void this.updateComplete.then(() =>
      this.renderRoot.querySelector<HTMLElement>(`#tab-${target}`)?.focus(),
    );
  }

  private banners() {
    const status = this.settings?.status;
    if (!status || !this.ctx) return nothing;
    const t = this.ctx.t;
    const items = [];
    if (status.hook !== "active") {
      const key = ["incompatible", "ip_ban_disabled", "error"].includes(status.hook)
        ? `status.hook_${status.hook}`
        : "status.hook_other";
      items.push(html`<div class="banner bad" role="alert">${t(key, { status: status.hook })}</div>`);
    }
    if (status.under_attack) {
      items.push(html`<div class="banner bad" role="alert">${t("status.under_attack")}</div>`);
    }
    if (!status.protection_enabled) {
      items.push(html`<div class="banner">${t("status.protection_off")}</div>`);
    }
    return items;
  }

  private view() {
    const ctx = this.ctx;
    if (!ctx) return nothing;
    switch (this.tab) {
      case "overview":
        return html`<bg-overview .ctx=${ctx} .revision=${this.revision}></bg-overview>`;
      case "bans":
        return html`<bg-bans .ctx=${ctx} .revision=${this.revision}></bg-bans>`;
      case "allowlist":
        return html`<bg-allowlist
          .ctx=${ctx}
          .revision=${this.revision}
          .requesterIp=${this.settings?.requester_ip ?? null}
        ></bg-allowlist>`;
      case "activity":
        return html`<bg-activity .ctx=${ctx}></bg-activity>`;
      case "sessions":
        return html`<bg-sessions .ctx=${ctx} .revision=${this.revision}></bg-sessions>`;
      case "settings":
        return html`<bg-settings .ctx=${ctx} .settings=${this.settings}></bg-settings>`;
      case "backup":
        return html`<bg-backup .ctx=${ctx}></bg-backup>`;
    }
  }

  protected override render() {
    if (!this.ctx) return nothing;
    const t = this.ctx.t;
    return html`
      <header class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <h1>${t("title")}</h1>
      </header>
      <nav role="tablist" aria-label=${t("title")} @keydown=${this.onTabKey}>
        ${TABS.map(
          (tab) => html`<button
            role="tab"
            id="tab-${tab.id}"
            aria-selected=${this.tab === tab.id}
            aria-controls="panel"
            tabindex=${this.tab === tab.id ? 0 : -1}
            @click=${() => this.select(tab.id)}
          >
            <ha-icon .icon=${tab.icon} aria-hidden="true"></ha-icon>
            <span>${t(`tabs.${tab.id}`)}</span>
          </button>`,
        )}
      </nav>
      <main id="panel" role="tabpanel" aria-labelledby="tab-${this.tab}">
        ${this.banners()} ${this.view()}
      </main>
      <bg-drawer
        .ctx=${this.ctx}
        .ip=${this.details}
        .revision=${this.revision}
        @closed=${() => (this.details = null)}
      ></bg-drawer>
      <bg-confirm></bg-confirm>
      <bg-toast></bg-toast>
    `;
  }

  static override styles = [
    shared,
    css`
      :host {
        display: block;
        min-height: 100vh;
        background: var(--primary-background-color);
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        height: var(--header-height, 56px);
        padding: 0 12px;
        background: var(--app-header-background-color, var(--primary-background-color));
        color: var(--app-header-text-color, var(--primary-text-color));
        border-bottom: var(--app-header-border-bottom, 1px solid var(--divider-color));
      }
      h1 {
        font-size: 1.25rem;
        font-weight: 400;
        margin: 0;
      }
      nav {
        display: flex;
        gap: 4px;
        overflow-x: auto;
        padding: 8px 12px 0;
        border-bottom: 1px solid var(--divider-color);
        scrollbar-width: none;
      }
      nav button {
        display: flex;
        align-items: center;
        gap: 6px;
        border: none;
        border-radius: 0;
        border-bottom: 2px solid transparent;
        color: var(--secondary-text-color);
        padding: 8px 12px;
        white-space: nowrap;
      }
      nav button[aria-selected="true"] {
        color: var(--primary-color);
        border-bottom-color: var(--primary-color);
      }
      nav ha-icon {
        --mdc-icon-size: 20px;
      }
      main {
        padding: 16px;
        max-width: 1200px;
        margin: 0 auto;
      }
      @media (max-width: 600px) {
        main {
          padding: 8px;
        }
        nav span {
          display: none;
        }
        nav button[aria-selected="true"] span {
          display: inline;
        }
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "ban-guard-panel": BanGuardPanel;
  }
}
