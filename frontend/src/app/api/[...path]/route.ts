import type { NextRequest } from "next/server";

// Forwards every /api/... request from the browser to the Flask backend.
//
// Why this exists (used when the website is deployed, e.g. on Render):
//  * The browser only ever talks to ONE address (this website), so there is no CORS problem and no
//    backend address is baked into the JavaScript.
//  * This code runs on the server, so it can add the secret API key to each request. The key never
//    reaches the browser, and the backend can refuse every request that does not come through here.
//
// Settings (read when a request arrives, so they can be changed without rebuilding):
//   BACKEND_URL  where the backend is, e.g. https://my-api.onrender.com or http://backend:5000
//   API_KEY      the same secret the backend has in its API_KEY setting
// Locally (npm run dev) the website calls the backend directly and this file is not used.

export const dynamic = "force-dynamic"; // never cache an API answer

function backendUrl(): string {
  let url = process.env.BACKEND_URL || "http://127.0.0.1:5000";
  if (!/^https?:\/\//.test(url)) url = `http://${url}`; // allow a bare "host:port"
  return url.replace(/\/+$/, "");
}

async function forward(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const target = `${backendUrl()}/${path.join("/")}${req.nextUrl.search}`;

  // Pass on only what the backend needs.
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
      signal: AbortSignal.timeout(100_000), // hosts usually cut requests after about 100 s
    });
  } catch {
    return Response.json(
      { error: "backend_unreachable", details: { message: "The backend is not reachable. It may be starting up; try again in a minute." } },
      { status: 502 }
    );
  }

  // The body was already decoded by fetch, so these headers would no longer be true.
  const out = new Headers(upstream.headers);
  for (const name of ["content-encoding", "content-length", "transfer-encoding", "connection"]) out.delete(name);
  return new Response(upstream.status === 204 ? null : upstream.body, { status: upstream.status, headers: out });
}

export { forward as GET, forward as POST, forward as PUT, forward as PATCH, forward as DELETE };
