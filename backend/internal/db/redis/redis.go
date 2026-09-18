package redis

import (
	"context"
	"time"

	goredis "github.com/redis/go-redis/v9"
)

const pingTimeout = 3 * time.Second

// NewClient parses url (redis://host:port/db) and verifies connectivity, so a
// misconfigured cache fails fast at startup instead of on the first request.
//
// The caller owns the returned client and is responsible for closing it.
func NewClient(url string) (*goredis.Client, error) {
	opts, err := goredis.ParseURL(url)
	if err != nil {
		return nil, err
	}

	client := goredis.NewClient(opts)

	ctx, cancel := context.WithTimeout(context.Background(), pingTimeout)
	defer cancel()
	if err := client.Ping(ctx).Err(); err != nil {
		_ = client.Close()
		return nil, err
	}

	return client, nil
}
