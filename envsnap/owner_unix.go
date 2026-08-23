//go:build darwin || linux

package envsnap

import (
	"errors"
	"os"
	"syscall"
)

func ownerChecksAvailable() bool { return true }

func currentProcessUID() uint32 { return uint32(os.Getuid()) }

func processIsAlive(pid int) bool {
	if pid <= 0 {
		return false
	}
	err := syscall.Kill(pid, syscall.Signal(0))
	return err == nil || errors.Is(err, syscall.EPERM)
}
