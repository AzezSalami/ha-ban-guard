import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import { shared } from "../styles";

/**
 * Accessible modal built on the native <dialog> element: focus is trapped by
 * the browser, Escape closes it, and focus returns to the opener.
 */
@customElement("bg-dialog")
export class BgDialog extends LitElement {
  @property() heading = "";
  @property({ type: Boolean }) open = false;
  @query("dialog") private dialog!: HTMLDialogElement;

  private opener: Element | null = null;

  protected override updated(changed: Map<string, unknown>): void {
    if (!changed.has("open")) return;
    if (this.open && !this.dialog.open) {
      this.opener = document.activeElement;
      this.dialog.showModal();
    } else if (!this.open && this.dialog.open) {
      this.dialog.close();
    }
  }

  private onClose(): void {
    if (this.open) {
      this.open = false;
      this.dispatchEvent(new CustomEvent("closed"));
    }
    (this.opener as HTMLElement | null)?.focus?.();
  }

  protected override render() {
    return html`<dialog aria-labelledby="h" @close=${this.onClose}>
      <h2 id="h">${this.heading}</h2>
      <div class="body"><slot></slot></div>
      <div class="actions"><slot name="actions"></slot></div>
    </dialog>`;
  }

  static override styles = [
    shared,
    css`
      dialog {
        border: none;
        border-radius: var(--ha-dialog-border-radius, 24px);
        padding: 24px;
        width: min(560px, calc(100vw - 32px));
        max-height: calc(100vh - 32px);
        background: var(--mdc-theme-surface, var(--card-background-color));
        color: var(--primary-text-color);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      }
      dialog::backdrop {
        background: rgba(0, 0, 0, 0.4);
      }
      .actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 24px;
        flex-wrap: wrap;
      }
    `,
  ];
}

export interface ConfirmOptions {
  title: string;
  body: string;
  confirm: string;
  cancel: string;
  destructive?: boolean;
}

/** Promise-based confirmation dialog for destructive actions. */
@customElement("bg-confirm")
export class BgConfirm extends LitElement {
  @property({ attribute: false }) options: ConfirmOptions | null = null;
  private resolve: ((value: boolean) => void) | null = null;

  ask(options: ConfirmOptions): Promise<boolean> {
    this.resolve?.(false);
    this.options = options;
    return new Promise((resolve) => {
      this.resolve = resolve;
    });
  }

  private finish(value: boolean): void {
    this.resolve?.(value);
    this.resolve = null;
    this.options = null;
  }

  protected override render() {
    const o = this.options;
    return html`<bg-dialog
      .open=${o !== null}
      .heading=${o?.title ?? ""}
      @closed=${() => this.finish(false)}
    >
      ${o ? html`<p>${o.body}</p>` : nothing}
      <button slot="actions" @click=${() => this.finish(false)}>${o?.cancel}</button>
      <button
        slot="actions"
        class=${o?.destructive ? "danger primary" : "primary"}
        @click=${() => this.finish(true)}
      >
        ${o?.confirm}
      </button>
    </bg-dialog>`;
  }

  static override styles = [shared];
}
