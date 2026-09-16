package entity

type DocumentSummary struct {
	DocumentID string `json:"document_id"`
	Source     string `json:"source"`
	ChunkCount int    `json:"chunk_count"`
	Status     string `json:"status"`
}

type Chunk struct {
	ChunkID    string `json:"chunk_id"`
	DocumentID string `json:"document_id"`
	Source     string `json:"source"`
	Text       string `json:"text"`
	ChunkIndex int    `json:"chunk_index"`
}

type DeleteDocumentsRequest struct {
	DocumentIDs []string `json:"document_ids"`
}

type DeleteChunksRequest struct {
	ChunkIDs []string `json:"chunk_ids"`
}

type DeleteResult struct {
	Deleted int `json:"deleted"`
}
