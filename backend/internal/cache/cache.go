package cache

import (
	"context"
	"time"
)

// Cache is the contract every cache backend must implement.
//
// It is deliberately small (get/set/delete) so another backend can be dropped
// in without touching callers: Redis today, a KV store or an in-memory map
// later. Implementations must report a missing key as a miss, not an error.
type Cache interface {
	// Get returns the value stored under key. found reports whether the key
	// existed; a miss is (nil, false, nil), never an error.
	Get(ctx context.Context, key string) (value []byte, found bool, err error)

	// Set stores value under key for ttl. A ttl <= 0 means no expiration.
	Set(ctx context.Context, key string, value []byte, ttl time.Duration) error

	// Delete removes the given keys. Keys that do not exist are ignored.
	Delete(ctx context.Context, keys ...string) error
}
