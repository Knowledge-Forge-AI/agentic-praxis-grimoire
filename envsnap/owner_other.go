//go:build !darwin && !linux

package envsnap

func ownerChecksAvailable() bool { return false }

func currentProcessUID() uint32 { return 0 }

func processIsAlive(pid int) bool {
	return false
}
