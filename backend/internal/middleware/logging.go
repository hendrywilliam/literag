package middleware

import (
	"time"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog"
)

const loggerKey = "logger"

func Logger(log zerolog.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()

		c.Set(loggerKey, log)
		c.Next()

		status := c.Writer.Status()
		ev := log.Info().
			Str("method", c.Request.Method).
			Str("path", c.Request.URL.Path).
			Int("status", status).
			Dur("latency", time.Since(start)).
			Str("client_ip", c.ClientIP()).
			Int("body_size", c.Writer.Size())

		if len(c.Errors) > 0 {
			ev = log.Error().Err(c.Errors.Last().Err).
				Str("method", c.Request.Method).
				Str("path", c.Request.URL.Path).
				Int("status", status).
				Dur("latency", time.Since(start)).
				Str("client_ip", c.ClientIP())
		}

		ev.Msg("request")
	}
}

func Recovery(log zerolog.Logger) gin.HandlerFunc {
	return gin.CustomRecovery(func(c *gin.Context, recovered any) {
		log.Error().
			Interface("panic", recovered).
			Str("method", c.Request.Method).
			Str("path", c.Request.URL.Path).
			Msg("panic recovered")

		c.AbortWithStatusJSON(500, gin.H{"error": "internal server error"})
	})
}

func FromContext(c *gin.Context) zerolog.Logger {
	if v, ok := c.Get(loggerKey); ok {
		if log, ok := v.(zerolog.Logger); ok {
			return log
		}
	}
	return zerolog.Nop()
}
