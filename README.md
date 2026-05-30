# Multi-Objective Diet Optimization Problem (MODP)

Term project for **BLM20364E / BLM22332E — Heuristic Optimization Algorithms**.

## Project Members

| # | Name |
|---|------|
| 1 | Haktan Sağlam |
| 2 | Ömer Faruk Kocabaş |
| 3 | Abdullah Beşir Arat |
| 4 | Muhammet Gelgör |
| 5 | Mustafa Aydın |

Recommend a daily menu (breakfast + lunch&dinner) for a user from a database of
**405 prepared foods**, modelled as a **Multi-Objective Multidimensional Knapsack
Problem (MOMKP)** and solved with two multi-objective evolutionary algorithms,
**NSGA-II** and **SPEA2**, implemented from scratch.

Objectives (3, the first is mandatory): **maximise user preference**, **minimise
cost**, **minimise prep+cook time** — subject to 5 nutritional constraints
(Energy, Protein, Carbohydrate, Fiber, Sodium) staying inside per-user DRI bounds.

---

## 1. Requirements & setup

Python 3.10+ (developed on 3.14). All dependencies install into a local venv:

```bash
cd "Heu Proje"
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```

Dependencies: `numpy`, `matplotlib`, `reportlab` (PDF report), `pymysql` (only if
you use the optional MySQL backend).

---

## 2. How to run (full pipeline)

```bash
./venv/bin/python src/load_sqlite.py     # 1. build diet.sqlite from diet.sql
./venv/bin/python src/experiments.py     # 2. run 8 experiments -> results/*.csv,*.json
./venv/bin/python src/viz.py             # 3. figures -> results/figures/*.png
./venv/bin/python src/report_gen.py      # 4. report -> report/MODP_Report.pdf
```

Step 1 is optional — `db.py` auto-builds `diet.sqlite` on first use. Quick checks:

```bash
./venv/bin/python src/data_model.py      # print per-user problem (candidates, DRI)
./venv/bin/python src/hypervolume.py     # hypervolume sanity checks
```

### Database backend

By default the project uses **SQLite** (`diet.sqlite`, auto-built from `diet.sql`)
so it runs with zero external services. To query a real **MySQL** server instead
(after importing `diet.sql` into a `diet` database), set environment variables:

```bash
export MODP_DB=mysql
export MODP_MYSQL_HOST=127.0.0.1 MODP_MYSQL_USER=root MODP_MYSQL_PASSWORD=... MODP_MYSQL_DB=diet
```

The same standard SQL runs against both backends. **Nothing is hardcoded — all
data is queried from the database.**

---

## 3. Project structure

```
Heu Proje/
  diet.sql                 provided MySQL dump (input)
  CLAUDE.md                living design/decision log
  requirements.txt
  src/
    load_sqlite.py         MySQL-dump -> SQLite importer (robust tokenizer)
    db.py                  DB access (SQLite default / MySQL optional)
    data_model.py          per-user Problem: foods, prefs, DRI, nutrient matrix, pools
    chromosome.py          two-part permutation representation + init   (our code)
    decode.py              greedy genotype -> menu decoding             (our code)
    objectives.py          f1/f2/f3 evaluation + penalty folding        (our code)
    penalty.py             DRI violation penalty R                      (our code)
    diversity.py           Option-B diversity penalty term              (our code)
    operators.py           OX/PMX crossover, swap mutation, tournament  (our code)
    moea_common.py         Individual, dominance, non-dom sort, crowding
    nsga2.py  spea2.py     the two MOEAs (from scratch)
    hypervolume.py         exact hypervolume (HSO)
    config.py              all tunable parameters
    experiments.py         run matrix + CSV/JSON export
    viz.py                 plots + sample-menu tables
    report_gen.py          PDF report
  results/                 Pareto fronts (CSV/JSON), metrics, figures/
  report/                  MODP_Report.pdf
```

---

## 4. Outputs

- `results/pareto_<run>.csv` / `.json` — every Pareto solution: objectives, the 5
  nutrient totals vs DRI bounds, feasibility, distinct groups, and the menu
  (food ids + names). `<run>` = `u{1,2}_{nsgaii,spea2}_{div,nodiv}`.
- `results/hypervolume.csv` — final hypervolume + front size + feasible count per run.
- `results/convergence.csv` — hypervolume per generation per run.
- `results/reference_point.json` — shared HV reference point + parameters.
- `results/sample_menus_user{1,2}.md` — readable sample menus.
- `results/figures/*.png` — Pareto scatter (2D pairwise + 3D), convergence curves,
  diversity-impact bars, sample-menu tables.
- `report/MODP_Report.pdf` — the full report.

---

## 5. Key design decisions

- **5 constraints → nutrient ids** Energy 5, Protein 15, Carbohydrate 8, Fiber 4, Sodium 17.
- **`food_nutrients.quantity` is per portion** — summed directly (verified empirically).
- **DRI is by age+gender** (not per user); each user maps via age + case-insensitive gender.
- **Vegetarian (User 2)** = `user_foods.preference = -1` sentinel → those foods excluded.
- **Breakfast/lunch split** by food group (handout's 94/311 is illustrative).
- **Penalty λ = 30** (handout starts at 1; tuned by sweep). **Diversity** = Option B, α = 1.
- **Hypervolume reference** = worst-across-all-runs + 10% of range (shared by all runs).

The chromosome representation, decoding and penalty function are entirely our own
code, as required by the handout.
