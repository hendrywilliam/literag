const DEFAULT_TIMEOUT_MS = 5_000;

export function fetchData(
  url: string,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
  init?: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  const callerSignal = init?.signal;
  const forwardAbort = () => controller.abort();

  callerSignal?.addEventListener('abort', forwardAbort, { once: true });

  let timer: ReturnType<typeof setTimeout> | null = null;

  const timeoutPromise = new Promise<never>((_, reject) => {
    if (timeoutMs > 0) {
      timer = setTimeout(() => {
        controller.abort();
        reject(new Error(`Request timed out after ${timeoutMs}ms`));
      }, timeoutMs);
    }
  });

  const request = fetch(url, { ...init, signal: controller.signal });

  return Promise.race([request, timeoutPromise]).finally(() => {
    if (timer) clearTimeout(timer);
    callerSignal?.removeEventListener('abort', forwardAbort);
  });
}
