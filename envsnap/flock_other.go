//go:build !darwin && !linux

package envsnap

import "os"

func tryExclusiveLock(file *os.File) error {
	return os.ErrInvalid
}

func unlockExclusive(file *os.File) error {
	return os.ErrInvalid
}

func lockBusy(err error) bool { return false }
