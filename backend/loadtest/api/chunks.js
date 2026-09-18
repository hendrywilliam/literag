import { getJson, postJson } from './client.js';

// Chunks belong to a document, so listing them is a document-scoped path, but
// the response is chunk data and lives here with the rest of the chunk calls.
export function listChunks(documentId) {
  return getJson(`/documents/${encodeURIComponent(documentId)}/chunks`, {
    endpoint: 'list_chunks',
  });
}

export function getChunk(chunkId) {
  return getJson(`/chunks/${encodeURIComponent(chunkId)}`, {
    endpoint: 'get_chunk',
  });
}

export function deleteChunks(chunkIds) {
  return postJson(
    '/chunks/delete',
    { chunk_ids: chunkIds },
    { endpoint: 'delete_chunks' },
  );
}
