'use client';

import { useState, useEffect, useRef, useLayoutEffect } from 'react';

interface TypewriterStreamProps {
  fullText: string;
  isStreaming: boolean;
  reducedMotion: boolean;
  onComplete?: () => void;
}

// Reveals text at ~80 chars/sec (2 chars/frame at 60fps) to produce a measured
// writing cadence rather than a strobe when the model outputs fast bursts.
export function TypewriterStream({
  fullText,
  isStreaming,
  reducedMotion,
  onComplete,
}: TypewriterStreamProps) {
  const [displayed, setDisplayed] = useState('');

  // Refs keep the RAF loop in sync with React state without restarting it.
  const fullTextRef = useRef(fullText);
  const isStreamingRef = useRef(isStreaming);
  const onCompleteRef = useRef(onComplete);
  const displayedCountRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const completeCalledRef = useRef(false);

  useLayoutEffect(() => { fullTextRef.current = fullText; }, [fullText]);
  useLayoutEffect(() => { isStreamingRef.current = isStreaming; }, [isStreaming]);
  useEffect(() => { onCompleteRef.current = onComplete; }, [onComplete]);

  // RAF-based cadence loop — starts on mount, stops when fully displayed and done streaming.
  useEffect(() => {
    if (reducedMotion) return;

    const CHARS_PER_FRAME = 2;

    function tick() {
      const full = fullTextRef.current;
      const count = displayedCountRef.current;

      if (count < full.length) {
        const end = Math.min(count + CHARS_PER_FRAME, full.length);
        displayedCountRef.current = end;
        setDisplayed(full.slice(0, end));
      }

      const hasMore = displayedCountRef.current < fullTextRef.current.length;
      if (hasMore || isStreamingRef.current) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        rafRef.current = null;
        if (!completeCalledRef.current) {
          completeCalledRef.current = true;
          onCompleteRef.current?.();
        }
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [reducedMotion]);

  // When reducedMotion is true, reveal full text immediately on stream completion.
  useEffect(() => {
    if (!reducedMotion || isStreaming) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDisplayed(fullText);
    displayedCountRef.current = fullText.length;
    if (!completeCalledRef.current) {
      completeCalledRef.current = true;
      onComplete?.();
    }
  }, [reducedMotion, isStreaming, fullText, onComplete]);

  const showCursor = isStreaming && !reducedMotion;
  const textToShow = reducedMotion ? (isStreaming ? '' : fullText) : displayed;

  return (
    <div
      role="region"
      aria-live="polite"
      aria-busy={isStreaming}
      className="min-h-48 font-serif leading-relaxed text-ink text-lg max-w-prose whitespace-pre-wrap"
    >
      {reducedMotion && isStreaming && (
        <span className="font-mono text-stone-600 text-xs">Writing…</span>
      )}
      {textToShow}
      {showCursor && (
        <span
          className="inline-block w-px h-5 bg-ink animate-pulse ml-0.5 align-middle"
          aria-hidden="true"
        />
      )}
    </div>
  );
}
