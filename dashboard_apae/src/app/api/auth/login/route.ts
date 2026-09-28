import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/cookie";
import { requestAuth } from "@/lib/auth-transport";

function sameOrigin(request: NextRequest) {
  const origin = request.headers.get("origin");
  return origin !== null && origin === request.nextUrl.origin;
}

export async function POST(request: NextRequest) {
  if (!sameOrigin(request))
    return NextResponse.json({ code: "forbidden" }, { status: 403 });
  let input: unknown;
  try {
    input = await request.json();
  } catch {
    return NextResponse.json({ code: "invalid_request" }, { status: 400 });
  }
  if (!input || typeof input !== "object")
    return NextResponse.json({ code: "invalid_request" }, { status: 400 });
  const { email, senha } = input as Record<string, unknown>;
  if (
    typeof email !== "string" ||
    typeof senha !== "string" ||
    email.length > 254 ||
    senha.length > 200
  ) {
    return NextResponse.json({ code: "invalid_request" }, { status: 400 });
  }
  const result = await requestAuth(
    process.env.NOTAS_API_URL ?? "http://127.0.0.1:8000",
    "login",
    { body: { email, senha } },
  );
  if (!result.ok)
    return NextResponse.json(
      { code: result.error.code },
      { status: result.error.status },
    );
  const cookieName = process.env.DASHBOARD_SESSION_COOKIE ?? "apae_session";
  const value = result.setCookie
    ? parseSessionCookie(result.setCookie, cookieName)
    : null;
  if (!value)
    return NextResponse.json({ code: "unavailable" }, { status: 502 });
  const response = NextResponse.json({ user: result.data });
  response.cookies.set(cookieName, value, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: Number(process.env.DASHBOARD_SESSION_MINUTES ?? "480") * 60,
  });
  response.headers.set("Cache-Control", "no-store");
  return response;
}
