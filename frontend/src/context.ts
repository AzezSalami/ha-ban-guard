import type { Api } from "./api";
import type { ConfirmOptions } from "./components/dialog";
import type { ToastOptions } from "./components/toast";
import type { Translate } from "./logic/i18n";
import type { Hass } from "./types";

/** Everything a view needs from the panel shell. */
export interface Ctx {
  hass: Hass;
  api: Api;
  t: Translate;
  language: string;
  confirm(
    options: Omit<ConfirmOptions, "confirm" | "cancel"> & { confirm?: string; cancel?: string },
  ): Promise<boolean>;
  toast(options: ToastOptions): void;
  error(err: unknown): void;
  openDetails(ip: string): void;
  navigate(tab: string): void;
}
