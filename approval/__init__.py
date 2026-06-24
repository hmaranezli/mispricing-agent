"""approval/ — isolated human-approval / operator-decision verification surface.

This package contains ONLY passive, public-key-only verification of inert offline-signed approval
packages. It holds no DB, no S1 dependency, no network, no private-key handling, and authorizes
nothing. A valid verification result is evidence at most, never an execution or authorization.
"""
