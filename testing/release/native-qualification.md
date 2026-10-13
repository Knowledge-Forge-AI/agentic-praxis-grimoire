# Native qualification evidence contract

Status: source implementation candidate; hosted acceptance pending.

The native workflow must qualify Darwin ARM64, Linux x64 and Linux ARM64 on
their actual hosts. Each lane retains Go compiler/build metadata, test/vet/race
output, reproducibility evidence and real Nix compiler/store/profile smoke.
An absent or skipped lane cannot satisfy qualification.

The assembler receives immutable GitHub artifact IDs and SHA-256 digests,
verifies the archived bytes and extracted members, and packages only those
native binaries. The canonical set is three wheels, one sdist, four npm tarballs
and three binaries. Native consumer jobs install the sealed wheel and npm bytes
offline and check the bundle again. They do not repackage or rebuild.

The fourteen scan views are source, eleven distributables, the sdist-derived
installation and the conditional Python dependency. The derived installation is
native hosted scan evidence, never a replacement release asset. Scanner policy
requires the pinned tools, complete catalogs, fresh Grype database identity and
no unwaived High/Critical finding. Lower severity findings remain visible.
The source distribution (sdist) scan evaluates coverage across both raw archive
and derived installation views: while uninstalled source archives may exhibit an
expected raw cataloging gap for Python packages, qualification requires the
derived installation and scan to pass, verified Python package coverage, and complete coverage
union. All non-sdist views remain strictly gap-free. Even if the raw source
archive reports complete coverage, any derived installation gap remains
rejected.

Both sdist views require typed inventories: nonempty type names, positive
integer counts, and a type-count sum equal to `package_count`. This validator
requirement is stricter than the scanner producer, which counts untyped Syft
artifacts in `package_count` without including them in `types`. Such an inventory
is rejected as count-inconsistent; it cannot qualify through the coverage union.
The union rule does not excuse unknown or unaccounted packages.

The aggregate verifies both job statuses and receipts; it rejects missing,
duplicate, failed, skipped or mismatched source/platform/artifact identities.
Source-only unit fixtures cover the parser, receipt, seal, archive transfer and
operator boundaries. They establish no hosted runner or scanner success.

The ordinary static suite, governance, public projection policy, govulncheck and
CodeQL remain active. Publication and required-check settings changes are
separate attended actions. Expired fourteen-day PR artifacts require fresh
hosted qualification. The old local publication build path cannot substitute
for native hosted proof.
