import type { ApiErrorCode, ApiResult } from "./types";

const errorCodes = new Set<ApiErrorCode>([
  "authentication_unavailable",
  "authentication_required",
  "forbidden",
  "not_found",
  "invalid_filters",
  "database_unavailable",
]);

export async function requestDashboard<T>(
  origin: string,
  endpoint: string,
  sessionCookie?: string,
  fetcher: typeof fetch = fetch,
): Promise<ApiResult<T>> {
  try {
    const base = new URL(origin);
    if (
      !["http:", "https:"].includes(base.protocol) ||
      base.username ||
      base.password
    ) {
      return { ok: false, error: { code: "unavailable", status: 503 } };
    }
    const url = new URL(`/admin/relatorios/${endpoint}`, base.origin);
    const response = await fetcher(url, {
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
      headers: {
        Accept: "application/json",
        ...(sessionCookie ? { Cookie: sessionCookie } : {}),
      },
    });
    if (!response.headers.get("content-type")?.includes("application/json")) {
      return { ok: false, error: { code: "invalid_response", status: 502 } };
    }
    const body = await response.json();
    if (!response.ok) {
      // Nunca repassa mensagens técnicas livres do backend para o HTML ou logs.
      const code = errorCodes.has(body?.code)
        ? (body.code as ApiErrorCode)
        : "unavailable";
      return { ok: false, error: { code, status: response.status } };
    }
    return { ok: true, data: body as T };
  } catch {
    return { ok: false, error: { code: "unavailable", status: 503 } };
  }
}
