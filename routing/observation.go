package routing

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"unicode/utf8"
)

// Observation types.
const (
	ObservationTypeAvailability   = "availability"
	ObservationTypeAuthentication = "authentication"
	ObservationTypeCooldown       = "cooldown"
	ObservationTypeQuota          = "quota"
)

// Observation state values.
const (
	StateAvailable      = "available"
	StateUnavailable    = "unavailable"
	StateUsable         = "usable"
	StateUnusable       = "unusable"
	StateExhausted      = "exhausted"
	StateHealthy        = "healthy"
	StateConstrained    = "constrained"
	StateActiveCooldown = "active_cooldown"
	StateCooldown       = "cooldown"
	StateUnknown        = "unknown"
)

// OperationalObservation represents an observed provider availability, auth, quota, or cooldown record.
type OperationalObservation struct {
	ObservationID   string         `json:"observation_id"`
	Producer        string         `json:"producer"`
	ObservationType string         `json:"observation_type"`
	Provider        string         `json:"provider"`
	Profile         *string        `json:"profile,omitempty"`
	Timestamp       float64        `json:"timestamp"`
	ExpiresAt       *float64       `json:"expires_at,omitempty"`
	StateValue      string         `json:"state_value"`
	Detail          map[string]any `json:"detail,omitempty"`
	Digest          string         `json:"digest,omitempty"`
}

// IsActive reports whether the observation is currently active relative to the given timestamp.
func (obs OperationalObservation) IsActive(now float64) bool {
	if obs.ExpiresAt == nil {
		return true
	}
	return now < *obs.ExpiresAt
}

type pythonFloat float64

func (f pythonFloat) MarshalJSON() ([]byte, error) {
	s := strconv.FormatFloat(float64(f), 'f', -1, 64)
	if !strings.Contains(s, ".") && !strings.Contains(s, "e") && !strings.Contains(s, "E") {
		s += ".0"
	}
	return []byte(s), nil
}

type canonicalObservationPayload struct {
	Detail          map[string]any `json:"detail"`
	ExpiresAt       *pythonFloat   `json:"expires_at"`
	ObservationID   string         `json:"observation_id"`
	ObservationType string         `json:"observation_type"`
	Producer        string         `json:"producer"`
	Profile         *string        `json:"profile"`
	Provider        string         `json:"provider"`
	StateValue      string         `json:"state_value"`
	Timestamp       pythonFloat    `json:"timestamp"`
}

// CanonicalDigest computes the deterministic SHA-256 digest over the compact,
// key-sorted JSON representation matching the APGR Python runtime oracle.
func CanonicalDigest(obs OperationalObservation) (string, error) {
	var exp *pythonFloat
	if obs.ExpiresAt != nil {
		f := pythonFloat(*obs.ExpiresAt)
		exp = &f
	}

	var detail map[string]any
	if len(obs.Detail) > 0 {
		detail = obs.Detail
	}

	payload := canonicalObservationPayload{
		Detail:          detail,
		ExpiresAt:       exp,
		ObservationID:   obs.ObservationID,
		ObservationType: obs.ObservationType,
		Producer:        obs.Producer,
		Profile:         obs.Profile,
		Provider:        obs.Provider,
		StateValue:      obs.StateValue,
		Timestamp:       pythonFloat(obs.Timestamp),
	}

	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(payload); err != nil {
		return "", err
	}
	raw := bytes.TrimRight(buf.Bytes(), "\n")

	var out bytes.Buffer
	for i := 0; i < len(raw); {
		if raw[i] < 0x80 {
			out.WriteByte(raw[i])
			i++
			continue
		}
		r, size := utf8.DecodeRune(raw[i:])
		i += size
		if r <= 0xFFFF {
			fmt.Fprintf(&out, "\\u%04x", r)
		} else {
			r -= 0x10000
			high := 0xD800 + (r >> 10)
			low := 0xDC00 + (r & 0x3FF)
			fmt.Fprintf(&out, "\\u%04x\\u%04x", high, low)
		}
	}

	sum := sha256.Sum256(out.Bytes())
	return hex.EncodeToString(sum[:]), nil
}
