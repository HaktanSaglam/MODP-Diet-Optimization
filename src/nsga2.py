"""
nsga2.py  (OUR CODE -- graded)
==============================
NSGA-II (Deb et al., 2002), from scratch.

Mechanism: fast non-dominated sorting + crowding distance. Parents are chosen by
binary tournament on the crowded-comparison operator; offspring are produced with
the permutation operators (OX/PMX crossover + swap mutation per chromosome part);
the combined parent+offspring population is truncated front-by-front, using
crowding distance to trim the last front -- elitist (mu + lambda) survival.
"""
from __future__ import annotations

import random

from chromosome import random_chromosome
import operators
from moea_common import (
    Result, raw_min, make_individual,
    fast_non_dominated_sort, crowding_distance, crowded_better, nondominated,
)


def _make_offspring(problem, P, cfg, rng):
    Q = []
    while len(Q) < cfg.pop_size:
        p1 = operators.binary_tournament(P, crowded_better, rng)
        p2 = operators.binary_tournament(P, crowded_better, rng)
        c1, c2 = operators.crossover(p1.chromo, p2.chromo, cfg.pc, rng, cfg.crossover)
        operators.mutate(c1, rng)
        operators.mutate(c2, rng)
        Q.append(make_individual(problem, c1, cfg))
        if len(Q) < cfg.pop_size:
            Q.append(make_individual(problem, c2, cfg))
    return Q


def run(problem, cfg) -> Result:
    rng = random.Random(cfg.seed)
    P = [make_individual(problem, random_chromosome(problem, rng), cfg)
         for _ in range(cfg.pop_size)]
    fronts = fast_non_dominated_sort(P)
    for f in fronts:
        crowding_distance(f)

    history = []
    for _ in range(cfg.generations):
        Q = _make_offspring(problem, P, cfg, rng)
        R = P + Q
        fronts = fast_non_dominated_sort(R)
        newP = []
        for f in fronts:
            crowding_distance(f)
            if len(newP) + len(f) <= cfg.pop_size:
                newP.extend(f)
            else:
                f.sort(key=lambda ind: ind.crowding, reverse=True)
                newP.extend(f[:cfg.pop_size - len(newP)])
                break
        P = newP
        history.append([raw_min(ind) for ind in nondominated(P)])

    front = nondominated(P)
    return Result(algo="NSGA-II", problem=problem, cfg=cfg, pop=P, front=front,
                  history=history)
