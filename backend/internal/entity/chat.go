package entity

type ChatRequest struct {
	Question string `json:"question"`
	TopK     *int   `json:"top_k,omitempty"`
}

type Source struct {
	ChunkID    string  `json:"chunk_id"`
	DocumentID string  `json:"document_id"`
	Source     string  `json:"source"`
	Score      float64 `json:"score"`
	Text       string  `json:"text"`
}

type QueryRequest struct {
	Question string `json:"question"`
	TopK     *int   `json:"top_k,omitempty"`
}

type QueryResponse struct {
	Question string   `json:"question"`
	Sources  []Source `json:"sources"`
}
