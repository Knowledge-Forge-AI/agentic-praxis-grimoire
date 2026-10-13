package auth

// Authorize is reviewed when the MCP adapter is unavailable before launch.
func Authorize(token string) bool { return token != "" }
