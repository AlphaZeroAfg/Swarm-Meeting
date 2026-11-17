# Task Negotiation Protocol (TNP) v0.1
**Genesis Architect:** Ehsanullah Rahimi (Ehsan)
**Status:** Approved & Finalized for v0.1 Implementation

## Core Principles
1. **Canonical Serialization (RFC 8785):** All cryptographic signatures and contract hashes must be computed over canonical JSON bytes to prevent formatting discrepancies.
2. **Strict State Machine Separation:** Pre-acceptance states (`EXPIRED`, `CANCELLED`) are strictly separated from post-acceptance execution failures (`BREACHED`, `DISPUTED`).
3. **Durable Replay Protection:** Processed message IDs and sender public keys are persistently stored in SQLite with atomic constraints to survive service restarts.
4. **Multi-tier Verification:** Verification types are explicitly declared in contracts (`STRUCTURAL`, `DETERMINISTIC`, `SUBJECTIVE`).
5. **Atomic Credit Reservation:** Credit limits ($D_0$) are atomically reserved prior to contract acceptance to prevent double-spending under concurrent requests.
