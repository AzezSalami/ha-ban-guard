import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { errorMessage } from "../api";
import type { Ctx } from "../context";
import { downloadName } from "../logic/format";
import { parseBackupText } from "../logic/backup";
import { shared } from "../styles";
import type { ImportPreview } from "../types";

@customElement("bg-backup")
export class BgBackup extends LitElement {
  @property({ attribute: false }) ctx!: Ctx;
  @state() private data: unknown = null;
  @state() private preview: ImportPreview | null = null;
  @state() private includeSettings = false;
  @state() private error = "";
  @state() private busy = false;

  private async exportBackup(): Promise<void> {
    try {
      const backup = await this.ctx.api.exportBackup();
      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = downloadName("ban_guard", new Date());
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private async onFile(ev: Event): Promise<void> {
    const { t } = this.ctx;
    const file = (ev.target as HTMLInputElement).files?.[0];
    this.preview = null;
    this.error = "";
    if (!file) return;
    const parsed = parseBackupText(await file.text());
    if (!parsed.ok) {
      this.error = t(`backup.${parsed.error}`);
      return;
    }
    this.data = parsed.data;
    try {
      this.preview = (await this.ctx.api.importBackup(parsed.data, true, false)).preview;
    } catch (err) {
      this.error = errorMessage(err, t);
    }
  }

  private async apply(): Promise<void> {
    const { t } = this.ctx;
    this.busy = true;
    try {
      await this.ctx.api.importBackup(this.data, false, this.includeSettings);
      this.ctx.toast({ message: t("backup.applied") });
      this.preview = null;
      this.data = null;
    } catch (err) {
      this.error = errorMessage(err, t);
    } finally {
      this.busy = false;
    }
  }

  private renderPreview(p: ImportPreview) {
    const { t } = this.ctx;
    const settingsCount = Object.keys(p.settings).length;
    const nothingToDo =
      !p.bans_new.length && !p.allow_new.length && !(this.includeSettings && settingsCount);
    return html`<section aria-labelledby="preview-h" class="preview">
      <h2 id="preview-h">${t("backup.preview_title")}</h2>
      <ul>
        <li>${t("backup.new_bans", { count: p.bans_new.length })}</li>
        <li class="muted">${t("backup.existing_bans", { count: p.bans_existing.length })}</li>
        <li class="muted">${t("backup.expired_bans", { count: p.bans_expired.length })}</li>
        <li>${t("backup.new_allow", { count: p.allow_new.length })}</li>
        <li class="muted">${t("backup.existing_allow", { count: p.allow_existing.length })}</li>
        <li>${t("backup.settings_changes", { count: settingsCount })}</li>
        ${p.errors.length
          ? html`<li class="error">${t("backup.errors", { count: p.errors.length })}
              <ul>
                ${p.errors.slice(0, 20).map(
                  (e) =>
                    html`<li>${e.section} #${e.index ?? "-"}: ${t(`errors.${e.error}`, Object.fromEntries(Object.entries(e).map(([k, v]) => [k, String(v)])))}</li>`,
                )}
              </ul>
            </li>`
          : nothing}
      </ul>
      ${settingsCount
        ? html`<label class="check">
            <input
              type="checkbox"
              .checked=${this.includeSettings}
              @change=${(e: Event) =>
                (this.includeSettings = (e.target as HTMLInputElement).checked)}
            />
            ${t("backup.include_settings")}
          </label>`
        : nothing}
      <div class="row">
        <button class="primary" ?disabled=${this.busy || nothingToDo} @click=${this.apply}>
          ${t("backup.apply")}
        </button>
        ${nothingToDo ? html`<span class="muted">${t("backup.nothing")}</span>` : nothing}
      </div>
    </section>`;
  }

  protected override render() {
    const { t } = this.ctx;
    return html`<div class="grid">
      <ha-card>
        <h2>${t("backup.export_title")}</h2>
        <p class="muted">${t("backup.export_body")}</p>
        <button class="primary" @click=${this.exportBackup}>
          <ha-icon icon="mdi:download"></ha-icon> ${t("backup.export")}
        </button>
      </ha-card>
      <ha-card>
        <h2>${t("backup.import_title")}</h2>
        <p class="muted">${t("backup.import_body")}</p>
        <label for="file">${t("backup.choose_file")}</label>
        <input id="file" type="file" accept="application/json,.json" @change=${this.onFile} />
        ${this.error ? html`<div class="error" role="alert">${this.error}</div>` : nothing}
        ${this.preview ? this.renderPreview(this.preview) : nothing}
      </ha-card>
    </div>`;
  }

  static override styles = [
    shared,
    css`
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 12px;
      }
      .check {
        display: flex;
        gap: 8px;
        align-items: center;
        color: var(--primary-text-color);
      }
      .check input {
        width: auto;
        min-height: 0;
      }
      button ha-icon {
        --mdc-icon-size: 18px;
      }
      .preview {
        margin-top: 16px;
      }
    `,
  ];
}
