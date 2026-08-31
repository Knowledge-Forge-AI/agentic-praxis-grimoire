package footprint_test

import (
	"context"
	"errors"
	"reflect"
	"testing"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

func sourceForProjection() footprint.Record {
	record := baseRecord()
	record.Components = append(record.Components,
		component(footprint.ComponentSupportMaterial, "support", 5),
		component(footprint.ComponentMaterializedBundle, "bundle", 6),
		component(footprint.ComponentAuthority, "authority-note", 7),
	)
	return record
}

func TestProjectExactPreservesSourceAndBindsCanonicalIdentity(t *testing.T) {
	source := sourceForProjection()
	projection, err := footprint.Project(context.Background(), footprint.ProjectRequest{
		Source:   source,
		Fidelity: footprint.FidelityExact,
	})
	requireNoError(t, err)
	canonical, err := source.CanonicalJSON()
	requireNoError(t, err)
	normalizedSource, err := footprint.DecodeRecord(canonical)
	requireNoError(t, err)
	if projection.SchemaVersion != footprint.ProjectionSchemaV1 || projection.CanonicalSourceSchema != footprint.FootprintSchemaV1 {
		t.Fatalf("projection schema identities = %#v", projection)
	}
	if projection.CanonicalSourceDigest != footprint.FingerprintRecord(source) || projection.CanonicalSourceSize != int64(len(canonical)) {
		t.Fatalf("source binding = digest %q, size %d; want %q, %d", projection.CanonicalSourceDigest, projection.CanonicalSourceSize, footprint.FingerprintRecord(source), len(canonical))
	}
	if len(projection.OmittedFields) != 0 || !reflect.DeepEqual(projection.Record, normalizedSource) {
		t.Fatalf("exact projection changed source: omitted=%#v record=%#v", projection.OmittedFields, projection.Record)
	}
	if projection.Sensitivity != source.Sensitivity || projection.Retention != source.Retention {
		t.Fatalf("exact labels = %q/%q, want %q/%q", projection.Sensitivity, projection.Retention, source.Sensitivity, source.Retention)
	}

	encoded, err := projection.CanonicalJSON()
	requireNoError(t, err)
	decoded, err := footprint.DecodeProjection(encoded)
	requireNoError(t, err)
	if !reflect.DeepEqual(decoded, projection) {
		t.Fatalf("decoded projection differs: %#v vs %#v", decoded, projection)
	}
	if footprint.FingerprintProjection(projection) != decoded.Fingerprint() {
		t.Fatal("projection fingerprint changed across decode")
	}
}

func TestProjectLosslessAndSummarizedFidelityDeclarePermittedOmissions(t *testing.T) {
	source := sourceForProjection()
	lossless, err := footprint.Project(nil, footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityLosslessStructural})
	requireNoError(t, err)
	if len(lossless.OmittedFields) != 0 || len(lossless.Record.Components) != len(source.Components) {
		t.Fatalf("lossless projection unexpectedly omitted content: %#v", lossless)
	}

	lossy, err := footprint.Project(nil, footprint.ProjectRequest{
		Source:        source,
		Fidelity:      footprint.FidelitySummarizedLossy,
		OmittedFields: []string{"support", "description"},
		Sensitivity:   footprint.SensitivityConfidential,
		Retention:     footprint.RetentionImmutable,
	})
	requireNoError(t, err)
	if !reflect.DeepEqual(lossy.OmittedFields, []string{"description", "support"}) {
		t.Fatalf("omitted fields = %#v", lossy.OmittedFields)
	}
	if lossy.Sensitivity != footprint.SensitivityConfidential || lossy.Retention != footprint.RetentionImmutable {
		t.Fatalf("upgraded labels = %q/%q", lossy.Sensitivity, lossy.Retention)
	}
	for _, item := range lossy.Record.Components {
		if item.Name == "description" || item.Name == "support" {
			t.Fatalf("permitted component survived omission: %#v", item)
		}
	}
	if !hasComponentNamed(lossy.Record, "body") || !hasComponentNamed(lossy.Record, "authority-note") {
		t.Fatalf("projection dropped non-omitted or consequence-bearing content: %#v", lossy.Record.Components)
	}

	alias, err := footprint.Project(nil, footprint.ProjectRequest{
		Source:    source,
		Fidelity:  footprint.FidelitySummarizedLossy,
		Omissions: []string{"support"},
	})
	requireNoError(t, err)
	if len(alias.OmittedFields) != 1 || alias.OmittedFields[0] != "support" {
		t.Fatalf("legacy omissions alias = %#v", alias.OmittedFields)
	}
}

func hasComponentNamed(record footprint.Record, name string) bool {
	for _, item := range record.Components {
		if item.Name == name {
			return true
		}
	}
	return false
}

func TestProjectRefusesConsequenceBearingAndBindingOmissions(t *testing.T) {
	source := sourceForProjection()
	fields := []string{
		"authority",
		"kind:authority",
		"authority-note",
		"security",
		"failure",
		"diagnostic",
		"finding",
		"refusal",
		"uncertainty",
		"unavailable",
		"sensitivity",
		"retention",
		"source_references",
		"observation",
		"components",
	}
	for _, field := range fields {
		t.Run(field, func(t *testing.T) {
			_, err := footprint.Project(nil, footprint.ProjectRequest{
				Source:        source,
				Fidelity:      footprint.FidelitySummarizedLossy,
				OmittedFields: []string{field},
			})
			requireErrorIs(t, err, footprint.ErrConsequenceBearingOmissionRefused)
		})
	}
}

