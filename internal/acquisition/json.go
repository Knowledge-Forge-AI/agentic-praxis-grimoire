package acquisition

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"unicode/utf8"
)

// StrictJSON rejects duplicate fields at every depth and trailing values before
// typed decoding. Depth is explicitly bounded independently of message bytes.
func StrictJSON(data []byte, target any) error {
	if !utf8.Valid(data) {
		return errors.New("JSON_INVALID_UTF8")
	}
	d := json.NewDecoder(bytes.NewReader(data))
	d.UseNumber()
	var walk func(int) error
	walk = func(depth int) error {
		if depth > 32 {
			return errors.New("JSON_DEPTH_LIMIT")
		}
		token, err := d.Token()
		if err != nil {
			return err
		}
		if delim, ok := token.(json.Delim); ok {
			switch delim {
			case '{':
				seen := map[string]bool{}
				for d.More() {
					key, err := d.Token()
					if err != nil {
						return err
					}
					s, ok := key.(string)
					if !ok || seen[s] {
						return errors.New("JSON_DUPLICATE_FIELD")
					}
					seen[s] = true
					if err = walk(depth + 1); err != nil {
						return err
					}
				}
			case '[':
				for d.More() {
					if err = walk(depth + 1); err != nil {
						return err
					}
				}
			default:
				return errors.New("JSON_INVALID_SHAPE")
			}
			_, err = d.Token()
			return err
		}
		return nil
	}
	if err := walk(0); err != nil {
		return err
	}
	if _, err := d.Token(); err != io.EOF {
		return errors.New("JSON_TRAILING_DATA")
	}
	typed := json.NewDecoder(bytes.NewReader(data))
	typed.DisallowUnknownFields()
	typed.UseNumber()
	return typed.Decode(target)
}
