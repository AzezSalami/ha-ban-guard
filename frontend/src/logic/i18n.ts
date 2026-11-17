// Tiny translation lookup. Add a language by adding src/translations/<lang>.json
// and registering it in TRANSLATIONS below.
import en from "../translations/en.json";

type Tree = { [key: string]: string | Tree };

export const TRANSLATIONS: Record<string, Tree> = { en };

function lookup(tree: Tree, key: string): string | undefined {
  let node: string | Tree | undefined = tree;
  for (const part of key.split(".")) {
    if (node === undefined || typeof node === "string") return undefined;
    node = node[part];
  }
  return typeof node === "string" ? node : undefined;
}

export function resolveLanguage(language: string | undefined): string {
  if (!language) return "en";
  if (language in TRANSLATIONS) return language;
  const base = language.split("-")[0] ?? "en";
  return base in TRANSLATIONS ? base : "en";
}

export type Translate = (key: string, params?: Record<string, string | number>) => string;

export function translator(language: string | undefined): Translate {
  const tree = TRANSLATIONS[resolveLanguage(language)] ?? en;
  return (key, params) => {
    const template = lookup(tree, key) ?? lookup(en, key) ?? key;
    if (!params) return template;
    return template.replace(/\{(\w+)\}/g, (match, name: string) =>
      name in params ? String(params[name]) : match,
    );
  };
}
