package handler

import "net/http"

// Health is intentionally unfinished in the clean subject.  The provider
// must implement the frozen task and choose its response details.
func Health(http.ResponseWriter, *http.Request) {
}
