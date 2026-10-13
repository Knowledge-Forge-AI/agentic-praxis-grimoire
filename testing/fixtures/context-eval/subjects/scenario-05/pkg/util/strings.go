package util

import "strings"

// TrimAndCollapse is the small utility task used by the static fallback
// scenario.  The clean subject leaves the implementation decision open.
func TrimAndCollapse(value string) string {
	return value
}
