"""Deriving randomness from the Seed (spec 9.3).

Every concern draws from its own stream, seeded from a hash of the Seed and a stable stream name, so supplying or
changing one thing never reshuffles another. Per-transaction streams carry the transaction number in their name
(`tx/3/amount`), so transaction 3 is the same whether the file holds 10 or 100 transactions.
"""

import hashlib
import random


def stream(seed: str, name: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}\x1f{name}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))  # noqa: S311 - seeded test data, not cryptography
