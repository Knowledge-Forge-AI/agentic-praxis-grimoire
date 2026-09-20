package service

// Service is a read-only review subject for mid-turn MCP recovery.
type Service struct{}

func (Service) Name() string { return "fixture" }
