package usecase

import (
	"context"
	"fmt"
	"io"
	"strings"

	"literag-backend/internal/entity"
	"literag-backend/internal/repo/chat"
	"literag-backend/internal/repo/llm"
	"literag-backend/internal/repo/rag"
)

type ChatUsecase struct {
	rag  *rag.Client
	llm  *llm.Client
	repo chat.Repo
}

func NewChatUsecase(rag *rag.Client, llm *llm.Client, repo chat.Repo) *ChatUsecase {
	return &ChatUsecase{rag: rag, llm: llm, repo: repo}
}

func (u *ChatUsecase) Complete(ctx context.Context, req entity.ChatRequest) (io.ReadCloser, *entity.QueryResponse, error) {
	query, err := u.rag.Query(ctx, req.Question, req.TopK)
	if err != nil {
		return nil, nil, fmt.Errorf("retrieve context: %w", err)
	}

	userMsg := buildUserMessage(req.Question, query)

	body, err := u.llm.Stream(ctx, systemPrompt, userMsg, query.Sources)
	if err != nil {
		return nil, nil, err
	}

	return body, query, nil
}

const systemPrompt = "You are a helpful assistant. Answer the user's question using the provided context. Do not make up answers or guesses. Dont mention context, just answer naturally."

func buildUserMessage(question string, query *entity.QueryResponse) string {
	if len(query.Sources) == 0 {
		return question
	}

	var sb strings.Builder
	sb.WriteString("Use the following documents to answer the question that will follow: \n")
	sb.WriteString("Context:\n")
	for i, s := range query.Sources {
		sb.WriteString(fmt.Sprintf("[%d] (%s) %s\n", i+1, s.Source, s.Text))
	}
	sb.WriteString("\n\n---\n\n")
	sb.WriteString("\nQuestion: ")
	sb.WriteString(question)

	return sb.String()
}
