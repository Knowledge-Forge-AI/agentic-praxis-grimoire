#!/usr/bin/env bash
set -eu

mkdir -p build
cc ${CFLAGS:-} -o build/app src/main.c
