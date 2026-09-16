package handler

import (
	"errors"
	"net/http"

	"literag-backend/internal/entity"
	"literag-backend/internal/usecase"

	"github.com/gin-gonic/gin"
)

type DocumentHandler struct {
	usecase *usecase.DocumentUsecase
}

func NewDocumentHandler(u *usecase.DocumentUsecase) *DocumentHandler {
	return &DocumentHandler{usecase: u}
}

func (h *DocumentHandler) ListDocuments(c *gin.Context) {
	docs, err := h.usecase.ListDocuments(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list documents"})
		return
	}
	c.JSON(http.StatusOK, docs)
}

func (h *DocumentHandler) GetDocument(c *gin.Context) {
	doc, err := h.usecase.GetDocument(c.Request.Context(), c.Param("document_id"))
	if err != nil {
		if errors.Is(err, usecase.ErrDocumentNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "document not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get document"})
		return
	}
	c.JSON(http.StatusOK, doc)
}

func (h *DocumentHandler) DeleteDocuments(c *gin.Context) {
	var req entity.DeleteDocumentsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	deleted, err := h.usecase.DeleteDocuments(c.Request.Context(), req.DocumentIDs)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, entity.DeleteResult{Deleted: deleted})
}

func (h *DocumentHandler) ListChunks(c *gin.Context) {
	chunks, err := h.usecase.ListChunks(c.Request.Context(), c.Param("document_id"))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list chunks"})
		return
	}
	c.JSON(http.StatusOK, chunks)
}

func (h *DocumentHandler) GetChunk(c *gin.Context) {
	chunk, err := h.usecase.GetChunk(c.Request.Context(), c.Param("chunk_id"))
	if err != nil {
		if errors.Is(err, usecase.ErrChunkNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "chunk not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get chunk"})
		return
	}
	c.JSON(http.StatusOK, chunk)
}

func (h *DocumentHandler) DeleteChunks(c *gin.Context) {
	var req entity.DeleteChunksRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	deleted, err := h.usecase.DeleteChunks(c.Request.Context(), req.ChunkIDs)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, entity.DeleteResult{Deleted: deleted})
}
