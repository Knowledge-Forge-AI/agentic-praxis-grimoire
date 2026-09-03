# APGR v0.8.1 independent consumer fixture

This is an independent Go module for the APGR v0.8.1 public-consumer gate. It
requires the exact public module version in `fixture-go.mod` and imports only the
published `footprint` and `skills` packages. There is deliberately no
`replace`, source copy, internal package, private checkout, provider runtime,
or network service in this fixture.

The repository cannot contain a nested `go.mod`: Go module proxies reject a
module zip with one. Qualification therefore copies this immutable
`fixture-go.mod` to `go.mod` only in the disposable consumer directory.

The work-stage qualification must run this fixture against an immutable local
candidate module proxy prepared from the exact reviewed release candidate:

```sh
GOPROXY="${APGR_IMMUTABLE_MODULE_PROXY_URI}" \
GOSUMDB=off \
go test -count=1 ./...
```

The caller-supplied immutable module-proxy URI names evidence storage, not a development replace
or a mutable checkout. Record the exact candidate source identity, module zip
and `go.mod` SHA-256 values, Go toolchain (`go version`), `go env` values
relevant to module resolution, and complete test output in the private release
packet. Do not add a `go.sum` generated from an unpublished or mutable source.

After publication, rerun the same fixture from a fresh consumer directory
using the public Go proxy and checksum database:

```sh
GOPROXY=https://proxy.golang.org \
GOSUMDB=sum.golang.org \
go test -count=1 ./...
```

The post-publication evidence must record the resolved module zip and `go.mod`
checksums, module proxy readback, source/tag identity, Go toolchain, and full
test output. A candidate-proxy pass is not public publication evidence; the
release is complete only after the fresh public-proxy run succeeds.
