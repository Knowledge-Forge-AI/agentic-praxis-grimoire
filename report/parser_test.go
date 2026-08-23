package report

import (
	"bytes"
	"errors"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

func TestParseRecordsStrictCanonicalContract(t *testing.T) {
	record := Record{Kind: schema.OperationalRecord, FormatVersion: 1, ID: "OPERATIONAL-REPORT-" + string(bytes.Repeat([]byte{'a'}, 64)), Project: "project", Phase: "APG95", Payload: []byte("payload\n")}
	encoded, err := buildRecord(record)
	if err != nil {
		t.Fatal(err)
	}
	parsed, err := ParseRecords(append(bytes.Clone(encoded), encoded...))
	if err != nil || len(parsed) != 2 {
		t.Fatalf("round trip: records=%d err=%v", len(parsed), err)
	}
	corruptions := [][]byte{
		encoded[:len(encoded)-1],
		append(bytes.Clone(encoded), []byte("suffix")...),
		bytes.Replace(bytes.Clone(encoded), []byte("PAYLOAD-SIZE-BYTES: 8"), []byte("PAYLOAD-SIZE-BYTES: 9"), 1),
		bytes.Replace(bytes.Clone(encoded), []byte("RECORD-TYPE: operational-report"), []byte("RECORD-TYPE: unknown-report"), 1),
		bytes.Replace(bytes.Clone(encoded), []byte("RECORD-FORMAT-VERSION: 1"), []byte("RECORD-FORMAT-VERSION: 2"), 1),
		append([]byte("legacy prefix\n"), encoded...),
	}
	for index, corrupted := range corruptions {
		if _, err := ParseRecords(corrupted); !errors.Is(err, ErrCompatibility) {
			t.Errorf("corruption %d error = %v", index, err)
		}
	}
}
