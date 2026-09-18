import { getJson, postJson } from './client.js';

export function listDocuments() {
  return getJson('/documents', { endpoint: 'list_documents' });
}

export function getDocument(documentId) {
  return getJson(`/documents/${encodeURIComponent(documentId)}`, {
    endpoint: 'get_document',
  });
}

export function deleteDocuments(documentIds) {
  return postJson(
    '/documents/delete',
    { document_ids: documentIds },
    { endpoint: 'delete_documents' },
  );
}
