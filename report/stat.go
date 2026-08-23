package report

import (
	"fmt"
	"os"
	"reflect"
)

type fileIdentity struct {
	dev, ino, mode, uid, gid, nlink, size, mtimeNS, ctimeNS int64
}

func identityFor(info os.FileInfo) (fileIdentity, error) {
	value := reflect.Indirect(reflect.ValueOf(info.Sys()))
	if !value.IsValid() {
		return fileIdentity{}, fmt.Errorf("%w: filesystem identity is unavailable", ErrUnsupported)
	}
	result := fileIdentity{}
	fields := []struct {
		name   string
		target *int64
	}{
		{"Dev", &result.dev}, {"Ino", &result.ino}, {"Mode", &result.mode}, {"Uid", &result.uid},
		{"Gid", &result.gid}, {"Nlink", &result.nlink}, {"Size", &result.size},
	}
	for _, item := range fields {
		field := value.FieldByName(item.name)
		converted, ok := integerValue(field)
		if !ok {
			return fileIdentity{}, fmt.Errorf("%w: filesystem identity is unavailable", ErrUnsupported)
		}
		*item.target = converted
	}
	mtime, ok := timespecNS(value, "Mtim", "Mtimespec")
	if !ok {
		return fileIdentity{}, fmt.Errorf("%w: filesystem modification time is unavailable", ErrUnsupported)
	}
	ctime, ok := timespecNS(value, "Ctim", "Ctimespec")
	if !ok {
		return fileIdentity{}, fmt.Errorf("%w: filesystem change time is unavailable", ErrUnsupported)
	}
	result.mtimeNS, result.ctimeNS = mtime, ctime
	return result, nil
}

func integerValue(value reflect.Value) (int64, bool) {
	if !value.IsValid() {
		return 0, false
	}
	switch value.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return value.Int(), true
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return int64(value.Uint()), true
	default:
		return 0, false
	}
}

func timespecNS(value reflect.Value, names ...string) (int64, bool) {
	for _, name := range names {
		field := value.FieldByName(name)
		if !field.IsValid() {
			continue
		}
		seconds, secondsOK := integerValue(field.FieldByName("Sec"))
		nanoseconds, nanosecondsOK := integerValue(field.FieldByName("Nsec"))
		if secondsOK && nanosecondsOK {
			return seconds*1_000_000_000 + nanoseconds, true
		}
	}
	return 0, false
}

func (identity fileIdentity) String() string {
	return fmt.Sprintf("%d:%d:%d:%d:%d:%d:%d:%d:%d", identity.dev, identity.ino, identity.mode, identity.uid, identity.gid, identity.nlink, identity.size, identity.mtimeNS, identity.ctimeNS)
}
