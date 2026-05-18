'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

const SAFE_PATH_RE = /^\/[a-zA-Z0-9/_-]{0,128}$/;

export default function AuthCallbackPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const router = useRouter();

  useEffect(() => {
    searchParams.then(({ next }) => {
      const destination =
        next && SAFE_PATH_RE.test(next) ? next : '/desk';
      router.refresh();
      router.push(destination);
    });
  }, [router, searchParams]);

  return null;
}
