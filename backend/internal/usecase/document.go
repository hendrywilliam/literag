package usecase

import (
	"context"
	"errors"

	"literag-backend/internal/entity"
	"literag-backend/internal/repo/document"
)

var ErrDocumentNotFound = document.ErrNotFound
var ErrChunkNotFound = document.ErrNotFound

type DocumentUsecase struct {
	repo document.Repo
}

func NewDocumentUsecase(repo document.Repo) *DocumentUsecase {
	return &DocumentUsecase{repo: repo}
}

func (u *DocumentUsecase) ListDocuments(ctx context.Context) ([]entity.DocumentSummary, error) {
	return u.repo.ListDocuments(ctx)
}

func (u *DocumentUsecase) GetDocument(ctx context.Context, documentID string) (entity.DocumentSummary, error) {
	return u.repo.GetDocument(ctx, documentID)
}

func (u *DocumentUsecase) ListChunks(ctx context.Context, documentID string) ([]entity.Chunk, error) {
	return u.repo.ListChunks(ctx, documentID)
}

func (u *DocumentUsecase) GetChunk(ctx context.Context, chunkID string) (entity.Chunk, error) {
	return u.repo.GetChunk(ctx, chunkID)
}

func (u *DocumentUsecase) DeleteDocuments(ctx context.Context, documentIDs []string) (int, error) {
	if len(documentIDs) == 0 {
		return 0, errors.New("document_ids must not be empty")
	}
	return u.repo.DeleteDocuments(ctx, documentIDs)
}

func (u *DocumentUsecase) DeleteChunks(ctx context.Context, chunkIDs []string) (int, error) {
	if len(chunkIDs) == 0 {
		return 0, errors.New("chunk_ids must not be empty")
	}
	return u.repo.DeleteChunks(ctx, chunkIDs)
}
