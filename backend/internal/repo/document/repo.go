package document

import (
	"context"
	"errors"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"

	"literag-backend/internal/entity"
)

var ErrNotFound = errors.New("not found")

type Repo interface {
	ListDocuments(ctx context.Context) ([]entity.DocumentSummary, error)
	GetDocument(ctx context.Context, documentID string) (entity.DocumentSummary, error)
	ListChunks(ctx context.Context, documentID string) ([]entity.Chunk, error)
	GetChunk(ctx context.Context, chunkID string) (entity.Chunk, error)
	DeleteDocuments(ctx context.Context, documentIDs []string) (int, error)
	DeleteChunks(ctx context.Context, chunkIDs []string) (int, error)
}

type neo4jRepo struct {
	driver   neo4j.DriverWithContext
	database string
}

func NewRepo(driver neo4j.DriverWithContext, database string) Repo {
	return &neo4jRepo{driver: driver, database: database}
}

func (r *neo4jRepo) session(ctx context.Context) neo4j.SessionWithContext {
	return r.driver.NewSession(ctx, neo4j.SessionConfig{DatabaseName: r.database})
}

func (r *neo4jRepo) collect(ctx context.Context, query string, params map[string]any) ([]map[string]any, error) {
	session := r.session(ctx)
	defer session.Close(ctx)

	out, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, query, params)
		if err != nil {
			return nil, err
		}
		records, err := res.Collect(ctx)
		if err != nil {
			return nil, err
		}
		maps := make([]map[string]any, 0, len(records))
		for _, rec := range records {
			maps = append(maps, rec.AsMap())
		}
		return maps, nil
	})
	if err != nil {
		return nil, err
	}
	return out.([]map[string]any), nil
}

const listDocumentsQuery = `
MATCH (n:Chunk)
WHERE n.document_id IS NOT NULL
WITH n.document_id AS document_id, n.source AS source, count(n) AS chunk_count
OPTIONAL MATCH (d:Document {document_id: document_id})
RETURN document_id, source, chunk_count, coalesce(d.status, 'indexed') AS status
ORDER BY source
`

const getDocumentQuery = `
MATCH (n:Chunk {document_id: $document_id})
WITH n.document_id AS document_id, n.source AS source, count(n) AS chunk_count
OPTIONAL MATCH (d:Document {document_id: document_id})
RETURN document_id, source, chunk_count, coalesce(d.status, 'indexed') AS status
`

const listChunksQuery = `
MATCH (n:Chunk {document_id: $document_id})
RETURN n.chunk_id AS chunk_id, n.document_id AS document_id,
       n.source AS source, n.text AS text, n.chunk_index AS chunk_index
ORDER BY n.chunk_index
`

const getChunkQuery = `
MATCH (n:Chunk {chunk_id: $chunk_id})
RETURN n.chunk_id AS chunk_id, n.document_id AS document_id,
       n.source AS source, n.text AS text, n.chunk_index AS chunk_index
`

func (r *neo4jRepo) ListDocuments(ctx context.Context) ([]entity.DocumentSummary, error) {
	rows, err := r.collect(ctx, listDocumentsQuery, nil)
	if err != nil {
		return nil, err
	}
	out := make([]entity.DocumentSummary, 0, len(rows))
	for _, row := range rows {
		out = append(out, toDocument(row))
	}
	return out, nil
}

func (r *neo4jRepo) GetDocument(ctx context.Context, documentID string) (entity.DocumentSummary, error) {
	rows, err := r.collect(ctx, getDocumentQuery, map[string]any{"document_id": documentID})
	if err != nil {
		return entity.DocumentSummary{}, err
	}
	if len(rows) == 0 {
		return entity.DocumentSummary{}, ErrNotFound
	}
	return toDocument(rows[0]), nil
}

func (r *neo4jRepo) ListChunks(ctx context.Context, documentID string) ([]entity.Chunk, error) {
	rows, err := r.collect(ctx, listChunksQuery, map[string]any{"document_id": documentID})
	if err != nil {
		return nil, err
	}
	out := make([]entity.Chunk, 0, len(rows))
	for _, row := range rows {
		out = append(out, toChunk(row))
	}
	return out, nil
}

func (r *neo4jRepo) GetChunk(ctx context.Context, chunkID string) (entity.Chunk, error) {
	rows, err := r.collect(ctx, getChunkQuery, map[string]any{"chunk_id": chunkID})
	if err != nil {
		return entity.Chunk{}, err
	}
	if len(rows) == 0 {
		return entity.Chunk{}, ErrNotFound
	}
	return toChunk(rows[0]), nil
}

func (r *neo4jRepo) DeleteDocuments(ctx context.Context, documentIDs []string) (int, error) {
	session := r.session(ctx)
	defer session.Close(ctx)

	ids := toAnys(documentIDs)

	out, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		docDeleted, err := runCount(ctx, tx, `
			UNWIND $ids AS id
			MATCH (d:Document {document_id: id})
			DETACH DELETE d
			RETURN count(d) AS deleted
		`, map[string]any{"ids": ids})
		if err != nil {
			return nil, err
		}

		chunkDeleted, err := runCount(ctx, tx, `
			UNWIND $ids AS id
			MATCH (c:Chunk {document_id: id})
			DETACH DELETE c
			RETURN count(c) AS deleted
		`, map[string]any{"ids": ids})
		if err != nil {
			return nil, err
		}

		return docDeleted + chunkDeleted, nil
	})
	if err != nil {
		return 0, err
	}
	return out.(int), nil
}

func (r *neo4jRepo) DeleteChunks(ctx context.Context, chunkIDs []string) (int, error) {
	session := r.session(ctx)
	defer session.Close(ctx)

	ids := toAnys(chunkIDs)

	out, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		return runCount(ctx, tx, `
			UNWIND $ids AS id
			MATCH (c:Chunk {chunk_id: id})
			DETACH DELETE c
			RETURN count(c) AS deleted
		`, map[string]any{"ids": ids})
	})
	if err != nil {
		return 0, err
	}
	return out.(int), nil
}

func runCount(ctx context.Context, tx neo4j.ManagedTransaction, query string, params map[string]any) (int, error) {
	res, err := tx.Run(ctx, query, params)
	if err != nil {
		return 0, err
	}
	rec, err := res.Single(ctx)
	if err != nil {
		return 0, err
	}
	v, _ := rec.Get("deleted")
	return toInt(v), nil
}

func toAnys(in []string) []any {
	out := make([]any, len(in))
	for i, s := range in {
		out[i] = s
	}
	return out
}

func toDocument(row map[string]any) entity.DocumentSummary {
	return entity.DocumentSummary{
		DocumentID: asString(row, "document_id"),
		Source:     asString(row, "source"),
		ChunkCount: toInt(row["chunk_count"]),
		Status:     asString(row, "status"),
	}
}

func toChunk(row map[string]any) entity.Chunk {
	return entity.Chunk{
		ChunkID:    asString(row, "chunk_id"),
		DocumentID: asString(row, "document_id"),
		Source:     asString(row, "source"),
		Text:       asString(row, "text"),
		ChunkIndex: toInt(row["chunk_index"]),
	}
}

func asString(row map[string]any, key string) string {
	if v, ok := row[key].(string); ok {
		return v
	}
	return ""
}

func toInt(v any) int {
	switch n := v.(type) {
	case int64:
		return int(n)
	case int:
		return n
	case float64:
		return int(n)
	}
	return 0
}
