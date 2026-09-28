import type { ApiResult } from "./types";

export interface LoginInput {
  email: string;
  senha: string;
}
export interface AdminUser {
  nome: string;
  email: string;
  role: string;
  scopes: string[];
}

export async function requestAuth(
  origin: string,
  action: "login" | "logout" | "me",
  options: { body?: LoginInput; cookie?: string; fetcher?: typeof fetch } = {},
): Promise<ApiResult<AdminUser> & { setCookie?: string }> {
  const fetcher = options.fetcher ?? fetch;
  try {
    const base = new URL(origin);
    if (
      !["http:", "https:"].includes(base.protocol) ||
      base.username ||
      base.password
    ) {
      return { ok: false, error: { code: "unavailable", status: 503 } };
    }
    const response = await fetcher(
      new URL(`/admin/auth/${action}`, base.origin),
      {
        method: action === "me" ? "GET" : "POST",
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(10_000),
        headers: {
          Accept: "application/json",
          ...(options.body ? { "Content-Type": "application/json" } : {}),
          ...(options.cookie ? { Cookie: options.cookie } : {}),
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
      },
    );
    const setCookie = response.headers.get("set-cookie") ?? undefined;
    if (!response.ok) {
      const code =
        response.status === 401
          ? "authentication_required"
          : response.status === 403
            ? "forbidden"
            : "unavailable";
      return { ok: false, error: { code, status: response.status }, setCookie };
    }
    const data = response.status === 204 ? null : await response.json();
    return { ok: true, data: data as AdminUser, setCookie };
  } catch {
    return { ok: false, error: { code: "unavailable", status: 503 } };
  }
}
