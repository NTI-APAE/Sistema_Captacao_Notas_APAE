import { strict as assert } from "node:assert";
import { test } from "node:test";
import { parseSessionCookie } from "../src/lib/cookie";
import { requestAuth } from "../src/lib/auth-transport";

test("extrai somente o cookie de sessão esperado", () => {
  assert.equal(
    parseSessionCookie("apae_session=abc123; HttpOnly; Path=/", "apae_session"),
    "abc123",
  );
  assert.equal(
    parseSessionCookie("outro=abc123; HttpOnly", "apae_session"),
    null,
  );
  assert.equal(
    parseSessionCookie("apae_session=; HttpOnly", "apae_session"),
    null,
  );
});

test("login usa JSON, no-store e não segue redirecionamento", async () => {
  const fetcher: typeof fetch = async (input, options) => {
    assert.equal(String(input), "http://127.0.0.1:8000/admin/auth/login");
    assert.equal(options?.method, "POST");
    assert.equal(options?.cache, "no-store");
    assert.equal(options?.redirect, "error");
    assert.equal(
      options?.body,
      JSON.stringify({ email: "op@apae.org.br", senha: "segredo" }),
    );
    return Response.json(
      {
        nome: "Operador",
        email: "op@apae.org.br",
        role: "ADMIN",
        scopes: ["dashboard:read"],
      },
      { headers: { "set-cookie": "apae_session=token; HttpOnly; Path=/" } },
    );
  };
  const result = await requestAuth("http://127.0.0.1:8000", "login", {
    body: { email: "op@apae.org.br", senha: "segredo" },
    fetcher,
  });
  assert.equal(result.ok, true);
  assert.equal(result.setCookie, "apae_session=token; HttpOnly; Path=/");
});

test("logout encaminha somente o cookie informado", async () => {
  const fetcher: typeof fetch = async (_input, options) => {
    assert.deepEqual(options?.headers, {
      Accept: "application/json",
      Cookie: "apae_session=token",
    });
    return new Response(null, { status: 204 });
  };
  const result = await requestAuth("http://localhost:8000", "logout", {
    cookie: "apae_session=token",
    fetcher,
  });
  assert.equal(result.ok, true);
});
