import "server-only";
import { cookies } from "next/headers";
import { requestDashboard } from "./transport";
import type { ApiResult, Query } from "./types";

export async function dashboardApi<T>(
  endpoint: string,
  query: Query = {},
): Promise<ApiResult<T>> {
  const cookieName = process.env.DASHBOARD_SESSION_COOKIE ?? "apae_session";
  const session = (await cookies()).get(cookieName);
  // Só encaminha a sessão administrativa. Não encaminha chaves do worker/webhook.
  const cookie = session
    ? `${cookieName}=${encodeURIComponent(session.value)}`
    : undefined;
  const search = new URLSearchParams(query).toString();
  return requestDashboard<T>(
    process.env.NOTAS_API_URL ?? "http://127.0.0.1:8000",
    endpoint + (search ? `?${search}` : ""),
    cookie,
  );
}
