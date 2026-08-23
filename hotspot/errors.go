package hotspot

import (
	"errors"
	"fmt"
)

var (
	ErrInvalidRequest = errors.New("invalid hotspot request")
	ErrRootSafety     = errors.New("hotspot root safety violation")
	ErrLimitExceeded  = errors.New("hotspot scan limit exceeded")
	ErrFileDrift      = errors.New("hotspot file drift")
	ErrUnreadable     = errors.New("hotspot file unreadable")
	ErrInvalidReport  = errors.New("invalid hotspot report")
)

type scanError struct {
	class  error
	detail string
}

func (err scanError) Error() string { return fmt.Sprintf("%v: %s", err.class, err.detail) }
func (err scanError) Unwrap() error { return err.class }

func invalidRequest(detail string) error { return scanError{ErrInvalidRequest, detail} }
func rootSafety(detail string) error     { return scanError{ErrRootSafety, detail} }
func limitExceeded(detail string) error  { return scanError{ErrLimitExceeded, detail} }
func fileDrift(path string) error        { return scanError{ErrFileDrift, path} }
func unreadable(path string) error       { return scanError{ErrUnreadable, path} }
func invalidReport(detail string) error  { return scanError{ErrInvalidReport, detail} }
