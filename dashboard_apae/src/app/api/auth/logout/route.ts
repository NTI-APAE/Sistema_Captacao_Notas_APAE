import { NextRequest, NextResponse } from "next/server";
import { requestAuth } from "@/lib/auth-transport";

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  if (origin === null || origin !== request.nextUrl.origin) {
    return NextResponse.json({ code: "forbidden" }, { status: 403 });
  }
  const cookieName = process.env.DASHBOARD_SESSION_COOKIE ?? "apae_session";
  const session = request.cookies.get(cookieName);
  await requestAuth(
    process.env.NOTAS_API_URL ?? "http://127.0.0.1:8000",
    "logout",
    {
      cookie: session
        ? `${cookieName}=${encodeURIComponent(session.value)}`
        : undefined,
    },
  );
  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(cookieName, "", {
    httpOnly: true,
    sameSite: "strict",
    path: "/",
    maxAge: 0,
  });
  response.headers.set("Cache-Control", "no-store");
  return response;
}
