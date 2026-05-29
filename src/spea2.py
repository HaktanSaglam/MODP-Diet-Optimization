"""
spea2.py  (OUR CODE -- graded)
==============================
SPEA2 (Zitzler, Laumanns & Thiele, 2001), from scratch.

Mechanism:
  * Strength S(i)   = number of solutions i dominates.
  * Raw fitness R(i)= sum of strengths of i's dominators (0 => non-dominated).
  * Density  D(i)   = 1 / (sigma_i^k + 2), sigma_i^k = distance to the k-th
                      nearest neighbour in (normalised) objective space, k=floor(sqrt(N)).
  * Fitness  F(i)   = R(i) + D(i)  (lower is better; F<1 => non-dominated).
  * Environmental selection fills a fixed-size archive with all non-dominated
    individuals, then either fills with the best dominated ones or truncates the
    archive by repeatedly removing the individual closest to its neighbours.
  * Mating selection = binary tournament on F over the archive.

Distances are computed on objectives normalised to their union range, so no
single objective (e.g. time) dominates the density estimate.
"""
from __future__ import annotations

import math
import random

from chromosome import random_chromosome
import operators
from moea_common import Result, raw_min, make_individual, dominates, nondominated


def _normalised(union):
    """Return list of normalised fitness vectors aligned with `union`."""
    n_obj = len(union[0].fitness)
    mins = [min(ind.fitness[k] for ind in union) for k in range(n_obj)]
    maxs = [max(ind.fitness[k] for ind in union) for k in range(n_obj)]
    spans = [(maxs[k] - mins[k]) or 1.0 for k in range(n_obj)]
    return [[(ind.fitness[k] - mins[k]) / spans[k] for k in range(n_obj)] for ind in union]


def _assign_fitness(union):
    """Set strength / raw_fitness / density / spea_fitness on every individual."""
    N = len(union)
    # strength
    for p in union:
        p.strength = sum(1 for q in union if p is not q and dominates(p, q))
    # raw fitness = sum of dominators' strengths
    for p in union:
        p.raw_fitness = float(sum(q.strength for q in union if q is not p and dominates(q, p)))
    # density from k-th nearest neighbour in normalised objective space
    norm = _normalised(union)
    k = int(math.sqrt(N)) or 1
    for i, p in enumerate(union):
        dists = []
        vi = norm[i]
        for j in range(N):
            if i == j:
                continue
            vj = norm[j]
            dists.append(math.sqrt(sum((vi[t] - vj[t]) ** 2 for t in range(len(vi)))))
        dists.sort()
        sigma = dists[k] if k < len(dists) else (dists[-1] if dists else 0.0)
        p.density = 1.0 / (sigma + 2.0)
        p.spea_fitness = p.raw_fitness + p.density


def _truncate(archive, size):
    """Remove the most crowded individuals until len(archive)==size."""
    norm_index = {id(ind): v for ind, v in zip(archive, _normalised(archive))}

    def d(a, b):
        va, vb = norm_index[id(a)], norm_index[id(b)]
        return math.sqrt(sum((va[t] - vb[t]) ** 2 for t in range(len(va))))

    while len(archive) > size:
        # find individual with the smallest distance to its nearest neighbour
        best_idx = None
        best_key = None
        for i, a in enumerate(archive):
            ds = sorted(d(a, b) for j, b in enumerate(archive) if i != j)
            key = tuple(ds)  # lexicographic: nearest, then 2nd nearest, ...
            if best_key is None or key < best_key:
                best_key = key
                best_idx = i
        archive.pop(best_idx)
    return archive


def _environmental_selection(union, size):
    nd = [p for p in union if p.spea_fitness < 1.0]   # non-dominated
    if len(nd) == size:
        return nd
    if len(nd) < size:
        rest = sorted((p for p in union if p.spea_fitness >= 1.0),
                      key=lambda p: p.spea_fitness)
        return nd + rest[:size - len(nd)]
    return _truncate(list(nd), size)


def _spea_better(a, b):
    return a.spea_fitness < b.spea_fitness


def run(problem, cfg) -> Result:
    rng = random.Random(cfg.seed)
    P = [make_individual(problem, random_chromosome(problem, rng), cfg)
         for _ in range(cfg.pop_size)]
    archive = []
    history = []

    for gen in range(cfg.generations + 1):
        union = P + archive
        _assign_fitness(union)
        archive = _environmental_selection(union, cfg.archive_size)
        history.append([raw_min(ind) for ind in nondominated(archive)])
        if gen == cfg.generations:
            break
        # mating selection + variation
        Q = []
        while len(Q) < cfg.pop_size:
            p1 = operators.binary_tournament(archive, _spea_better, rng)
            p2 = operators.binary_tournament(archive, _spea_better, rng)
            c1, c2 = operators.crossover(p1.chromo, p2.chromo, cfg.pc, rng, cfg.crossover)
            operators.mutate(c1, rng)
            operators.mutate(c2, rng)
            Q.append(make_individual(problem, c1, cfg))
            if len(Q) < cfg.pop_size:
                Q.append(make_individual(problem, c2, cfg))
        P = Q

    front = nondominated(archive)
    return Result(algo="SPEA2", problem=problem, cfg=cfg, pop=archive, front=front,
                  history=history)
