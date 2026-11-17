import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { errorMessage } from "../api";
import type { Ctx } from "../context";
import { formatDateTime } from "../logic/format";
import { isAllowValue } from "../logic/ip";
import { shared } from "../styles";
import type { AllowEntry } from "../types";

@customElement("bg-allowlist")
export class BgAllowlist extends LitElement {
  @property({ attribute: false }) ctx!: Ctx;
  @property({ type: Number }) revision = 0;
  @property() requesterIp: string | null = null;
  @state() private entries: AllowEntry[] | null = null;
  @state() private adding = false;
  @state() private value = "";
  @state() private comment = "";
  @state() private formError = "";
  @state() private busy = false;

  protected override updated(changed: Map<string, unknown>): void {
    if (changed.has("revision") || changed.has("ctx")) void this.load();
  }

  private async load(): Promise<void> {
    try {
      this.entries = await this.ctx.api.allowlist();
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private openAdd(value = ""): void {
    this.value = value;
    this.comment = "";
    this.formError = "";
    this.adding = true;
  }

  private async submit(ev: Event): Promise<void> {
    ev.preventDefault();
    const { t } = this.ctx;
    const value = this.value.trim();
    if (!isAllowValue(value)) {
      this.formError = t("allowlist.invalid", { value });
      return;
    }
    this.busy = true;
    try {
      const entry = await this.ctx.api.allow(value, this.comment);
      this.adding = false;
      this.ctx.toast({
        message: t("allowlist.added", { value: entry.value }),
        actionLabel: t("common.undo"),
        action: async () => {
          try {
            await this.ctx.api.disallow(entry.value);
          } catch (err) {
            this.ctx.error(err);
          }
        },
      });
    } catch (err) {
      this.formError = errorMessage(err, t);
    } finally {
      this.busy = false;
    }
  }

  private async removeEntry(entry: AllowEntry): Promise<void> {
    const { t } = this.ctx;
    const ok = await this.ctx.confirm({
      title: t("allowlist.confirm_remove_title", { value: entry.value }),
      body: t("allowlist.confirm_remove_body"),
      confirm: t("allowlist.remove"),
      destructive: true,
    });
    if (!ok) return;
    try {
      await this.ctx.api.disallow(entry.value);
      this.ctx.toast({
        message: t("allowlist.removed", { value: entry.value }),
        actionLabel: t("common.undo"),
        action: async () => {
          try {
            await this.ctx.api.allow(entry.value, entry.comment);
          } catch (err) {
            this.ctx.error(err);
          }
        },
      });
    } catch (err) {
      this.ctx.error(err);
    }
  }

  private dialog() {
    const { t } = this.ctx;
    return html`<bg-dialog
      .open=${this.adding}
      .heading=${t("allowlist.add_title")}
      @closed=${() => (this.adding = false)}
    >
      <form id="allow-form" @submit=${this.submit}>
        <label for="value">${t("allowlist.value_label")}</label>
        <input
          id="value"
          required
          aria-describedby="value-help"
          .value=${this.value}
          @input=${(e: Event) => (this.value = (e.target as HTMLInputElement).value)}
        />
        <div class="help" id="value-help">${t("allowlist.value_help")}</div>
        <label for="comment">${t("allowlist.comment_label")}</label>
        <input
          id="comment"
          maxlength="200"
          .value=${this.comment}
          @input=${(e: Event) => (this.comment = (e.target as HTMLInputElement).value)}
        />
        ${this.formError ? html`<div class="error" role="alert">${this.formError}</div>` : nothing}
      </form>
      <button slot="actions" @click=${() => (this.adding = false)}>${t("common.cancel")}</button>
      <button slot="actions" class="primary" type="submit" form="allow-form" ?disabled=${this.busy}>
        ${t("allowlist.add")}
      </button>
    </bg-dialog>`;
  }

  protected override render() {
    const { t, language } = this.ctx;
    if (this.entries === null) return html`<p class="muted">${t("common.loading")}</p>`;
    if (!this.entries.length) {
      return html`<ha-card class="empty">
          <ha-icon icon="mdi:playlist-check" aria-hidden="true"></ha-icon>
          <h3>${t("allowlist.empty_title")}</h3>
          <p>${t("allowlist.empty_body", { ip: this.requesterIp ?? t("common.unknown") })}</p>
          <div class="row" style="justify-content:center">
            ${this.requesterIp
              ? html`<button @click=${() => this.openAdd(this.requesterIp ?? "")}>
                  ${t("allowlist.add_current")}
                </button>`
              : nothing}
            <button class="primary" @click=${() => this.openAdd()}>${t("allowlist.add")}</button>
          </div>
        </ha-card>
        ${this.dialog()}`;
    }
    return html`<ha-card>
        <div class="row toolbar">
          <span class="spacer"></span>
          <button class="primary" @click=${() => this.openAdd()}>${t("allowlist.add")}</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>${t("allowlist.col_value")}</th>
                <th>${t("allowlist.col_comment")}</th>
                <th class="hide-narrow">${t("allowlist.col_resolved")}</th>
                <th class="hide-narrow">${t("allowlist.col_added")}</th>
                <th><span class="sr-only">${t("allowlist.remove")}</span></th>
              </tr>
            </thead>
            <tbody>
              ${this.entries.map(
                (entry) => html`<tr>
                  <td class="mono">${entry.value}</td>
                  <td>${entry.comment}</td>
                  <td class="hide-narrow mono">
                    ${entry.hostname
                      ? entry.resolved.length
                        ? entry.resolved.join(", ")
                        : html`<span class="muted">${t("allowlist.unresolved")}</span>`
                      : ""}
                  </td>
                  <td class="hide-narrow">${formatDateTime(entry.created_at, language)}</td>
                  <td>
                    <button
                      class="icon"
                      @click=${() => this.removeEntry(entry)}
                      aria-label=${t("allowlist.remove_label", { value: entry.value })}
                      title=${t("allowlist.remove")}
                    >
                      <ha-icon icon="mdi:delete-outline"></ha-icon>
                    </button>
                  </td>
                </tr>`,
              )}
            </tbody>
          </table>
        </div>
      </ha-card>
      ${this.dialog()}`;
  }

  static override styles = [
    shared,
    css`
      .toolbar {
        margin-bottom: 8px;
      }
    `,
  ];
}
