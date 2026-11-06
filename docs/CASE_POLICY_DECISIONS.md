# Case policy decisions — ADR-002 / ADR-006 follow-up

Status: proposed engineering contracts, pending owner review and counsel where
specified. The referenced ADR-002 and ADR-006 were not present in this checkout.
This note does not replace those ADRs or claim that THUS Cases are implemented in Engram.

## ADR-002: deletion and frozen evidence

Proposed contract: freezing preserves the original prediction and its chronology;
it does not promise perpetual retention of customer evidence. Keep evidence bodies
and excerpts in separately deletable storage. Frozen Cases refer to revision IDs
and precise spans; any materialized excerpts, exports and caches participate in the
same deletion process. Access checks apply when resolving evidence, including old Cases.

Deletion should revoke retrieval immediately, propagate to indexes, derived
assertions and learned precedents, and leave only an authorized minimal tombstone
and deletion audit record. Display “evidence deleted/unavailable”; never silently
substitute a newer source or claim the original Case remains fully reproducible.
A deletion-aware Case revision records what changed without retaining the deleted
excerpt inside the revision history. Prevent backups from resurrecting deleted data
by replaying a deletion ledger before serving restored content.

Counsel and the customer policy owner must decide retention periods, lawful holds,
backup expiry, scope of derived-data deletion, and what metadata or commitments may
remain. These are open requirements, not legal conclusions or shipped guarantees.
Do not use customer evidence in frozen production Cases until this contract and
its deletion/restore tests are approved and implemented.

## ADR-006: correction verification

Proposed default: an author may suggest a correction to their own Case, but an
independent authorized actor must verify it before it becomes reusable verified
memory. The verifier must differ from the Case author and correction proposer;
verification cannot broaden source permissions. Record actor IDs, evidence,
reason, timestamp and version. Reject self-verification server-side. Unverified
corrections stay visibly pending and are excluded from verified-memory retrieval.
Owner approval and enforcement remain pending; no exception policy is assumed.

## ADR-006: tamper evidence

Proposed default: frozen Cases receive a versioned SHA-256 digest over a defined
canonical manifest (prediction, as-of time, evidence revision references, model and
policy versions). Keep mutable/deletable evidence bodies outside that manifest.
Define canonical serialization and schema version before implementation. A hash
stored beside editable data alone cannot prove integrity against an actor who can
rewrite both; anchor it in an independently controlled append-only audit mechanism.
Never describe a digest as a signature, proof of correctness, or immutable storage.

Deletion creates an explicit revision/tombstone with its own audit event and digest;
it must not leave deleted excerpts in a hashed payload. Counsel must also review
whether retained references/digests disclose customer information. Hashing is not
an exemption from deletion. This design remains pending acceptance and implementation.

## Required validation before production Cases

- Delete evidence after freezing: no excerpts survive in Cases, indexes, caches,
  exports, derived memory or restored serving data; the UI explains missing evidence.
- Enforce tenant/source authorization for historical Cases and corrections.
- Reject self-verification; accept an authorized independent verifier with audit provenance.
- Detect manifest alteration against the independent anchor; validate canonical
  serialization and the deletion revision path without retaining deleted content.
