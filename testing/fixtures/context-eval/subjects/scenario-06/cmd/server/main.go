package main

import (
	"encoding/json"
	"net/http"
	"os/exec"
)

// queryStore is a dependency-free bridge to the source-owned SQLite fixture.
// The provider task owns the HTTP handler and integration assertions; no
// third-party Go SQLite driver is assumed by this clean subject.
func queryStore(path string) ([]string, error) {
	output, err := exec.Command("python3", "tools/query_sqlite.py", path).Output()
	if err != nil {
		return nil, err
	}
	var names []string
	if err := json.Unmarshal(output, &names); err != nil {
		return nil, err
	}
	return names, nil
}

func handler(http.ResponseWriter, *http.Request) {}
