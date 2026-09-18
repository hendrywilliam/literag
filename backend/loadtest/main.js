import { listChunks } from './api/chunks.js';
import { listDocuments } from './api/documents.js';
import {
  ALLOW_DESTRUCTIVE,
  CHUNK_ID,
  DELETE_CHUNK_IDS,
  DELETE_DOCUMENT_IDS,
  DOCUMENT_ID,
  MAX_SEED_CHUNKS,
  MAX_SEED_DOCS,
  SCENARIO,
  SCENARIOS,
  THRESHOLDS,
} from './config.js';
import { readFlow, readFlowWithPacing } from './scenarios/read.js';
import { deleteFlow } from './scenarios/write.js';

// k6 resolves `exec` by exported name on this entrypoint, so re-export the
// scenario functions defined in their own modules.
export { readFlow, readFlowWithPacing, deleteFlow };

if (SCENARIO === 'write') {
  if (!ALLOW_DESTRUCTIVE) {
    throw new Error(
      'SCENARIO=write is destructive and requires ALLOW_DESTRUCTIVE=true. ' +
        'Run it only against a disposable stack.',
    );
  }
  if (DELETE_DOCUMENT_IDS.length === 0 || DELETE_CHUNK_IDS.length === 0) {
    throw new Error(
      'SCENARIO=write requires DELETE_DOCUMENT_IDS and DELETE_CHUNK_IDS ' +
        '(comma-separated ids) so the targets are explicit.',
    );
  }
}

export const options = {
  scenarios: SCENARIOS,
  thresholds: THRESHOLDS,
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

/**
 * Resolve real ids once before the test so VUs read existing data. The backend
 * has no create/upload endpoint (upload lives in the RAG service), so seeding
 * is a documented prerequisite; DOCUMENT_ID/CHUNK_ID can bypass discovery.
 */
export function setup() {
  const documentIds = [];
  const chunkIds = [];

  if (SCENARIO === 'write') {
    return { documentIds, chunkIds };
  }

  if (DOCUMENT_ID) {
    documentIds.push(DOCUMENT_ID);
  } else {
    const res = listDocuments();
    if (res.status === 200) {
      let docs = [];
      try {
        docs = res.json();
      } catch (err) {
        docs = [];
      }
      if (Array.isArray(docs)) {
        for (const doc of docs.slice(0, MAX_SEED_DOCS)) {
          if (doc && doc.document_id) {
            documentIds.push(doc.document_id);
          }
        }
      }
    } else {
      console.warn(`setup: GET /documents returned ${res.status}; read checks will be degraded`);
    }
  }

  if (CHUNK_ID) {
    chunkIds.push(CHUNK_ID);
  } else {
    for (const documentId of documentIds.slice(0, MAX_SEED_DOCS)) {
      const res = listChunks(documentId);
      if (res.status !== 200) {
        continue;
      }
      let chunks = [];
      try {
        chunks = res.json();
      } catch (err) {
        chunks = [];
      }
      if (!Array.isArray(chunks)) {
        continue;
      }
      for (const chunk of chunks.slice(0, MAX_SEED_CHUNKS)) {
        if (chunk && chunk.chunk_id) {
          chunkIds.push(chunk.chunk_id);
        }
      }
    }
  }

  if (documentIds.length === 0) {
    console.warn(
      'setup: no documents found. Seed data through the RAG service upload ' +
        'endpoint (then poll GET /jobs/{job_id}) for meaningful read tests, or ' +
        'pass DOCUMENT_ID/CHUNK_ID explicitly.',
    );
  }

  console.log(
    `setup: resolved ${documentIds.length} document(s) and ${chunkIds.length} chunk(s)`,
  );

  return { documentIds, chunkIds };
}
