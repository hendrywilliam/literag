package rag

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"golang.org/x/sync/singleflight"

	"literag-backend/internal/cache"
	"literag-backend/internal/entity"
)

const loadTimeout = 10 * time.Second

// cachedClient decorates a Querier with a read-through cache keyed by question
// and topK. Retrieval is expensive (embedding plus vector search), so a repeated
// question is served from Redis instead of the RAG service.
type cachedClient struct {
	next  Querier
	cache cache.Cache
	ttl   time.Duration

	// group collapses concurrent misses on the same key so a stampede does not
	// reach the RAG service.
	group singleflight.Group
}

// NewCachedClient wraps next with Redis-backed caching of its queries.
func NewCachedClient(next Querier, c cache.Cache, ttl time.Duration) Querier {
	return &cachedClient{next: next, cache: c, ttl: ttl}
}

// cacheKey hashes the question: it can be up to 2000 characters, which is long
// and awkward as a Redis key.
func cacheKey(question string, topK *int) string {
	sum := sha256.Sum256([]byte(question))

	top := "default"
	if topK != nil {
		top = strconv.Itoa(*topK)
	}

	return fmt.Sprintf("rag:query:%x:%s", sum, top)
}

func (c *cachedClient) Query(ctx context.Context, question string, topK *int) (*entity.QueryResponse, error) {
	key := cacheKey(question, topK)

	if raw, found, err := c.cache.Get(ctx, key); err == nil && found {
		var cached entity.QueryResponse
		if err := json.Unmarshal(raw, &cached); err == nil {
			return &cached, nil
		}
	}

	// The load is detached from the initiating caller's cancellation, otherwise
	// one aborted request would fail every goroutine waiting on the same key.
	result, err, _ := c.group.Do(key, func() (any, error) {
		loadCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), loadTimeout)
		defer cancel()
		return c.next.Query(loadCtx, question, topK)
	})
	if err != nil {
		return nil, err
	}

	value, ok := result.(*entity.QueryResponse)
	if !ok || value == nil {
		return nil, fmt.Errorf("cache: unexpected value type for key %q", key)
	}

	if raw, err := json.Marshal(value); err == nil {
		_ = c.cache.Set(ctx, key, raw, c.ttl)
	}

	return value, nil
}
