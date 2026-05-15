import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { TypewriterStream } from './typewriter-stream';

// Replace rAF with a synchronous stand-in for deterministic tests.
let rafCallbacks: FrameRequestCallback[] = [];

beforeEach(() => {
  rafCallbacks = [];
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    rafCallbacks.push(cb);
    return rafCallbacks.length;
  });
  vi.stubGlobal('cancelAnimationFrame', () => {});
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function flushFrames(n = 1) {
  for (let i = 0; i < n; i++) {
    const cbs = rafCallbacks.splice(0);
    cbs.forEach((cb) => cb(performance.now()));
  }
}

describe('TypewriterStream', () => {
  it('renders text progressively via RAF when not reducedMotion', () => {
    const { rerender } = render(
      <TypewriterStream fullText="hello" isStreaming={true} reducedMotion={false} />
    );

    // Before any frame, nothing is shown yet (initial state '')
    // After frames, chars appear
    act(() => flushFrames(3));

    // 3 frames × 2 chars = 6 chars, but text is only 5 — should show all of "hello"
    expect(screen.getByRole('region')).toHaveTextContent('hello');

    // Streaming ends
    rerender(
      <TypewriterStream fullText="hello" isStreaming={false} reducedMotion={false} />
    );
    act(() => flushFrames(1));
    expect(screen.getByRole('region')).toHaveTextContent('hello');
  });

  it('renders complete text immediately on stream end when reducedMotion is true', () => {
    const { rerender } = render(
      <TypewriterStream fullText="world" isStreaming={true} reducedMotion={true} />
    );

    // While streaming with reducedMotion, shows placeholder not text
    expect(screen.getByRole('region')).toHaveTextContent('Writing…');

    // Stream ends
    rerender(
      <TypewriterStream fullText="world" isStreaming={false} reducedMotion={true} />
    );

    expect(screen.getByRole('region')).toHaveTextContent('world');
    expect(screen.getByRole('region')).not.toHaveTextContent('Writing…');
  });

  it('sets aria-busy=true while streaming and aria-busy=false when done', () => {
    const { rerender } = render(
      <TypewriterStream fullText="" isStreaming={true} reducedMotion={true} />
    );
    expect(screen.getByRole('region')).toHaveAttribute('aria-busy', 'true');

    rerender(
      <TypewriterStream fullText="done" isStreaming={false} reducedMotion={true} />
    );
    expect(screen.getByRole('region')).toHaveAttribute('aria-busy', 'false');
  });

  it('calls onComplete when stream ends and text is fully displayed (reducedMotion)', () => {
    const onComplete = vi.fn();
    const { rerender } = render(
      <TypewriterStream
        fullText="abc"
        isStreaming={true}
        reducedMotion={true}
        onComplete={onComplete}
      />
    );
    expect(onComplete).not.toHaveBeenCalled();

    rerender(
      <TypewriterStream
        fullText="abc"
        isStreaming={false}
        reducedMotion={true}
        onComplete={onComplete}
      />
    );
    expect(onComplete).toHaveBeenCalledOnce();
  });
});
