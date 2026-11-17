import { getToken } from "next-auth/jwt";
import type { NextRequest } from "next/server";

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

async function proxy(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  const apiBaseUrl =
    process.env.API_INTERNAL_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!apiBaseUrl) {
    return Response.json(
      { detail: "The simulation API is not configured." },
      { status: 503 },
    );
  }

  const secret = process.env.NEXTAUTH_SECRET;
  const token = secret ? await getToken({ req: request, secret }) : null;
  const apiAccessToken =
    typeof token?.apiAccessToken === "string" ? token.apiAccessToken : null;
  if (process.env.NODE_ENV === "production" && !apiAccessToken) {
    return Response.json(
      { detail: "Institutional sign-in is required." },
      { status: 401 },
    );
  }

  const { path } = await context.params;
  const url = new URL(
    `/v1/${path.map(encodeURIComponent).join("/")}`,
    apiBaseUrl,
  );
  url.search = request.nextUrl.search;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  const tenantId =
    request.headers.get("x-tenant-id") ??
    process.env.NEXT_PUBLIC_DEMO_TENANT_ID;
  if (tenantId) headers.set("X-Tenant-ID", tenantId);
  if (apiAccessToken) headers.set("Authorization", `Bearer ${apiAccessToken}`);

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  try {
    const upstream = await fetch(url, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });
    const responseHeaders = new Headers();
    const upstreamContentType = upstream.headers.get("content-type");
    if (upstreamContentType)
      responseHeaders.set("content-type", upstreamContentType);
    responseHeaders.set("cache-control", "no-store");
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      { detail: "Could not reach the simulation API." },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
