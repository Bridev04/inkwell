// EventSource only supports GET requests. The rewrites endpoint requires a POST
// with a JSON body, so we roll our own parser over the Fetch ReadableStream instead.

export async function parseSSE(
  response: Response,
  handlers: Record<string, (data: unknown) => void>
): Promise<void> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split('\n\n');
      // Last entry may be an incomplete event — keep it in the buffer.
      buffer = events.pop() ?? '';

      for (const eventText of events) {
        if (!eventText.trim()) continue;

        let eventName: string | undefined;
        let dataLine: string | undefined;

        for (const line of eventText.split('\n')) {
          if (line.startsWith(':')) continue; // SSE comment line
          if (line.startsWith('event:')) {
            eventName = line.slice('event:'.length).trim();
          } else if (line.startsWith('data:')) {
            dataLine = line.slice('data:'.length).trim();
          }
        }

        if (eventName && dataLine !== undefined && handlers[eventName]) {
          try {
            handlers[eventName](JSON.parse(dataLine));
          } catch {
            // Malformed JSON — skip this event rather than crashing the stream.
          }
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}
