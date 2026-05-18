import { NextRequest, NextResponse } from 'next/server';

const backendBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function getSetCookies(headers: Headers): string[] {
  if (typeof (headers as Headers & { getSetCookie?: () => string[] }).getSetCookie === 'function') {
    return (headers as Headers & { getSetCookie: () => string[] }).getSetCookie();
  }
  const single = headers.get('set-cookie');
  return single ? [single] : [];
}

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams.toString();

  const backendRes = await fetch(
    `${backendBase}/api/v1/auth/google/callback?${params}`,
    {
      redirect: 'manual',
      headers: {
        // Forward the oauth_state cookie (and any others) from the browser to Railway
        cookie: request.headers.get('cookie') ?? '',
        'x-forwarded-for': request.headers.get('x-forwarded-for') ?? '',
        'x-real-ip': request.headers.get('x-real-ip') ?? '',
      },
    }
  );

  // Railway raises HTTPException (4xx/5xx) on invalid state, expired session, etc.
  if (backendRes.status >= 400) {
    const body = await backendRes.json().catch(() => ({ detail: 'OAuth callback failed' }));
    return NextResponse.json(body, { status: backendRes.status });
  }

  const location = backendRes.headers.get('location');
  if (!location) {
    return NextResponse.json({ detail: 'No redirect location from backend' }, { status: 502 });
  }

  // Railway redirects to the full frontend URL (e.g. https://draftwell-six.vercel.app/desk).
  // We bounce through /auth-callback so the client can call router.refresh() before
  // router.push(), clearing the Next.js Router Cache stale entry for the protected route.
  const nextPath = (() => {
    try { return new URL(location).pathname; } catch { return '/desk'; }
  })();
  const response = NextResponse.redirect(
    new URL(`/auth-callback?next=${encodeURIComponent(nextPath)}`, request.url)
  );

  // Forward access_token cookie (and oauth_state deletion) from Railway to the browser.
  for (const cookie of getSetCookies(backendRes.headers)) {
    response.headers.append('set-cookie', cookie);
  }

  return response;
}
