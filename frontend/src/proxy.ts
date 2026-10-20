import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Password protection for a shared demo. Runs before every page and every /api request.
//
// Turn it on by setting BASIC_AUTH_PASSWORD (and optionally BASIC_AUTH_USER, default "demo").
// With no password set (local development) it does nothing. The browser shows its own
// username/password box once, then remembers it.
//
// This is a light gate for a demo, not a user system: one shared login, no lock-out after wrong tries.
export function proxy(request: NextRequest) {
  const password = process.env.BASIC_AUTH_PASSWORD;
  if (!password) return NextResponse.next();

  const user = process.env.BASIC_AUTH_USER || "demo";
  const header = request.headers.get("authorization");
  if (header?.startsWith("Basic ")) {
    try {
      const [name, ...rest] = atob(header.slice(6)).split(":");
      if (name === user && rest.join(":") === password) return NextResponse.next();
    } catch {
      // malformed header: fall through to the challenge
    }
  }
  return new NextResponse("Please sign in to see the demo.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Transport planner demo", charset="UTF-8"' },
  });
}

// Everything except Next's own static files.
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