func TestProjectRejectsInvalidFidelityDuplicateOmissionAndLabelDowngrade(t *testing.T) {
	source := sourceForProjection()
	cases := []struct {
		name    string
		request footprint.ProjectRequest
		want    error
	}{
		{
			name:    "unknown fidelity",
			request: footprint.ProjectRequest{Source: source, Fidelity: footprint.Fidelity("future")},
			want:    footprint.ErrUnknownVocabulary,
		},
		{
			name:    "exact omission",
			request: footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityExact, OmittedFields: []string{"description"}},
			want:    footprint.ErrInvalidType,
		},
		{
			name:    "lossless omission",
			request: footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityLosslessStructural, OmittedFields: []string{"description"}},
			want:    footprint.ErrInvalidType,
		},
		{
			name:    "sensitivity downgrade",
			request: footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityExact, Sensitivity: footprint.SensitivityPublic},
			want:    footprint.ErrSensitivityDowngrade,
		},
		{
			name:    "retention downgrade",
			request: footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityExact, Retention: footprint.RetentionEphemeral},
			want:    footprint.ErrRetentionDowngrade,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := footprint.Project(nil, tc.request)
			requireErrorIs(t, err, tc.want)
		})
	}
}

func TestProjectPermitsIdenticalOmissionInCompatibilityAlias(t *testing.T) {
	source := sourceForProjection()
	projection, err := footprint.Project(nil, footprint.ProjectRequest{
		Source:        source,
		Fidelity:      footprint.FidelitySummarizedLossy,
		OmittedFields: []string{"support"},
		Omissions:     []string{"support"},
	})
	requireNoError(t, err)
	if len(projection.OmittedFields) != 1 || projection.OmittedFields[0] != "support" {
		t.Fatalf("expected deduplicated omissions [support], got %#v", projection.OmittedFields)
	}
}

func TestDecodeAndValidateProjectionEnforceConsequenceBearingAndLosslessInvariants(t *testing.T) {
	source := sourceForProjection()
	exactProj, err := footprint.Project(context.Background(), footprint.ProjectRequest{
		Source:   source,
		Fidelity: footprint.FidelityExact,
	})
	requireNoError(t, err)

	// Lossless structural with omissions
	losslessWithOmission := exactProj
	losslessWithOmission.Fidelity = footprint.FidelityLosslessStructural
	losslessWithOmission.OmittedFields = []string{"support"}
	requireErrorIs(t, footprint.ValidateProjection(losslessWithOmission), footprint.ErrInvalidType)
	losslessJSON, err := losslessWithOmission.CanonicalJSON()
	if err == nil {
		_, err = footprint.DecodeProjection(losslessJSON)
		requireErrorIs(t, err, footprint.ErrInvalidType)
	}

	// Consequence-bearing omission: authority
	authorityOmission := exactProj
	authorityOmission.Fidelity = footprint.FidelitySummarizedLossy
	authorityOmission.OmittedFields = []string{"authority"}
	requireErrorIs(t, footprint.ValidateProjection(authorityOmission), footprint.ErrConsequenceBearingOmissionRefused)

	// Consequence-bearing omission: security
	securityOmission := exactProj
	securityOmission.Fidelity = footprint.FidelitySummarizedLossy
	securityOmission.OmittedFields = []string{"security"}
	requireErrorIs(t, footprint.ValidateProjection(securityOmission), footprint.ErrConsequenceBearingOmissionRefused)

	// Duplicate omitted fields in struct
	dupOmission := exactProj
	dupOmission.Fidelity = footprint.FidelitySummarizedLossy
	dupOmission.OmittedFields = []string{"support", "support"}
	requireErrorIs(t, footprint.ValidateProjection(dupOmission), footprint.ErrDuplicateField)
}

func TestProjectHonorsCancellationAndDeadline(t *testing.T) {
	source := sourceForProjection()
	cancelled, cancel := context.WithCancel(context.Background())
	cancel()
	result, err := footprint.Project(cancelled, footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityExact})
	if !reflect.DeepEqual(result, footprint.Projection{}) {
		t.Fatalf("cancelled projection returned partial result: %#v", result)
	}
	requireErrorIs(t, err, footprint.ErrContextCancelled)
	requireErrorIs(t, err, context.Canceled)

	deadline, cancel := context.WithDeadline(context.Background(), time.Unix(0, 0))
	defer cancel()
	_, err = footprint.Project(deadline, footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityExact})
	requireErrorIs(t, err, context.DeadlineExceeded)
}

func TestValidateProjectionRejectsForgedBindingShape(t *testing.T) {
	source := sourceForProjection()
	projection, err := footprint.Project(nil, footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityExact})
	requireNoError(t, err)
	projection.CanonicalSourceDigest = "fp-sha256:not-a-digest"
	requireErrorIs(t, footprint.ValidateProjection(projection), footprint.ErrInvalidType)

	projection, err = footprint.Project(nil, footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelityExact})
	requireNoError(t, err)
	projection.CanonicalSourceSize = 0
	requireErrorIs(t, footprint.ValidateProjection(projection), footprint.ErrInvalidType)

	if _, err := footprint.Project(nil, footprint.ProjectRequest{Source: footprint.Record{}, Fidelity: footprint.FidelityExact}); !errors.Is(err, footprint.ErrInvalidRecord) {
		t.Fatalf("invalid projection source error = %v", err)
	}
}
