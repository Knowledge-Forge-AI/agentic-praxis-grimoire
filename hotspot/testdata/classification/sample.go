package sample

func Decision(a, b int) int {
	if a > 0 && b > 0 {
		return a + b
	}
	return 0
}

var Closure = func(value int) int { return value + 1 }
