package cache

import (
	"context"
	"errors"
	"time"

	"github.com/redis/go-redis/v9"
)

// Redis adapter for the Cache interface.
//
// redisCache adapts a go-redis client to the Cache interface.
//
// The client is owned by the caller (see cmd/main), so the adapter never closes
// it: the same client can serve other features such as rate limiting.
type redisCache struct {
	client *redis.Client
	prefix string
}

// NewRedis returns a Cache backed by Redis.
//
// Every key is namespaced with prefix so a shared instance (for example the
// Celery broker) cannot collide with cached entries. Pass an empty prefix to
// disable namespacing.
func NewRedis(client *redis.Client, prefix string) Cache {
	return &redisCache{client: client, prefix: prefix}
}

func (c *redisCache) namespaced(key string) string {
	return c.prefix + key
}

func (c *redisCache) Get(ctx context.Context, key string) ([]byte, bool, error) {
	value, err := c.client.Get(ctx, c.namespaced(key)).Bytes()
	if errors.Is(err, redis.Nil) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, err
	}

	return value, true, nil
}

func (c *redisCache) Set(ctx context.Context, key string, value []byte, ttl time.Duration) error {
	return c.client.Set(ctx, c.namespaced(key), value, ttl).Err()
}

func (c *redisCache) Delete(ctx context.Context, keys ...string) error {
	if len(keys) == 0 {
		return nil
	}

	namespaced := make([]string, len(keys))
	for i, key := range keys {
		namespaced[i] = c.namespaced(key)
	}

	return c.client.Del(ctx, namespaced...).Err()
}
