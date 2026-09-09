package main

import (
	"context"
	"log"

	"github.com/gin-gonic/gin"

	"literag-backend/internal/config"
	"literag-backend/internal/handler"
	"literag-backend/internal/logger"
	"literag-backend/internal/middleware"
	"literag-backend/internal/repo/chat"
	"literag-backend/internal/repo/llm"
	"literag-backend/internal/repo/rag"
	"literag-backend/internal/usecase"
)

func main() {
	cfg := config.Load()
	logg := logger.Init("info")

	ctx := context.Background()

	chatRepo, err := chat.NewRepo(ctx, cfg.DatabaseURL)
	if err != nil {
		logg.Fatal().Err(err).Msg("init chat repo")
	}

	ragClient := rag.NewClient(cfg.RAGURL)
	llmClient := llm.NewClient(cfg.OpenRouterURL, cfg.OpenRouterAPIKey, cfg.OpenRouterModel)
	chatUsecase := usecase.NewChatUsecase(ragClient, llmClient, chatRepo)
	chatHandler := handler.NewChatHandler(chatUsecase)

	r := gin.New()
	r.Use(middleware.Logger(logg))
	r.Use(middleware.Recovery(logg))

	r.POST("/chat/completion", chatHandler.Completion)

	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal(err)
	}
}
