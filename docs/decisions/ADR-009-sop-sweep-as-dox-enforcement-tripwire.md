# ADR-009: SOP Sweep As DOX Enforcement Tripwire

**Date:** 2026-06-14
**Status:** Accepted (implementation staged)
**Extends:** [EBA Control Plane Foundation Implementation Plan](../superpowers/plans/2026-06-13-eba-control-plane-foundation.md)

---

## Context

The first control-plane implementation added `./eba begin` and `./eba end`
turn gates, a path corridor, and a concrete SOP sweep. PR #13 then introduced
DOX, the `AGENTS.md` hierarchy that owns local work contracts and durable
instructions for each subtree.

After that change, the relationship between DOX and the SOP sweep needed to be
made explicit. They are not peer authorities. DOX is the judgment and contract
layer. The SOP sweep is a cheap mechanical tripwire that catches weakened
contracts before a turn closes.

The existing sweep also exposed two scaling problems:

- criticality was hardcoded centrally in `scripts/eba_control_plane.py`, blind
  to the DOX hierarchy;
- brittle central checks, such as a fixed ADR-008 status string, would keep
  accumulating as the repo gained more local contracts.

## Decision

The SOP sweep is DOX's enforcement tripwire, not a parallel authority.
Enforcement is two-tier:

### Tier 0: Immutable Code Floor

Tier 0 is a tiny root of trust implemented in `scripts/eba_control_plane.py`.
It contains the non-negotiable invariants and the gate's self-protection:

- root `AGENTS.md` must keep the turn gate, browser boundary, base64/image-byte
  boundary, and provider-attribution boundary;
- `docs/superpowers/project-sop.md` must keep SOP change control and turn
  command language;
- ADR-008 must continue to express the Playwright CLI browser boundary, even if
  it is explicitly superseded later;
- `.eba/policy.json` must not become a mutable hard-policy source;
- the gate must protect the minimum set of Tier-0 check names with a
  `sop_gate_integrity` check.

This floor stays hardcoded because the enforcer must be more separate and more
trustworthy than the instruction material it governs. Tier 0 is deliberately
small and should not grow into a central policy registry.

### Tier 1: DOX-Declared Invariants

Tier 1 is deferred to a follow-up PR. Each applicable `AGENTS.md` will declare
its own protected invariants. `end_turn` will walk the DOX read-chain for the
touched paths, collect those declarations, and verify that each declared
invariant survived before closing the turn.

Tier 1 moves criticality to the nearest owning DOX document. That is DOX's whole
thesis: local contracts should own local rules.

## Consequences

- The SOP sweep is re-homed under DOX as an enforcement mechanism.
- Tier 0 remains a code-enforced minimum and includes gate self-protection.
- Tier 1 removes the central hardcoded check list for ordinary local
  invariants.
- Tier 1 removes the ADR-008-title/status brittleness by letting future
  decisions declare their own protected rule locally instead of editing the
  control plane for each new critical invariant.
- Criticality becomes local to each `AGENTS.md`, and control-plane changes are
  reserved for the immutable floor and enforcement engine.

## Residual Limits

In-process self-checks are tamper-evident, not tamper-proof. `./eba end` loads
the control-plane code from the same working tree an agent may have edited, so
no in-repo self-check is a durable root of trust by itself.

Two known limits remain until Tier 1 and CI hardening land:

- Removing `scripts/eba_control_plane.py` from instruction-bearing detection in
  the same turn can still be hidden if the edited gate also removes or weakens
  the guard. Running `sop_gate_integrity` unconditionally makes accidental
  shrinkage visible, but it cannot defeat a malicious edit to the enforcer.
- A name-set integrity check catches removed Tier-0 checks, not hollowed checks.
  Tests must pin the protected behavior for each Tier-0 check, following the
  existing pattern that weakens a required invariant and expects closeout to
  block.

The durable backstop is CI plus human review of diffs to
`scripts/eba_control_plane.py`, which is now instruction-bearing.
`.github/workflows/validate.yml` runs `./eba dev validate`, including the
control-plane pinning tests, on PRs from a checked-out ref that the in-turn agent
is not editing and rerunning as its own authority.

## Staging And Trigger

Tier 1 is intentionally deferred to a follow-up PR. That work includes:

- an `AGENTS.md` protected-invariants declaration convention;
- a DOX-chain collector in `end_turn`;
- migration of ordinary hardcoded checks into local DOX declarations.

Build Tier 1 when an invariant would otherwise be hand-copied into
`concrete_sop_checks` for a third time.

## Related

- [ADR-008: Playwright CLI Is The Browser Engine](ADR-008-playwright-cli-browser-engine.md)
- [Project SOP](../superpowers/project-sop.md)
- [EBA Control Plane Foundation Implementation Plan](../superpowers/plans/2026-06-13-eba-control-plane-foundation.md)
