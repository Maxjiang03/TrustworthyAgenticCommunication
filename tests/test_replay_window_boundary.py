"""The replay cache must not release a `jti` while the proof is still fresh.

ADR 0027 fixes ONE `Δ` for all three consumers: the `jti` cache TTL, the DPoP
`iat` acceptance window, and INV freshness at the boundary. `is_fresh` accepts
a closed window (`|now - iat| <= Δ`), while the cache evicted on
`expires_at <= now` -- a half-open one. At exactly `t + Δ` the two disagreed:
the proof was still fresh, the cache entry was already gone, and the replay
`B3⁺` exists to block was ADMITTED.

That single cell -- `F3 dpop-captured-proof-replay` -- is the only row in the
entire §E.4 matrix where `B3⁺` differs from `B3`, so a one-second hole at the
window edge is a hole in the arm's whole reason to exist. ADR 0044.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

from src.harness import frozen_parameters  # noqa: E402
from src.sut import freshness  # noqa: E402
from src.sut.authz.jti_cache import Consumption, JtiCache  # noqa: E402

DELTA = frozen_parameters.delta_seconds()
# The mechanism namespace: `B3⁺`'s INV plane. Namespaces are separated so a
# DPoP `jti` and an INV `jti` cannot collide (ADR 0027).
TAG = "inv"


class TestTheCacheAndTheWindowAgreeAtEveryInstant:
    @pytest.mark.parametrize("elapsed", list(range(0, 62)))
    def test_a_still_fresh_proof_can_never_be_replayed(self, elapsed):
        """The invariant, stated once and checked at every second across the
        boundary: if the proof is still FRESH, the replay is a DUPLICATE."""
        issued = 1_800_000_000
        cache = JtiCache(ttl_seconds=DELTA)
        assert cache.consume(TAG, "jti-1", now=issued) is Consumption.ADMITTED

        now = issued + elapsed
        replayed = cache.consume(TAG, "jti-1", now=now)

        if freshness.is_fresh(now, issued):
            assert replayed is Consumption.DUPLICATE, (
                f"at t+{elapsed} the proof is still fresh but the cache released its jti: "
                "B3⁺ would admit the in-Δ replay that is its only reason to exist"
            )

    def test_the_boundary_second_itself(self):
        """`t + Δ` exactly -- where the closed window and a half-open TTL
        disagreed."""
        issued = 1_800_000_000
        now = issued + DELTA
        assert freshness.is_fresh(now, issued), "Δ is a CLOSED window (ADR 0027)"

        cache = JtiCache(ttl_seconds=DELTA)
        cache.consume(TAG, "jti-edge", now=issued)
        assert cache.consume(TAG, "jti-edge", now=now) is Consumption.DUPLICATE

    def test_past_the_window_the_entry_is_released(self):
        """The cache must not become unbounded: one second past Δ the proof is
        stale, the entry goes, and a fresh submission is admitted again."""
        issued = 1_800_000_000
        now = issued + DELTA + 1
        assert not freshness.is_fresh(now, issued)

        cache = JtiCache(ttl_seconds=DELTA)
        cache.consume(TAG, "jti-old", now=issued)
        assert cache.consume(TAG, "jti-old", now=now) is Consumption.ADMITTED
        assert len(cache) == 1, "the expired entry was replaced, not accumulated"

    def test_eviction_still_happens_so_the_cache_is_not_a_leak(self):
        cache = JtiCache(ttl_seconds=DELTA)
        for index in range(10):
            cache.consume(TAG, f"jti-{index}", now=1_800_000_000)
        assert len(cache) == 10

        cache.consume(TAG, "jti-later", now=1_800_000_000 + DELTA + 1)
        assert len(cache) == 1, "everything older than Δ was released"
