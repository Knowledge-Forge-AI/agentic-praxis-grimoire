# APGR v0.8.1 independent consumer fixture

This documentation covers 0.9.0 qualification. This fixture preserves the
released v0.8.1 compatibility control lane and its checked-in requirement and
sums. The prospective v0.9.0 lane requires separate qualification in a
disposable copy; its exact commands and evidence are deferred until the amended
source is committed. Once 0.9.0 is published, a separate consumer lane can
verify that release through the public proxy without replacing this control.
The historical candidate-proxy procedure below applies to the v0.8.1 release
packet, not to v0.9.0 source preparation.

## Preserved v0.8.1 control and historical qualification procedure

This is an independent Go module for the APGR v0.8.1 public-consumer gate. It
requires the exact public module version in `fixture-go.mod` and imports only the
published `footprint` and `skills` packages. The checked-in control deliberately contains no
`replace`, source copy, internal package, private checkout, provider runtime,
or network service in this fixture.

The repository cannot contain a nested `go.mod`: Go module proxies reject a
module zip with one. Qualification therefore copies this immutable
`fixture-go.mod` to `go.mod` only in the disposable consumer directory.

For the historical v0.8.1 candidate qualification, the procedure required an
immutable local candidate module proxy prepared from that reviewed candidate:

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

For the released v0.8.1 control, run the same fixture from a fresh consumer directory
using the public Go proxy and checksum database:

```sh
GOPROXY=https://proxy.golang.org \
GOSUMDB=sum.golang.org \
go test -count=1 ./...
```

The post-publication evidence must record the resolved module zip and `go.mod`
checksums, module proxy readback, source/tag identity, Go toolchain, and full
test output. A candidate-proxy pass is not public publication evidence; the
historical release procedure required the fresh public-proxy run to succeed.
