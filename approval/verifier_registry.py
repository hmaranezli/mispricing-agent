"""approval/verifier_registry.py — production crypto verifier identity boundary (public-key only).

Production verification may use ONLY an explicitly pinned verifier identity resolved through a strict
registry. Arbitrary runtime injection is structurally rejected: a callable, lambda, mock, dummy, or
always-true function cannot be resolved as a production verifier. Resolution is deterministic and
fails closed for unknown / missing / unpinned identity, version mismatch, and fingerprint mismatch.

The output is PASSIVE: a frozen ``ResolveResult(valid, reason, identity)`` carrying no callable
handle. A ``valid=True`` resolution authorizes NOTHING — it only states that a pinned identity
matched its pinned version and fingerprint. No DB, no S1 append, no matrix, no paper/live, no
trading, no wallet/signing, no capacity follows from it.
"""
from __future__ import annotations

from dataclasses import dataclass

# Identity substrings that mark a verifier as test-only; never resolvable in production mode.
TEST_ONLY_TOKENS = (
    "mock",
    "dummy",
    "fake",
    "stub",
    "test",
    "always_true",
    "alwaystrue",
    "lambda",
    "anon",
)


@dataclass(frozen=True)
class PinnedVerifier:
    """An explicitly pinned production verifier descriptor (no callable, public-key-only)."""

    identity: str
    version: str
    fingerprint: str
    test_only: bool = False


@dataclass(frozen=True)
class ResolveResult:
    """Passive, immutable resolution outcome. Never a callable/authorization handle."""

    valid: bool
    reason: str
    identity: str = ""


def resolve_production_verifier(
    identity, *, version: str, fingerprint: str, registry
) -> ResolveResult:
    """Resolve a production verifier from the pinned registry. Fails closed on any ambiguity.

    Returns ``valid=True`` only when the identity is a pinned, non-test, version- and
    fingerprint-matched registry entry — and even then authorizes nothing.
    """
    # Reject any non-string identity FIRST — no callable/lambda may enter the production path.
    if not isinstance(identity, str):
        if callable(identity):
            if getattr(identity, "__name__", "") == "<lambda>":
                return ResolveResult(False, "anonymous_verifier_rejected")
            return ResolveResult(False, "callable_injection")
        return ResolveResult(False, "non_string_identity")

    if identity == "":
        return ResolveResult(False, "missing_verifier_identity")

    pinned = registry.get(identity)
    if pinned is None:
        return ResolveResult(False, "unknown_verifier_identity")

    if pinned.fingerprint == "":
        return ResolveResult(False, "unpinned_verifier_identity")

    if pinned.test_only or any(tok in identity.lower() for tok in TEST_ONLY_TOKENS):
        return ResolveResult(False, "test_verifier_rejected_in_production")

    if version != pinned.version:
        return ResolveResult(False, "verifier_version_mismatch")

    if fingerprint != pinned.fingerprint:
        return ResolveResult(False, "verifier_fingerprint_mismatch")

    return ResolveResult(True, "", identity)
