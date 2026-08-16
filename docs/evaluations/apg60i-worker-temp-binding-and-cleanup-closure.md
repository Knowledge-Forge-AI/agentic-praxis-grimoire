# APG60I Worker Temporary-Root Binding and Cleanup Closure

APG60H remains adopted through explicit maintainer direction with its two known
worker temporary-storage review exceptions preserved historically. Its Claude
commit is `25ccebb288ba3530121a94b5f0df48a88d065fef`; its Codex completion is
`88284d43c5802156b8257b1b151042eae7369ab2`. The six managed record IDs remain
unchanged. APG60I corrects the exceptions forward rather than reinterpreting
APG60H.

The preserved IDs are
`GIT-DIFF-REPORT-e6f0215e70eaefdb62a1f1c13cbd411d36ad62adc48add4693371e74da7e6020`,
`OPERATIONAL-REPORT-e8fead10b48aecee65ccf246edadf9bc0b4a4fdbe8ff5ff9f2b2fe481ded62f1`,
`GIT-SHOW-REPORT-25ccebb288ba3530121a94b5f0df48a88d065fef`,
`OPERATIONAL-REPORT-ea987690c3385ae3fbbb6a2c6d92105180f33c158abbdab4a50c864647182d30`,
`GIT-SHOW-REPORT-88284d43c5802156b8257b1b151042eae7369ab2`, and
`OPERATIONAL-REPORT-1bdcad7b625fa6ab37c07ee66de7feb0083fd18dc4507f0c0ebf0cabb4c67761`.

## Worker temporary-storage correction

Failing-first controls reproduced both defects: a validated temporary-root
pathname could be rebound before path-based child creation, and a child could
remain when post-creation validation failed before cleanup ownership began.

The corrected contract opens every component of the caller-selected absolute
temporary root without following links, retains the final root and parent
descriptors, records the complete identity chain, and creates the operation
child descriptor-relatively beneath that exact object. Cleanup ownership now
begins before the first exclusive creation attempt. It removes entries without
following replacements, proves lexical absence, closes descriptors on every
path, and preserves a body failure as primary while attaching bounded cleanup
evidence. Final root revalidation detects pathname replacement before success.
Worker output and public errors expose no temporary path.

## Forward record correction and foundation

The APG60H current record's broad wording is corrected to the exact statement
“ADR 0036 does not exist.” ADR 0036 remains unused and absent.

The manifest and removal plan advance to schema 8 and the phase-history
manifest advances to APG60I schema 4. APG58 through APG60I are foundation;
APG61 is the authored state; APG61 and APG62 are terminal histories. APG60I
consumes exit `00089`; future exits are `00090` and `00091`.

All sixty CSS cases, their expected objects, and 300/600/900 remain unchanged.
CSS remains absent; ADR 0035 remains Rejected; development remains 28/28/28
and 14 stable / 14 provisional. Corrected public and active v0.4.0 remain
unchanged. Authorized shared scratch was used; no target command, candidate,
readiness, publication, deployment, APG61, or successor work ran.
