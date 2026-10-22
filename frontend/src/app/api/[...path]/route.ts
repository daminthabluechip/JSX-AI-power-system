import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

function backendUrl(): string {
  let url = process.env.BACKEND_URL || "http://127.0.0.1:5000";
  if (!/^https?:\/\//.test(url)) url = `http://${url}`;
  return url.replace(/\/+$/, "");
}

async function forward(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const target = `${backendUrl()}/${path.join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  for (const name of ["content-type", "accept"]) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (process.env.API_KEY) headers.set("X-API-Key", process.env.API_KEY);

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.timeout(100_000),
    });
  } catch {
    return Response.json(
      { error: "backend_unreachable", details: { message: "The backend is not reachable. It may be starting up; try again in a minute." } },
      { status: 502 }
    );
  }

  const out = new Headers(upstream.headers);
  for (const name of ["content-encoding", "content-length", "transfer-encoding", "connection"]) out.delete(name);
  return new Response(upstream.status === 204 ? null : upstream.body, { status: upstream.status, headers: out });
}

export { forward as GET, forward as POST, forward as PUT, forward as PATCH, forward as DELETE };
