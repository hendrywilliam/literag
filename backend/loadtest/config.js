// Central configuration for the backend load tests.
//
// Scope: the document/chunk API (backed directly by Neo4j). The streaming chat
// endpoint is intentionally excluded, since its latency is dominated by the RAG
// service and the LLM provider rather than by this backend.
//
// Every value is overridable through environment variables so the same suite
// can target local, staging, or production-like stacks without edits. See
// `.env.example` for the documented list.

const env = __ENV;

function num(name, fallback) {
  const raw = env[name];
  if (raw === undefined || raw === '') {
    return fallback;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

function bool(name, fallback) {
  const raw = env[name];
  if (raw === undefined || raw === '') {
    return fallback;
  }
  return String(raw).trim().toLowerCase() === 'true';
}

function list(name) {
  return String(env[name] || '')
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

// --- target ---

export const BASE_URL = String(env.BASE_URL || 'http://localhost:8080').replace(/\/+$/, '');
export const SCENARIO = String(env.SCENARIO || 'load').trim().toLowerCase();

// --- load shape ---

export const VUS = Math.max(1, Math.floor(num('VUS', 20)));
export const DURATION = env.DURATION || '5m';
export const SMOKE_DURATION = env.SMOKE_DURATION || '30s';
export const READ_RPS = Math.max(1, Math.floor(num('READ_RPS', 50)));
export const THINK_TIME = Math.max(0, num('THINK_TIME', 1));

// --- timeouts ---

export const READ_TIMEOUT = env.READ_TIMEOUT || '5s';

// --- seed data ---

export const DOCUMENT_ID = env.DOCUMENT_ID || '';
export const CHUNK_ID = env.CHUNK_ID || '';
export const MAX_SEED_DOCS = Math.max(1, Math.floor(num('MAX_SEED_DOCS', 25)));
export const MAX_SEED_CHUNKS = Math.max(1, Math.floor(num('MAX_SEED_CHUNKS', 50)));

// --- destructive writes (opt-in) ---

export const ALLOW_DESTRUCTIVE = bool('ALLOW_DESTRUCTIVE', false);
export const DELETE_DOCUMENT_IDS = list('DELETE_DOCUMENT_IDS');
export const DELETE_CHUNK_IDS = list('DELETE_CHUNK_IDS');

// --- thresholds ---

export const MAX_ERROR_RATE = num('MAX_ERROR_RATE', 0.01);
export const MIN_CHECK_RATE = num('MIN_CHECK_RATE', 0.99);
export const READ_P95_MS = num('READ_P95_MS', 300);
export const READ_P99_MS = num('READ_P99_MS', 800);

// Requests are tagged by traffic profile (`read` / `write`) rather than by
// executor name, so the read threshold applies across every scenario that hits
// the document API.
function thresholdsFor(scenario) {
  const base = {
    http_req_failed: [`rate<${MAX_ERROR_RATE}`],
    checks: [`rate>${MIN_CHECK_RATE}`],
  };

  if (scenario === 'write') {
    return base;
  }

  return {
    ...base,
    'http_req_duration{scenario:read}': [`p(95)<${READ_P95_MS}`, `p(99)<${READ_P99_MS}`],
  };
}

export const THRESHOLDS = thresholdsFor(SCENARIO);

export function scenariosFor(scenario) {
  switch (scenario) {
    case 'smoke':
      return {
        smoke_read: {
          executor: 'constant-vus',
          vus: 1,
          duration: SMOKE_DURATION,
          exec: 'readFlow',
          gracefulStop: '5s',
        },
      };

    // Maximum throughput: no think time, arrival rate is the target.
    case 'read':
      return {
        read: {
          executor: 'constant-arrival-rate',
          rate: READ_RPS,
          timeUnit: '1s',
          duration: DURATION,
          preAllocatedVUs: Math.max(10, Math.ceil(READ_RPS / 2)),
          maxVUs: Math.max(20, READ_RPS * 2),
          exec: 'readFlow',
        },
      };

    case 'stress':
      return {
        stress: {
          executor: 'ramping-vus',
          exec: 'readFlowWithPacing',
          startVUs: 1,
          stages: [
            { duration: '1m', target: VUS },
            { duration: '2m', target: VUS * 2 },
            { duration: '2m', target: VUS * 4 },
            { duration: '1m', target: 0 },
          ],
          gracefulStop: '30s',
        },
      };

    case 'spike':
      return {
        spike: {
          executor: 'ramping-vus',
          exec: 'readFlowWithPacing',
          stages: [
            { duration: '10s', target: 1 },
            { duration: '20s', target: VUS * 4 },
            { duration: '30s', target: VUS * 4 },
            { duration: '20s', target: 1 },
          ],
          gracefulStop: '30s',
        },
      };

    case 'soak':
      return {
        soak: {
          executor: 'constant-vus',
          vus: VUS,
          duration: DURATION,
          exec: 'readFlowWithPacing',
          gracefulStop: '30s',
        },
      };

    case 'write':
      return {
        write: {
          executor: 'per-vu-iterations',
          vus: Math.min(5, VUS),
          iterations: 1,
          exec: 'deleteFlow',
        },
      };

    case 'load':
    default:
      return {
        load_read: {
          executor: 'ramping-vus',
          exec: 'readFlowWithPacing',
          stages: [
            { duration: '30s', target: VUS },
            { duration: DURATION, target: VUS },
            { duration: '30s', target: 0 },
          ],
          gracefulStop: '30s',
        },
      };
  }
}

export const SCENARIOS = scenariosFor(SCENARIO);
