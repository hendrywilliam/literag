package config

import (
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	Port             string
	RAGURL           string
	OpenRouterURL    string
	OpenRouterAPIKey string
	OpenRouterModel  string
	DatabaseURL      string
	Neo4jURI         string
	Neo4jUsername    string
	Neo4jPassword    string
	Neo4jDatabase    string
}

func Load() Config {
	_ = godotenv.Load()

	return Config{
		Port:             getenv("PORT", "8080"),
		RAGURL:           getenv("RAG_URL", "http://localhost:8000"),
		OpenRouterURL:    getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
		OpenRouterAPIKey: os.Getenv("OPENROUTER_API_KEY"),
		OpenRouterModel:  getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash-latest"),
		DatabaseURL:      getenv("DATABASE_URL", ""),
		Neo4jURI:         getenv("NEO4J_URI", "bolt://localhost:7687"),
		Neo4jUsername:    getenv("NEO4J_USERNAME", "neo4j"),
		Neo4jPassword:    getenv("NEO4J_PASSWORD", ""),
		Neo4jDatabase:    getenv("NEO4J_DATABASE", "neo4j"),
	}
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
