import { strict as assert } from "node:assert";
import { test } from "node:test";
import { requestDashboard } from "../src/lib/transport";

test("consulta sem cache e encaminha somente a sessão recebida", async () => {
  const fetcher: typeof fetch = async (input, options) => {
    assert.equal(
      String(input),
      "http://127.0.0.1:8000/admin/relatorios/notas?page=2",
    );
    assert.equal(options?.cache, "no-store");
    assert.equal(options?.redirect, "error");
    assert.deepEqual(options?.headers, {
      Accept: "application/json",
      Cookie: "apae_session=test",
    });
    return Response.json({ total: 2 });
  };
  assert.deepEqual(
    await requestDashboard(
      "http://127.0.0.1:8000",
      "notas?page=2",
      "apae_session=test",
      fetcher,
    ),
    { ok: true, data: { total: 2 } },
  );
});

for (const [status, code] of [
  [503, "authentication_unavailable"],
  [401, "authentication_required"],
  [403, "forbidden"],
  [404, "not_found"],
  [422, "invalid_filters"],
] as const) {
  test(`preserva erro ${status} sem expor detalhes internos`, async () => {
    const fetcher: typeof fetch = async () =>
      Response.json({ code, detail: "secret=private" }, { status });
    const result = await requestDashboard(
      "http://localhost:8000",
      "resumo",
      undefined,
      fetcher,
    );
    assert.deepEqual(result, { ok: false, error: { code, status } });
    assert.ok(!JSON.stringify(result).includes("private"));
  });
}

test("trata indisponibilidade sem registrar a exceção", async () => {
  const fetcher: typeof fetch = async () => {
    throw new Error("private URL");
  };
  assert.deepEqual(
    await requestDashboard(
      "http://localhost:8000",
      "resumo",
      undefined,
      fetcher,
    ),
    { ok: false, error: { code: "unavailable", status: 503 } },
  );
});
test("não trata HTML de um proxy como dados válidos", async () => {
  const fetcher: typeof fetch = async () =>
    new Response("<html>login</html>", {
      headers: { "content-type": "text/html" },
    });
  assert.deepEqual(
    await requestDashboard(
      "http://localhost:8000",
      "resumo",
      undefined,
      fetcher,
    ),
    { ok: false, error: { code: "invalid_response", status: 502 } },
  );
});
test("não aceita credenciais na URL do backend", async () => {
  const fetcher: typeof fetch = async () => {
    assert.fail("não deve conectar");
  };
  const result = await requestDashboard(
    "http://user:password@localhost",
    "resumo",
    undefined,
    fetcher,
  );
  assert.equal(result.ok, false);
});
