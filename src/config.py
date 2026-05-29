"""
config.py
=========
All tunable parameters in one place so every experiment is reproducible and
comparable. The handout fixes p_c = 0.9 and p_m = 1/n; lambda / alpha are tuned
experimentally and reported.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    pop_size: int = 100
    generations: int = 100
    pc: float = 0.9                 # crossover probability (handout)
    crossover: str = "ox"           # "ox" or "pmx"
    lam: float = 30.0               # penalty weight: handout starts at 1.0, tuned to 30
                                    # via a sweep (1->120) balancing feasibility vs front spread
    alpha: float = 1.0              # diversity penalty weight (Option B)
    use_diversity: bool = True
    seed: int = 0
    archive_size: int = 100         # SPEA2 archive size
