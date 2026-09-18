import { check } from 'k6';

import { deleteChunks } from '../api/chunks.js';
import { deleteDocuments } from '../api/documents.js';
import { DELETE_CHUNK_IDS, DELETE_DOCUMENT_IDS } from '../config.js';

function hasDeletedField(res) {
  try {
    return typeof res.json().deleted === 'number';
  } catch (err) {
    return false;
  }
}

/**
 * Destructive path. Deleting a document also deletes its chunks in Neo4j
 * (`DETACH DELETE`) and cannot be undone, so this only runs when explicitly
 * enabled against a disposable stack. See the guard in main.js.
 */
export function deleteFlow() {
  const chunks = deleteChunks(DELETE_CHUNK_IDS);
  check(chunks, {
    'chunks delete: status 200': (r) => r.status === 200,
    'chunks delete: returns deleted count': hasDeletedField,
  });

  const documents = deleteDocuments(DELETE_DOCUMENT_IDS);
  check(documents, {
    'documents delete: status 200': (r) => r.status === 200,
    'documents delete: returns deleted count': hasDeletedField,
  });
}
