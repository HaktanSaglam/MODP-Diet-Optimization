"""
operators.py  (OUR CODE -- graded)
==================================
Genetic operators for the two-part permutation chromosome. Each operator is
applied INDEPENDENTLY to the breakfast part and the lunch+dinner part
(handout section 6):

    Crossover : OX (order crossover) or PMX, p_c = 0.9
    Mutation  : swap mutation within each part, p_m = 1/n  (n = part length)
    Selection : binary tournament
"""
from __future__ import annotations

import random

from chromosome import Chromosome


# --------------------------------------------------------------------------- #
# Permutation crossovers (operate on a single list)                           #
# --------------------------------------------------------------------------- #
def ox(p1: list, p2: list, rng: random.Random):
    """Order Crossover -> two children."""
    n = len(p1)
    if n < 2:
        return p1[:], p2[:]
    a, b = sorted(rng.sample(range(n), 2))

    def build(parent, donor):
        child = [None] * n
        child[a:b + 1] = parent[a:b + 1]
        seg = set(child[a:b + 1])
        fill = [x for x in donor if x not in seg]
        idx = 0
        for i in list(range(b + 1, n)) + list(range(0, a)):
            child[i] = fill[idx]
            idx += 1
        return child

    return build(p1, p2), build(p2, p1)


def pmx(p1: list, p2: list, rng: random.Random):
    """Partially Mapped Crossover -> two children."""
    n = len(p1)
    if n < 2:
        return p1[:], p2[:]
    a, b = sorted(rng.sample(range(n), 2))

    def build(parent, donor):
        child = [None] * n
        child[a:b + 1] = parent[a:b + 1]
        mapping = {parent[i]: donor[i] for i in range(a, b + 1)}
        seg = set(child[a:b + 1])
        for i in list(range(0, a)) + list(range(b + 1, n)):
            val = donor[i]
            while val in seg and val in mapping:
                val = mapping[val]
            # if still clashing (cycle), fall back to first unused donor value
            while val in seg:
                val = next(x for x in donor if x not in seg and x not in child)
            child[i] = val
            seg.add(val)
        return child

    return build(p1, p2), build(p2, p1)


_XOVERS = {"ox": ox, "pmx": pmx}


# --------------------------------------------------------------------------- #
# Chromosome-level crossover & mutation                                       #
# --------------------------------------------------------------------------- #
def crossover(c1: Chromosome, c2: Chromosome, pc: float, rng: random.Random,
              method: str = "ox"):
    """Crossover applied separately to each part with probability pc."""
    xf = _XOVERS[method]
    b1, b2 = (xf(c1.breakfast, c2.breakfast, rng)
              if rng.random() < pc else (c1.breakfast[:], c2.breakfast[:]))
    l1, l2 = (xf(c1.lunchdinner, c2.lunchdinner, rng)
              if rng.random() < pc else (c1.lunchdinner[:], c2.lunchdinner[:]))
    return Chromosome(b1, l1), Chromosome(b2, l2)


def _swap_mutate(perm: list, rng: random.Random):
    """Swap mutation with p_m = 1/n per gene."""
    n = len(perm)
    if n < 2:
        return
    pm = 1.0 / n
    for i in range(n):
        if rng.random() < pm:
            j = rng.randrange(n)
            perm[i], perm[j] = perm[j], perm[i]


def mutate(chromo: Chromosome, rng: random.Random) -> Chromosome:
    """Swap mutation applied independently to each part (in place, returns it)."""
    _swap_mutate(chromo.breakfast, rng)
    _swap_mutate(chromo.lunchdinner, rng)
    return chromo


# --------------------------------------------------------------------------- #
# Selection                                                                   #
# --------------------------------------------------------------------------- #
def binary_tournament(pop: list, better, rng: random.Random):
    """Pick 2 at random, return the one `better(a, b)` prefers (True if a wins)."""
    a, b = rng.choice(pop), rng.choice(pop)
    return a if better(a, b) else b
