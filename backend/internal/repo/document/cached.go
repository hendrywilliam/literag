package document

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"golang.org/x/sync/singleflight"

	"literag-backend/internal/cache"
	"literag-backend/internal/entity"
)

const (
	cacheKeyDocumentList   = "documents:list"
	cacheKeyDocument       = "documents:%s"
	cacheKeyDocumentChunks = "documents:%s:chunks"
	cacheKeyChunk          = "chunks:%s"

	// loadTimeout bounds a singleflight load, which runs detached from the
	// caller context so collapsing a stampede can never hang forever.
	loadTimeout = 10 * time.Second
)

// cachedRepo decorates a Repo with a read-through cache.
//
// Only reads are cached, and deletes invalidate. Every cache failure degrades
// to a direct call, because the cache must never break reads.
type cachedRepo struct {
	next  Repo
	cache cache.Cache
	ttl   time.Duration

	// group collapses concurrent misses on the same key so a stampede does not
	// reach Neo4j.
	group singleflight.Group
}

// NewCachedRepo wraps next with Redis-backed caching of its read methods.
func NewCachedRepo(next Repo, c cache.Cache, ttl time.Duration) Repo {
	return &cachedRepo{next: next, cache: c, ttl: ttl}
}

func (r *cachedRepo) ListDocuments(ctx context.Context) ([]entity.DocumentSummary, error) {
	return readThrough(ctx, r, cacheKeyDocumentList, r.next.ListDocuments)
}

func (r *cachedRepo) GetDocument(ctx context.Context, documentID string) (entity.DocumentSummary, error) {
	key := fmt.Sprintf(cacheKeyDocument, documentID)
	return readThrough(ctx, r, key, func(ctx context.Context) (entity.DocumentSummary, error) {
		return r.next.GetDocument(ctx, documentID)
	})
}

func (r *cachedRepo) ListChunks(ctx context.Context, documentID string) ([]entity.Chunk, error) {
	key := fmt.Sprintf(cacheKeyDocumentChunks, documentID)
	return readThrough(ctx, r, key, func(ctx context.Context) ([]entity.Chunk, error) {
		return r.next.ListChunks(ctx, documentID)
	})
}

func (r *cachedRepo) GetChunk(ctx context.Context, chunkID string) (entity.Chunk, error) {
	key := fmt.Sprintf(cacheKeyChunk, chunkID)
	return readThrough(ctx, r, key, func(ctx context.Context) (entity.Chunk, error) {
		return r.next.GetChunk(ctx, chunkID)
	})
}

func (r *cachedRepo) DeleteDocuments(ctx context.Context, documentIDs []string) (int, error) {
	deleted, err := r.next.DeleteDocuments(ctx, documentIDs)
	if err != nil {
		return deleted, err
	}

	keys := make([]string, 0, 1+2*len(documentIDs))
	keys = append(keys, cacheKeyDocumentList)
	for _, documentID := range documentIDs {
		keys = append(keys,
			fmt.Sprintf(cacheKeyDocument, documentID),
			fmt.Sprintf(cacheKeyDocumentChunks, documentID),
		)
	}
	r.invalidate(ctx, keys)

	return deleted, nil
}

func (r *cachedRepo) DeleteChunks(ctx context.Context, chunkIDs []string) (int, error) {
	deleted, err := r.next.DeleteChunks(ctx, chunkIDs)
	if err != nil {
		return deleted, err
	}

	keys := make([]string, 0, len(chunkIDs))
	for _, chunkID := range chunkIDs {
		keys = append(keys, fmt.Sprintf(cacheKeyChunk, chunkID))
	}
	// documents:{id}:chunks cannot be derived from a chunk id, so those entries
	// are left to expire with the TTL.
	r.invalidate(ctx, keys)

	return deleted, nil
}

// invalidate drops cache entries after a successful write. A cache failure is
// swallowed: the worst case is a stale entry that expires with the TTL.
func (r *cachedRepo) invalidate(ctx context.Context, keys []string) {
	_ = r.cache.Delete(ctx, keys...)
}

// readThrough returns the cached value for key, or loads it and caches the
// result. Cache failures fall back to load, and errors are never cached.
func readThrough[T any](
	ctx context.Context,
	r *cachedRepo,
	key string,
	load func(context.Context) (T, error),
) (T, error) {
	var zero T

	if raw, found, err := r.cache.Get(ctx, key); err == nil && found {
		var cached T
		if err := json.Unmarshal(raw, &cached); err == nil {
			return cached, nil
		}
	}

	// The load is detached from the initiating caller's cancellation, otherwise
	// one aborted request would fail every goroutine waiting on the same key.
	result, err, _ := r.group.Do(key, func() (any, error) {
		loadCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), loadTimeout)
		defer cancel()
		return load(loadCtx)
	})
	if err != nil {
		return zero, err
	}

	value, ok := result.(T)
	if !ok {
		return zero, fmt.Errorf("cache: unexpected value type for key %q", key)
	}

	if raw, err := json.Marshal(value); err == nil {
		_ = r.cache.Set(ctx, key, raw, r.ttl)
	}

	return value, nil
}
