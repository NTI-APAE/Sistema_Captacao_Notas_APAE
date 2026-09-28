import type { Query, SearchParams } from "./types";

const keys = new Set([
  "q",
  "page",
  "consent_page",
  "size",
  "data_inicial",
  "data_final",
  "status",
  "cadastro",
  "telefone",
  "chave",
  "duplicada",
  "ativo",
  "comunicacao",
  "ligacao",
]);

export function cleanQuery(params: SearchParams): Query {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([key, value]) =>
        keys.has(key) && typeof value === "string" && value !== "",
    ),
  ) as Query;
}

export function pageHref(
  path: string,
  query: Query,
  page: number,
  key = "page",
): string {
  return `${path}?${new URLSearchParams({ ...query, [key]: String(page) })}`;
}

export function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    value,
  );
}
