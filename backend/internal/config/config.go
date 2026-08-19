package config

import "os"

type Config struct {
	Port           string
	RAGURL         string
	DeepSeekURL    string
	DeepSeekAPIKey string
	DeepSeekModel  string
	DatabaseURL    string
}

func Load() Config {
	return Config{
		Port:           getenv("PORT", "8080"),
		RAGURL:         getenv("RAG_URL", "http://localhost:8000"),
		DeepSeekURL:    getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
		DeepSeekAPIKey: os.Getenv("DEEPSEEK_API_KEY"),
		DeepSeekModel:  getenv("DEEPSEEK_MODEL", "deepseek-chat"),
		DatabaseURL:    getenv("DATABASE_URL", ""),
	}
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
