# Backend load tests (k6)

Load tests for the Go backend's document and chunk API, which is backed directly
by Neo4j.

**In scope:** `GET /documents`, `GET /documents/{document_id}`,
`GET /documents/{document_id}/chunks`, `GET /chunks/{chunk_id}`, plus the opt-in
destructive `POST /documents/delete` and `POST /chunks/delete`.

**Out of scope:** `POST /chat/completion`. That endpoint streams a completion
whose latency is dominated by the RAG service and the external LLM provider, so
it measures the stack behind the backend rather than the backend itself. Load
testing it here would produce noisy, non-actionable results.

## Layout

```
backend/
├─ Makefile                    # convenience targets
└─ loadtest/
   ├─ README.md
   ├─ .env.example             # documented configuration
   ├─ run.sh                   # loads .env, applies overrides, runs k6
   ├─ config.js                # env parsing, scenarios, thresholds
   ├─ main.js                  # entrypoint: setup() + options + exec exports
   ├─ metrics.js               # custom read-latency Trend
   ├─ api/                     # one file per resource
   │  ├─ client.js             # shared GET/POST helpers, tags, timeout
   │  ├─ documents.js          # listDocuments, getDocument, deleteDocuments
   │  └─ chunks.js             # listChunks, getChunk, deleteChunks
   └─ scenarios/
      ├─ read.js               # readFlow, readFlowWithPacing
      └─ write.js              # deleteFlow (destructive, opt-in)
```

## Prerequisites

- **k6 v0.53+** (uses `http.expectedStatuses`). Verified against v0.57.
  Install: <https://grafana.com/docs/k6/latest/set-up/install-k6/>
- A running backend (`go run ./cmd/main`) with reachable Neo4j.
- **Seeded data.** The backend has no create/upload endpoint, so documents must
  already exist in Neo4j. Upload through the RAG service
  (`POST {RAG_URL}/documents/upload`), then poll `GET /jobs/{job_id}` until the
  job is `done`. Without data, the read checks are skipped and the suite only
  exercises `GET /documents`.

## Quick start

```bash
cd backend
cp loadtest/.env.example loadtest/.env   # optional; adjust BASE_URL etc.
make loadtest-smoke                      # 1 VU, 30s
```

Or run k6 directly:

```bash
./loadtest/run.sh SCENARIO=read READ_RPS=100 DURATION=2m
BASE_URL=http://staging:8080 k6 run loadtest/main.js
```

## Scenarios

| `SCENARIO` | Executor | What it measures |
| ---------- | -------- | ---------------- |
| `smoke`    | 1 VU, 30s | Endpoint reachability and response contract |
| `load` (default) | ramping VUs | Steady load with think time; the everyday run |
| `read`     | constant-arrival-rate | Max throughput at a fixed `READ_RPS`; no think time |
| `stress`   | ramping VUs | Ramps until the latency/error thresholds break |
| `spike`    | ramping VUs | Sudden burst, then recovery |
| `soak`     | constant VUs | Long run to surface leaks (set a long `DURATION`) |
| `write`    | per-VU iterations | Bulk delete endpoints; **destructive, opt-in** |

`load`/`stress`/`spike`/`soak` use `readFlowWithPacing`, which pauses
`THINK_TIME` (averaged) between iterations. `read` uses the unpaced `readFlow`
so the arrival rate is the real target.

## Configuration

Every value is an environment variable; see `loadtest/.env.example` for the full
list. The most common ones:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `BASE_URL` | `http://localhost:8080` | Backend under test |
| `SCENARIO` | `load` | Scenario from the table above |
| `VUS` | `20` | Concurrent users for VU-based scenarios |
| `DURATION` | `5m` | Steady-phase duration |
| `SMOKE_DURATION` | `30s` | Duration of the `smoke` scenario |
| `READ_RPS` | `50` | Target RPS for the `read` scenario |
| `THINK_TIME` | `1` | Average pause between iterations (0 = none) |
| `DOCUMENT_ID` / `CHUNK_ID` | *(discovered)* | Pin specific ids instead of auto-discovery |
| `READ_P95_MS` / `READ_P99_MS` | `300` / `800` | Read latency budget |
| `MAX_ERROR_RATE` | `0.01` | Allowed failed-request rate |
| `MIN_CHECK_RATE` | `0.99` | Required passing-check rate |

`setup()` calls `GET /documents` (then `GET /documents/{id}/chunks`) once and
shares the resulting ids with every VU, so iterations read real data instead of
generating 404s.

## Thresholds

```
http_req_failed                              rate<0.01
checks                                       rate>0.99
http_req_duration{scenario:read}             p(95)<300ms  p(99)<800ms
```

Requests are tagged `scenario: read` or `scenario: write` by traffic profile
(not by executor name), so the read threshold holds across every scenario that
hits the document API. Run `k6 run` exit code is non-zero when a threshold
fails, which is what makes this CI-friendly.

## Destructive runs

`SCENARIO=write` permanently deletes documents and chunks in Neo4j
(`DETACH DELETE`) and cannot be undone. Two guards make that explicit:

1. `ALLOW_DESTRUCTIVE=true` must be set.
2. `DELETE_DOCUMENT_IDS` and `DELETE_CHUNK_IDS` must both be non-empty, so
   targets are never ambiguous.

```bash
make loadtest-write DELETE_DOCUMENT_IDS=doc-1 DELETE_CHUNK_IDS=chunk-1,chunk-2
```

Only run it against a disposable stack.

## Output and CI

- Human-readable summary: printed to stdout by default.
- Machine-readable: `SUMMARY_EXPORT=loadtest/results/summary.json ./loadtest/run.sh ...`
- Time series: add a k6 output, e.g. `K6_BIN="k6 --out experimental-prometheus-rw"`
  or run the official image:

  ```bash
  docker run --rm -i --network host \
    -v "$PWD/loadtest:/lt" grafana/k6 run /lt/main.js
  ```

In CI, run `smoke` on every deploy and `load` on a schedule against staging,
asserting on k6's non-zero exit code when thresholds fail.

## Backend notes

Findings from wiring this up that affect the tests:

- The backend exposes **no `/healthz`**. The Kubernetes readiness probe is a raw
  TCP check, so smoke traffic uses `GET /documents` as the liveness signal.
- `backend/openapi.json` documents `GET /openapi.json`, but no such route is
  registered in `cmd/main/main.go`, and the file is not served at runtime.
- The `internal/ratelimit` package exists but is not wired into any route, so
  the suite does not expect `429` responses. If rate limiting is enabled later,
  add a scenario that asserts `429` and tag it separately so it does not pollute
  the latency thresholds.
