"""
chromosome.py  (OUR CODE -- graded)
===================================
Chromosome representation (handout section 3).

A candidate solution is a permutation of all of the user's candidate food IDs,
split into two INDEPENDENT parts:

    [  breakfast-pool permutation  |  lunch+dinner-pool permutation  ]

The two parts are shuffled and operated on independently -- crossover and
mutation are applied to each part separately (see operators.py). The chromosome
is NOT the menu; it is decoded greedily into the actual selected foods
(see decode.py).
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Chromosome:
    breakfast: list      # permutation of problem.breakfast_ids
    lunchdinner: list    # permutation of problem.lunchdinner_ids

    def copy(self) -> "Chromosome":
        return Chromosome(list(self.breakfast), list(self.lunchdinner))


def random_chromosome(problem, rng: random.Random | None = None) -> Chromosome:
    """Random permutation of each pool independently (handout: initialization)."""
    rng = rng or random
    b = list(problem.breakfast_ids)
    l = list(problem.lunchdinner_ids)
    rng.shuffle(b)
    rng.shuffle(l)
    return Chromosome(b, l)
