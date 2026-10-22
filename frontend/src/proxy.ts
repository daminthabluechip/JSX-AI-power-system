import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

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
    }
  }
  return new NextResponse("Please sign in to see the demo.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Transport planner demo", charset="UTF-8"' },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
