package footprint

import "errors"

// Sentinel errors returned by footprint operations. Callers should use
// errors.Is so that additional diagnostic context can be added without
// changing the public error contract.
var (
	ErrInvalidRecord                     = errors.New("invalid footprint record")
	ErrInvalidComparison                 = errors.New("invalid footprint comparison")
	ErrInvalidProjection                 = errors.New("invalid footprint projection")
	ErrInvalidRegistry                   = errors.New("invalid footprint component registry")
	ErrInvalidControlMapping             = errors.New("invalid footprint capacity-control mapping")
	ErrUnknownSchema                     = errors.New("unknown footprint schema")
	ErrUnknownVersion                    = ErrUnknownSchema
	ErrUnknownField                      = errors.New("unknown footprint field")
	ErrDuplicateField                    = errors.New("duplicate footprint field")
	ErrInvalidUTF8                       = errors.New("footprint input is not valid UTF-8")
	ErrTrailingData                      = errors.New("trailing footprint data")
	ErrUnknownVocabulary                 = errors.New("unknown footprint vocabulary")
	ErrUnknownMapping                    = errors.New("unknown footprint mapping")
	ErrMissingField                      = errors.New("missing footprint field")
	ErrInvalidType                       = errors.New("invalid footprint field type")
	ErrMalformedJSON                     = errors.New("malformed footprint JSON")
	ErrNonCanonical                      = errors.New("noncanonical footprint JSON")
	ErrUnavailableMetric                 = errors.New("footprint metric is unavailable")
	ErrUnitMismatch                      = errors.New("footprint metric units do not match")
	ErrIncompatibleComparison            = errors.New("incompatible footprint comparison")
	ErrConsequenceBearingOmissionRefused = errors.New("omission of consequence-bearing footprint content refused")
	ErrSensitivityDowngrade              = errors.New("projection would downgrade sensitivity")
	ErrRetentionDowngrade                = errors.New("projection would downgrade retention")
	ErrIntegerOverflow                   = errors.New("footprint integer overflow")
	ErrContextCancelled                  = errors.New("footprint operation cancelled")
)
