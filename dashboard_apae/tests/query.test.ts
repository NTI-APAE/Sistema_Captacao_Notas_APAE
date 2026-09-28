import { strict as assert } from "node:assert";
import { test } from "node:test";
import { cleanQuery, isUuid, pageHref } from "../src/lib/query";
import { dateTime, money } from "../src/lib/format";

test("mantém somente filtros conhecidos e valores únicos", () => {
  assert.deepEqual(
    cleanQuery({
      q: "Ana",
      page: "2",
      status: "",
      token: "segredo",
      size: ["1", "2"],
    }),
    { q: "Ana", page: "2" },
  );
});
test("paginação preserva filtros e codifica pesquisa", () => {
  const href = pageHref(
    "/dashboard/notas",
    { q: "Ana & Bia", status: "DUPLICADA" },
    2,
  );
  const url = new URL(href, "http://localhost");
  assert.equal(url.searchParams.get("q"), "Ana & Bia");
  assert.equal(url.searchParams.get("status"), "DUPLICADA");
  assert.equal(url.searchParams.get("page"), "2");
});
test("históricos têm paginação independente", () => {
  const href = pageHref(
    "/dashboard/contatos/id",
    { page: "3", consent_page: "1" },
    2,
    "consent_page",
  );
  assert.equal(new URL(href, "http://localhost").searchParams.get("page"), "3");
  assert.equal(
    new URL(href, "http://localhost").searchParams.get("consent_page"),
    "2",
  );
});
test("aceita apenas UUIDs nas rotas de detalhes", () => {
  assert.equal(isUuid("72c84b19-b727-4cba-9b39-2e772b6d66c8"), true);
  assert.equal(isUuid("../../worker"), false);
});
test("data fiscal não recua um dia; timestamp usa Brasília", () => {
  assert.equal(dateTime("2026-09-28"), "28/09/2026");
  assert.match(dateTime("2026-09-28T02:59:00Z"), /27\/09\/2026.*23:59/);
  assert.equal(dateTime(null), "Não informado");
  assert.equal(money(null), "Não informado");
  assert.match(money("0"), /0,00/);
});
