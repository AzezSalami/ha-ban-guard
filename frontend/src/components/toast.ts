import { LitElement, css, html, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { shared } from "../styles";

export interface ToastOptions {
  message: string;
  actionLabel?: string;
  action?: () => void | Promise<void>;
  duration?: number;
}

/** A single polite live-region toast with an optional Undo action. */
@customElement("bg-toast")
export class BgToast extends LitElement {
  @state() private current: ToastOptions | null = null;
  private timer: number | undefined;

  show(options: ToastOptions): void {
    window.clearTimeout(this.timer);
    this.current = options;
    this.timer = window.setTimeout(() => this.dismiss(), options.duration ?? 8000);
  }

  dismiss(): void {
    window.clearTimeout(this.timer);
    this.current = null;
  }

  private async run(): Promise<void> {
    const action = this.current?.action;
    this.dismiss();
    await action?.();
  }

  protected override render() {
    const c = this.current;
    return html`<div class="region" role="status" aria-live="polite">
      ${c
        ? html`<div class="toast">
            <span>${c.message}</span>
            ${c.actionLabel
              ? html`<button class="action" @click=${this.run}>${c.actionLabel}</button>`
              : nothing}
          </div>`
        : nothing}
    </div>`;
  }

  static override styles = [
    shared,
    css`
      .region {
        position: fixed;
        inset-inline: 0;
        bottom: 16px;
        display: flex;
        justify-content: center;
        pointer-events: none;
        z-index: 10;
      }
      .toast {
        pointer-events: auto;
        display: flex;
        align-items: center;
        gap: 16px;
        max-width: calc(100vw - 32px);
        padding: 8px 8px 8px 16px;
        border-radius: 8px;
        background: var(--sidebar-background-color, #323232);
        color: var(--sidebar-text-color, #fff);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
      }
      .action {
        border: none;
        color: var(--primary-color);
      }
    `,
  ];
}
