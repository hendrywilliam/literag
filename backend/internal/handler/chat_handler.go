package handler

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"

	"literag-backend/internal/entity"
	"literag-backend/internal/middleware"
	"literag-backend/internal/usecase"

	"github.com/gin-gonic/gin"
)

type sourcesEvent struct {
	Type    string          `json:"type"`
	Sources []entity.Source `json:"sources"`
}

type ChatHandler struct {
	usecase *usecase.ChatUsecase
}

func NewChatHandler(u *usecase.ChatUsecase) *ChatHandler {
	return &ChatHandler{usecase: u}
}

func (h *ChatHandler) Completion(c *gin.Context) {
	log := middleware.FromContext(c)

	var req entity.ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Question == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "question is required"})
		return
	}

	body, query, err := h.usecase.Complete(c.Request.Context(), req)
	if err != nil {
		log.Error().Err(err).Msg("completion failed")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "completion failed"})
		return
	}
	defer body.Close()

	sourceCount := 0
	if query != nil {
		sourceCount = len(query.Sources)
	}
	log.Info().Str("question", req.Question).Int("sources", sourceCount).Msg("streaming")

	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")
	c.Status(http.StatusOK)

	buf := make([]byte, 4096) // 4KB
	flusher := c.Writer.(http.Flusher)
	for {
		n, err := body.Read(buf)
		if n > 0 {
			if _, werr := c.Writer.Write(buf[:n]); werr != nil {
				return
			}
			flusher.Flush()
		}
		if err != nil {
			if !errors.Is(err, io.EOF) {
				log.Error().Err(err).Msg("stream read failed")
			}
			break
		}
	}

	writeSources(c.Writer, flusher, query)
}

func writeSources(w io.Writer, flusher http.Flusher, query *entity.QueryResponse) {
	if query == nil || len(query.Sources) == 0 {
		return
	}

	payload := sourcesEvent{Type: "sources", Sources: query.Sources}
	data, err := json.Marshal(payload)
	if err != nil {
		return
	}

	if _, werr := fmt.Fprintf(w, "data: %s\n\n", data); werr == nil {
		flusher.Flush()
	}
}
