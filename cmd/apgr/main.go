package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/cli"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	signals := make(chan os.Signal, 1)
	signal.Notify(signals, os.Interrupt, syscall.SIGTERM, syscall.SIGHUP)
	defer signal.Stop(signals)
	interrupted := make(chan os.Signal, 1)
	go func() {
		value := <-signals
		interrupted <- value
		cancel()
	}()
	exit := cli.RunWithInput(ctx, os.Args[1:], os.Stdin, os.Stdout, os.Stderr)
	select {
	case value := <-interrupted:
		if value == os.Interrupt {
			exit = 130
		} else {
			exit = 1
		}
	default:
	}
	os.Exit(exit)
}
