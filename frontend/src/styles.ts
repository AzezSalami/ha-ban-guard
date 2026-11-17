import { css } from "lit";

// Shared styles. Only Home Assistant theme variables are used for colour so
// the panel follows light, dark and custom themes.
export const shared = css`
  :host {
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, inherit));
  }
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  ha-card,
  .card {
    display: block;
    background: var(--ha-card-background, var(--card-background-color, #fff));
    border-radius: var(--ha-card-border-radius, 12px);
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color));
    box-shadow: var(--ha-card-box-shadow, none);
    padding: 16px;
  }
  h2 {
    font-size: 1.1rem;
    font-weight: 500;
    margin: 0 0 12px;
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  .spacer {
    flex: 1;
  }
  button {
    font: inherit;
    cursor: pointer;
    border-radius: 18px;
    padding: 6px 14px;
    min-height: 36px;
    border: 1px solid var(--divider-color);
    background: transparent;
    color: var(--primary-color);
    font-weight: 500;
  }
  button.primary {
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
    border-color: var(--primary-color);
  }
  button.danger {
    color: var(--error-color);
    border-color: var(--error-color);
  }
  button.danger.primary {
    background: var(--error-color);
    color: var(--text-primary-color, #fff);
  }
  button.icon {
    border: none;
    padding: 6px;
    min-width: 36px;
    border-radius: 50%;
    color: var(--secondary-text-color);
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  button:focus-visible,
  input:focus-visible,
  select:focus-visible,
  textarea:focus-visible,
  [tabindex]:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }
  input,
  select,
  textarea {
    font: inherit;
    color: var(--primary-text-color);
    background: var(--input-fill-color, var(--secondary-background-color));
    border: 1px solid var(--input-idle-line-color, var(--divider-color));
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 40px;
    width: 100%;
  }
  label {
    display: block;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
    margin: 12px 0 4px;
  }
  .help {
    font-size: 0.8rem;
    color: var(--secondary-text-color);
    margin-top: 4px;
  }
  .error {
    color: var(--error-color);
    font-size: 0.85rem;
    margin-top: 4px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th,
  td {
    text-align: start;
    padding: 10px 8px;
    border-bottom: 1px solid var(--divider-color);
    vertical-align: middle;
  }
  th {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  th button {
    border: none;
    padding: 0;
    min-height: 0;
    color: inherit;
    font-weight: inherit;
    border-radius: 0;
  }
  tbody tr:hover {
    background: var(--secondary-background-color);
  }
  .mono {
    font-family: var(--ha-font-family-code, ui-monospace, monospace);
    font-size: 0.9em;
    word-break: break-all;
  }
  .chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75rem;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  .chip.warn {
    color: var(--warning-color);
  }
  .chip.bad {
    color: var(--error-color);
  }
  .chip.good {
    color: var(--success-color);
  }
  .empty {
    text-align: center;
    padding: 32px 16px;
  }
  .empty ha-icon {
    --mdc-icon-size: 48px;
    color: var(--secondary-text-color);
  }
  .empty h3 {
    margin: 8px 0;
    font-weight: 500;
  }
  .empty p {
    color: var(--secondary-text-color);
    max-width: 480px;
    margin: 0 auto 16px;
  }
  .banner {
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    border-inline-start: 4px solid var(--warning-color);
    background: var(--secondary-background-color);
  }
  .banner.bad {
    border-color: var(--error-color);
  }
  .table-wrap {
    overflow-x: auto;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  @media (max-width: 600px) {
    .hide-narrow {
      display: none;
    }
    th,
    td {
      padding: 8px 4px;
    }
  }
`;
