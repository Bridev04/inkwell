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
  const next = request.nextUrl.searchParams.get('next') ?? '/desk';

  const backendRes = await fetch(
    `${backendBase}/api/v1/auth/google?next=${encodeURIComponent(next)}`,
    {
      redirect: 'manual',
      headers: {
        'x-forwarded-for': request.headers.get('x-forwarded-for') ?? '',
        'x-real-ip': request.headers.get('x-real-ip') ?? '',
      },
    }
  );

  const location = backendRes.headers.get('location');
  if (!location) {
    return NextResponse.json({ detail: 'Google OAuth is not configured' }, { status: 503 });
  }

  const response = NextResponse.redirect(location, { status: 307 });

  // Explicitly forward the oauth_state Set-Cookie from Railway to the browser.
  // Vercel's rewrite proxy drops Set-Cookie headers from redirect responses,
  // which is why this must be a Route Handler rather than a transparent rewrite.
  for (const cookie of getSetCookies(backendRes.headers)) {
    response.headers.append('set-cookie', cookie);
  }

  return response;
}
