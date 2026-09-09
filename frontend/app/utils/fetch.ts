const DEFAULT_TIMEOUT_MS = 5_000;

export function fetchData(
  url: string,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
  init?: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout>;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new Error(`Request timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  });

  return Promise.race([
    fetch(url, { ...init, signal: controller.signal }),
    timeoutPromise,
  ]).finally(() => {
    clearTimeout(timer);
  }) as Promise<Response>;
}
