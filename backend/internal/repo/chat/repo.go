package chat

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
	"literag-backend/internal/entity"
)

type Repo interface {
	SaveConversation(ctx context.Context, req entity.ChatRequest, response entity.QueryResponse) error
}

type postgresRepo struct {
	pool *pgxpool.Pool
}

func NewRepo(ctx context.Context, databaseURL string) (Repo, error) {
	if databaseURL == "" {
		return &postgresRepo{}, nil
	}

	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return nil, err
	}
	return &postgresRepo{pool: pool}, nil
}

// SaveConversation is backlog. Uses raw SQL (no ORM).
func (r *postgresRepo) SaveConversation(ctx context.Context, req entity.ChatRequest, response entity.QueryResponse) error {
	// TODO(backlog): implement raw SQL insert into conversations/chats table.
	return nil
}
