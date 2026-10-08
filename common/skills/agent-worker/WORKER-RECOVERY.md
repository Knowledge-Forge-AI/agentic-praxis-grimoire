# APGR worker recovery

1. Inspect the exact job status, partial output, terminal result and cleanup.
   These are separate facts. Record the parent's outcome through the facility.
2. Choose continued work, investigation, pool pause or deliberate abandonment.
   Silence alone proves neither death nor quota exhaustion.
3. Preserve partial edits and occupancy while cleanup is uncertain. Never infer
   cleanup from wrapper exit, a stale PID or cancellation acknowledgment.
4. Before a replacement writer starts, require proven cleanup and inspect the
   stable partial candidate. Link the predecessor and the adoption decision to
   the same logical task. Never replay a writing task blindly.
5. Pause an exhausted pool without quota polling or automatic retry. A healthy
   in-flight job is not cancelled solely because another admission failed.
6. Drain the exact owned jobs before returning stage authority. Report unknown
   cleanup and retained evidence; never erase a ledger to release capacity.

Triple-pool recovery never upgrades historical two-pool evidence. A Sonnet
quota failure pauses Sonnet only. Native Claude Sonnet interruption retains
its slot until terminal completion or observed parent-exit cleanup; a
foreground terminal hook may release the same reservation only once.
