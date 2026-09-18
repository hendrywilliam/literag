import { check, sleep } from 'k6';

import { getChunk, listChunks } from '../api/chunks.js';
import { getDocument, listDocuments } from '../api/documents.js';
import { THINK_TIME } from '../config.js';
import { readDuration } from '../metrics.js';

function pick(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function isArrayBody(res) {
  try {
    return Array.isArray(res.json());
  } catch (err) {
    return false;
  }
}

function fieldMatches(field, expected) {
  return (res) => {
    try {
      return res.json()[field] === expected;
    } catch (err) {
      return false;
    }
  };
}

/**
 * Document/chunk read path. Backed directly by Neo4j, so it is expected to be
 * fast; latency is tracked separately from the aggregate http_req_duration.
 */
export function readFlow(data) {
  const documentIds = (data && data.documentIds) || [];
  const chunkIds = (data && data.chunkIds) || [];

  const documents = listDocuments();
  readDuration.add(documents.timings.duration);
  check(documents, {
    'documents: status 200': (r) => r.status === 200,
    'documents: body is an array': isArrayBody,
    'documents: items expose contract fields': (r) => {
      try {
        const body = r.json();
        if (!Array.isArray(body) || body.length === 0) {
          return true;
        }
        const item = body[0];
        return (
          typeof item.document_id === 'string' &&
          typeof item.source === 'string' &&
          typeof item.chunk_count === 'number' &&
          typeof item.status === 'string'
        );
      } catch (err) {
        return false;
      }
    },
  });

  if (documentIds.length > 0) {
    const documentId = pick(documentIds);

    const document = getDocument(documentId);
    check(document, {
      'document: status 200': (r) => r.status === 200,
      'document: id matches request': fieldMatches('document_id', documentId),
    });

    const chunks = listChunks(documentId);
    check(chunks, {
      'chunks: status 200': (r) => r.status === 200,
      'chunks: body is an array': isArrayBody,
    });
  }

  if (chunkIds.length > 0) {
    const chunkId = pick(chunkIds);

    const chunk = getChunk(chunkId);
    check(chunk, {
      'chunk: status 200': (r) => r.status === 200,
      'chunk: id matches request': fieldMatches('chunk_id', chunkId),
    });
  }
}

/**
 * Same flow plus think time, so VU-based scenarios (load/stress/spike/soak)
 * model users pausing between requests instead of hammering back-to-back.
 * Set THINK_TIME=0 for maximum throughput.
 */
export function readFlowWithPacing(data) {
  readFlow(data);

  if (THINK_TIME > 0) {
    sleep(Math.random() * THINK_TIME);
  }
}
