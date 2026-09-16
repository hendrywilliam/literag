package main

import (
	"context"
	"log"

	"github.com/gin-gonic/gin"

	"literag-backend/internal/config"
	"literag-backend/internal/db/neo4j"
	"literag-backend/internal/handler"
	"literag-backend/internal/logger"
	"literag-backend/internal/middleware"
	"literag-backend/internal/repo/chat"
	"literag-backend/internal/repo/document"
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

	neo4jDriver, err := neo4j.NewDriver(cfg.Neo4jURI, cfg.Neo4jUsername, cfg.Neo4jPassword)
	if err != nil {
		logg.Fatal().Err(err).Msg("init neo4j driver")
	}
	defer neo4jDriver.Close(ctx)

	if err := neo4jDriver.VerifyConnectivity(ctx); err != nil {
		logg.Warn().Err(err).Msg("neo4j unreachable; document endpoints may fail until available")
		log.Fatal(err)
	}

	docRepo := document.NewRepo(neo4jDriver, cfg.Neo4jDatabase)
	docUsecase := usecase.NewDocumentUsecase(docRepo)
	docHandler := handler.NewDocumentHandler(docUsecase)

	r := gin.New()
	r.Use(middleware.Logger(logg))
	r.Use(middleware.Recovery(logg))

	r.POST("/chat/completion", chatHandler.Completion)

	r.GET("/documents", docHandler.ListDocuments)
	r.GET("/documents/:document_id", docHandler.GetDocument)
	r.POST("/documents/delete", docHandler.DeleteDocuments)

	r.GET("/documents/:document_id/chunks", docHandler.ListChunks)
	r.GET("/chunks/:chunk_id", docHandler.GetChunk)
	r.POST("/chunks/delete", docHandler.DeleteChunks)

	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal(err)
	}
}
