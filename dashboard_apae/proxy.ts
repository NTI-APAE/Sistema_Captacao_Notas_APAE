import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const cookieName = process.env.DASHBOARD_SESSION_COOKIE ?? "apae_session";
  if (!request.cookies.has(cookieName)) {
    const login = new URL("/login", request.url);
    login.searchParams.set(
      "next",
      request.nextUrl.pathname + request.nextUrl.search,
    );
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/dashboard/:path*"] };
