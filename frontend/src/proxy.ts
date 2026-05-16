import { NextRequest, NextResponse } from 'next/server';

const APP_PREFIXES = ['/desk', '/documents', '/grammar', '/paraphrase'];
const AUTH_PATHS = ['/login', '/register'];

export function proxy(request: NextRequest) {
  const token = request.cookies.get('access_token');
  const path = request.nextUrl.pathname;

  const isApp = APP_PREFIXES.some((p) => path === p || path.startsWith(p + '/'));
  const isAuth = AUTH_PATHS.includes(path);

  if (isApp && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  if (isAuth && token) {
    return NextResponse.redirect(new URL('/desk', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/desk/:path*',
    '/documents/:path*',
    '/grammar/:path*',
    '/paraphrase/:path*',
    '/login',
    '/register',
  ],
};
