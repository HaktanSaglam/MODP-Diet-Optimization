# CLAUDE.md — Multi-Objective Diet Optimization Problem (MODP)

> **Living document.** Update this file after every prompt as decisions are made and tasks
> are completed. The "Progress Log" at the bottom is the running history.
> Course: BLM20364E / BLM22332E — Heuristic Optimization Algorithms · Term Project (30% of grade).

---

## 1. What the project is

Recommend a **daily menu** (breakfast + lunch&dinner) for a specific user, picked from a database
of **405 prepared foods**. Modelled as a **Multi-Objective Multidimensional Knapsack Problem
(MOMKP)** and solved with **Evolutionary Multi-Objective Algorithms (MOEAs)**.

- **Group project** (max 5 students), ~7 weeks.
- **Deliverables:** Report (PDF, max 15 pages) + Source code (ZIP, runnable, with README) +
  Results (CSV/JSON Pareto fronts).
- **Hard rule (repeated twice in the handout, in red):** the **chromosome representation,
  decoding, and penalty function MUST be our own code**, even if we use a MOEA library.
  Be ready to explain every line.

### Objectives — choose exactly 3
| f | Objective | Direction | Status |
|---|-----------|-----------|--------|
| f1 | User preference | **MAX** | **Mandatory** |
| f2 | Cost (`cost`) | MIN | pick 2 of 3 |
| f3 | Prep time (`preparingTime + cookingTime`) | MIN | pick 2 of 3 |
| f4 | CO₂ footprint (`co2`) | MIN | pick 2 of 3 |

**Decision:** Use **f1 (preference, MAX), f2 (cost, MIN), f3 (prep+cook time, MIN)**.
(Rationale documented in §5; revisit if we prefer CO₂ over time.)

### Mathematical model
```
max f1 = Σ xᵢ·preferenceᵢ          (mandatory)
min f2 = Σ xᵢ·costᵢ                 (chosen)
min f3 = Σ xᵢ·(prepTime+cookTime)ᵢ  (chosen)
s.t.   RLLⱼ ≤ Σ xᵢ·nutrient(j,i) ≤ RULⱼ   for j = 1..5
       xᵢ ∈ {0,1},  n = 405 foods
```

### The 5 nutritional constraints → verified nutrient IDs
| # | Nutrient | Unit | `nutrients.id` |
|---|----------|------|----------------|
| C1 | Energy | kcal | **5** |
| C2 | Protein | g | **15** |
| C3 | Carbohydrate (by difference) | g | **8** |
| C4 | Fiber (total dietary) | g | **4** |
| C5 | Sodium (Na) | mg | **17** |

---

## 2. Verified database facts (from `diet.sql`)

Source dump: phpMyAdmin / MariaDB 10.4, database name **`diet`**, charset utf8mb4.
**Do NOT hardcode any values — everything is queried from the DB.** Facts below are for
*understanding only*, not for embedding as constants.

### Tables we actually use
| Table | Key columns | Purpose |
|-------|-------------|---------|
| `foods` | id, name, foodGroupId, portion, cost, preference, preference2, preparingTime, cookingTime, co2 | The 405 candidate foods + objective values |
| `user_foods` | userId, foodId, preference | **Per-user preference (use this, NOT foods.preference)** |
| `food_nutrients` | foodId, nutrientId, quantity | Nutrient content per food |
| `nutrients` | id, name, nGroupId, unitId | Nutrient names/units |
| `dri` | nutrient_id, low_age, up_age, gender, RLL, RUL | Daily intake bounds **by age+gender** |
| `food_group` | id, name | Food groups (for diversity) |
| `user` | id, age, gender, … | User demographics → maps to DRI rows |

(Other tables — `menus`, `chosen_menu`, `ingredients`, `food_ingredients`, `food_sim`,
`nutrient_group`, `units` — are not needed for the core task.)

### Verified counts & values
- **`foods` has exactly 405 rows** → this is `n=405`. (Ignore the `caseStudy` column for
  selection; all 405 rows are the candidate set.)
- **`food_group` has 29 groups (id 0–28)**, *not* 18 as the handout text says — see Discrepancies.
- **`food_nutrients` covers all 405 foods for each of our 5 nutrients** (405 rows each). Good.
- **Both target users are 25-year-old Female** → identical DRI bounds:

  | Nutrient | RLL | RUL |
  |----------|-----|-----|
  | Energy (5) | 2000 | 2400 |
  | Protein (15) | 40 | 100 |
  | Carbohydrate (8) | 170 | 300 |
  | Fiber (4) | 20 | 9999 (effectively no upper cap) |
  | Sodium (17) | 1500 | 2300 |

### The two users (run algorithms separately for each)
- **User 1 = `user.id = 1`** — *Isla Morris*, 25 F. **Non-vegetarian.** Has preference values
  for all **405** foods in `user_foods`.
- **User 2 = `user.id = 2`** — *Zoely Butler*, 25 F. **Vegetarian.** Has preference values for
  only **~307** foods; the remaining ~98 meat/chicken/fish foods have **NULL preference** in
  `user_foods` → these are excluded from User 2's candidate set (or preference treated as
  unavailable). This is how the vegetarian distinction is encoded — confirmed empirically.

---

## 3. Chromosome representation, decoding, penalty (OUR CODE — most important)

### Representation
A candidate = a **permutation of all 405 food IDs split into two independent parts**:
```
[ breakfast-pool permutation | lunch+dinner-pool permutation ]
```
The two parts are shuffled and operated on **independently** (crossover + mutation per part).

- **RESOLVED — breakfast vs lunch+dinner split:** classified by `foodGroupId`.
  `BREAKFAST_GROUPS = {1,4,5,7,8,11,12,13,14,20,26,27}` (dairy, jams, honey, pancakes,
  seed/bean/olive, bakery, sweet marmelades, beverages, cereals, fruits, beverages-2, bakery-2).
  Resulting counts — **User 1: 91 breakfast / 314 lunch+dinner**; **User 2: 86 / 221**.
  (Handout's 94/311 is illustrative; our split is reproducible from the DB.)

### Decoding (genotype → phenotype) — greedy, left-to-right
- **Breakfast part** (Energy + Protein only, target 35% of daily DRI):
  iterate breakfast genes L→R, tentatively add each food; **skip** if it would exceed `ε·RUL`
  for Energy or Protein; **stop** once `ε·RLL` for both Energy and Protein is met.
- **Lunch+dinner part** (all 5 nutrients, totals carried over from breakfast):
  same greedy procedure, checking all 5 DRI bounds at each step.
- **ε tolerance (soft, keeps feasible space non-empty):**
  - effective RUL = `RUL × 1.15` (allow 15% over)
  - effective RLL = `RLL × 0.90` (allow 10% under)
  - breakfast split: `RLL_b = RLL × 0.35`, `RUL_b = RUL × 0.35`

### Penalty function (added to fitness)
```
for each nutrient j=1..5 with menu total vⱼ:
  viol_low_j  = max(0, RLLⱼ − vⱼ) / (RULⱼ − RLLⱼ)
  viol_high_j = max(0, vⱼ − RULⱼ) / (RULⱼ − RLLⱼ)
R = 0.7·Σ viol_low_j + 0.3·Σ viol_high_j      # under-nutrition penalized harder
penalized_fitness = objective_value − λ·R       # λ = penalty weight, tune; start λ = 1.0
```

---

## 4. Diversity (required)
A valid menu must span different food groups. Implement **at least one** of:
- **A — extra objective:** f_diversity = distinct foodGroupId count (→ 4-objective). 
- **B — penalty term:** `R_total = R + α·(1 / distinct_group_count)`. 
- **C — hard constraint:** distinct foodGroupId ≥ 4 enforced during decode (simplest).

**Plan:** Option **B (penalty term)** as primary — it toggles on/off cleanly for the required
"with vs without diversity" experiment. Target **4–6 distinct food groups** per menu.

---

## 5. Algorithms (implement & compare ≥ 2)
**Decision:** Implement **NSGA-II** and **SPEA2** **from scratch** (full control + required
explainability; library MOEAs make the custom permutation/decode awkward).
- NSGA-II: non-dominated sorting + crowding distance.
- SPEA2: strength fitness + k-NN density + archive truncation.

### Operators (applied independently to each chromosome part)
| Operator | Detail |
|----------|--------|
| Initialization | Random permutation per part |
| Crossover | **OX or PMX**, per part, `p_c = 0.9` |
| Mutation | Swap mutation within each part, `p_m = 1/n` (n = part length) |
| Selection | Binary tournament |

---

## 6. Experiments, outputs & evaluation
**Required experiments:** (1) User 1 vs User 2 Pareto fronts; (2) ≥2 algorithms, same params;
(3) diversity on vs off.

**Required visualizations:** Pareto front scatter (per algorithm + overlay); convergence curve
(hypervolume vs generation); sample menu table (≥3 Pareto solutions: foods, nutrient totals vs
DRI bounds, objective values).

**Hypervolume:** true front unknown → use **hypervolume with a fixed reference point** =
for each objective, worst value observed across all runs **+ 10% margin**; same reference for all
algorithms; report the values used.

**Grading (100 pts):** DB integration & data loading 10 · Chromosome rep & decode 20 ·
Algorithms (min 2) 30 · Constraint & penalty 15 · Diversity 10 · Experiments & visualizations 15.

---

## 7. Tech stack & repo layout (IMPLEMENTED for data layer)
- **Language:** Python 3.14 in a project **venv** (`./venv`). Deps: numpy, matplotlib, pymysql.
- **DB access (`src/db.py`):** default backend is **SQLite** (`diet.sqlite`, auto-built from
  `diet.sql` by `src/load_sqlite.py` on first use) — zero install, fully runnable. Optional
  **MySQL** backend via env `MODP_DB=mysql` + `MODP_MYSQL_*` for graders who load `diet` into
  MySQL. Same standard SQL on both; nothing hardcoded — all queried.
- **Plotting:** matplotlib. **Numerics:** numpy.
- **Run data layer:** `./venv/bin/python src/load_sqlite.py` then `src/data_model.py`.

```
Heu Proje/
  CLAUDE.md  diet.sql  "Term Project Handout - MODP.pdf"
  src/
    db.py          # connection + queries, zero hardcoded values
    data_model.py  # build food/nutrient/dri/preference objects for a user
    chromosome.py  # two-part permutation rep + init
    decode.py      # greedy genotype→phenotype
    objectives.py  # f1..f3 evaluation
    penalty.py     # DRI penalty R
    diversity.py   # diversity penalty / metric
    operators.py   # OX/PMX, swap mutation, binary tournament
    nsga2.py  spea2.py  hypervolume.py
    experiments.py # runs experiments 1–3 for user 1 & 2
    viz.py         # plots
  results/         # CSV/JSON Pareto fronts + figures
  report/          # report PDF + sources
  README.md
```

---

## 8. Discrepancies between handout and actual DB (be ready to explain in report)
1. **DRI is per age+gender, not per user.** Handout's dataset table says `dri(userId, nutrientId,
   RLL, RUL)`, but the real table is `dri(nutrient_id, low_age, up_age, gender, RLL, RUL)`.
   → Map each user via `user.age` + `user.gender` to the matching DRI rows.
   **Gender case mismatch:** `user` has `Male/Female/child`, `dri` has `male/female/child` →
   compare case-insensitively.
2. **Food groups: 29 (id 0–28), not 18.** Use the real count for diversity.
3. **"Two users provided":** the `user` table actually has 125 users; the two *target* users for
   this project are `id=1` (non-veg) and `id=2` (veg), identified by their `user_foods` coverage.
4. **Vegetarian encoding** = NULL preference rows in `user_foods` for User 2 (no explicit flag).

## 9. Resolved questions / still open
- **RESOLVED — `food_nutrients.quantity` is PER PORTION** (used directly, NOT ×portion).
  Verified: AKDENİZ SALATASI (193 g) → 312 kcal / 5.2 g protein; ANKARA TAVA (215 g) → 991 kcal /
  56.7 g protein. Multiplying by portion gives absurd 60 000 kcal.
- **RESOLVED — vegetarian encoding = `user_foods.preference = -1`** (sentinel "does not eat").
  User 2 has 98 such foods (49 Meat dishes + 32 Chicken/Turkey + 1 Fish + scattered) → excluded
  from the candidate set. User 1 has none. (NULL preference is treated the same way.)
- **RESOLVED — preference scale 0–10** (max observed 10; -1 is the exclusion sentinel).
- Still open: final OX vs PMX choice; final λ and α values (tune experimentally, report them);
  whether to also produce CO₂ (f4) results for comparison.

---

## 10. Roadmap (phased)
> Nothing is implemented yet. Code only starts when the user says **"yap"** (go).

- **Phase 0 — Understanding & docs** ✅ *(done)*: read handout + DB, write this file.
- **Phase 1 — Data layer** ✅ *(done)*: `load_sqlite.py` (diet.sql→SQLite), `db.py`, `data_model.py`.
  405 foods loaded, per-user candidate sets (U1 405, U2 307), DRI bounds, nutrient matrix, groups.
  Nutrient units verified (per-portion). Vegetarian filter (pref=-1) working.
- **Phase 2 — Core (our code):** chromosome rep + init, greedy decode, objectives, penalty,
  diversity. Unit-test the decode on a few menus vs DRI bounds.
- **Phase 3 — Algorithms:** NSGA-II, then SPEA2, with shared operators (OX/PMX, swap, tournament).
- **Phase 4 — Experiments:** run for User 1 & User 2; hypervolume + reference point; the 3
  required experiments. Export Pareto fronts to CSV/JSON.
- **Phase 5 — Visualization:** Pareto scatter + overlay, convergence curves, sample menu tables.
- **Phase 6 — Report & packaging:** 15-page report, README, ZIP.

---

## 11. Progress Log
- **2026-05-26 (Phase 0):** Read full handout (8 pp) + `diet.sql`. Mapped 5 nutrient IDs,
  identified target users 1 (non-veg) & 2 (veg), verified DRI bounds for 25 F, confirmed
  405 foods & full nutrient coverage, recorded handout↔DB discrepancies. Created CLAUDE.md.
  Objectives chosen: f1+f2+f3. Algorithms chosen: NSGA-II + SPEA2 from scratch.
- **2026-05-26 (Phase 1 ✅):** Created venv (numpy 2.4.6, matplotlib 3.10.9). Wrote
  `src/load_sqlite.py` (robust MySQL-dump→SQLite tokenizer; verified row counts: foods 405,
  food_nutrients 12555, user_foods 43729, dri 402). Wrote `src/db.py` (SQLite default + optional
  MySQL). Wrote `src/data_model.py` (per-user `Problem`: DRI by age+gender, per-user prefs,
  nutrient matrix, breakfast/lunch pools). Resolved all 3 open data questions (units per-portion;
  veg = pref −1; scale 0–10). U1: 405 foods (91/314). U2: 307 foods (86/221).
- **2026-05-26 (Phase 2 ✅):** Wrote core (our code): `chromosome.py` (two-part permutation +
  random init), `decode.py` (greedy L→R, breakfast Energy+Protein@35%, lunch+dinner all-5,
  ε tolerances), `penalty.py` (DRI violation R, 0.7 low / 0.3 high), `diversity.py` (Option B
  penalty term α/groups), `objectives.py` (f1 pref MAX / f2 cost / f3 time MIN → min-vector with
  penalty folded in). Smoke test (500 random decodes): U1 avg 9.6 foods, 2.81/5 compliance,
  10% fully-feasible, 7.7 groups; U2 10.4 foods, 3.08/5, 13% feasible, 8.1 groups. Behaviour
  matches handout (soft-feasible decode + penalty drives MOEA toward feasibility).
- **2026-05-26 (Phase 3 ✅):** Wrote `operators.py` (OX + PMX per-part crossover pc=0.9, swap
  mutation pm=1/n, binary tournament), `moea_common.py` (Individual, Pareto dominance, fast
  non-dominated sort, crowding distance, Result, raw_min), `config.py`, `hypervolume.py` (HSO,
  exact, sanity-checked), `nsga2.py` (elitist μ+λ, crowded tournament), `spea2.py` (strength +
  k-NN density on normalised objectives + archive truncation). Both run in <0.5 s at pop40/gen20
  and produce Pareto fronts with fully-feasible (5/5) menus. **λ tuned: sweep 1→120 showed
  feasible-count rises (9→23) as front-spread shrinks; chose λ=30** (good balance). Diversity
  note: decoded menus already span 8–12 groups (>> 4–6 target) so Option-B diversity is rarely
  binding — expect small with/without difference (a legitimate finding to report).
- **2026-05-26 (Phase 4 ✅):** Wrote `experiments.py`. Run matrix = {user 1,2} × {NSGA-II, SPEA2}
  × {diversity on/off} = 8 runs, pop=100 gen=100 seed=42 (~22 s total). Shared HV reference
  (min-form) = (16.17, 67.67, 934.5) = worst-across-all + 10% range. Fronts deduped by objective
  vector. Each run → `results/pareto_<label>.csv` + `.json` (objectives, 5 nutrient totals vs DRI,
  menus, feasibility, groups). Plus `convergence.csv` (HV/gen), `hypervolume.csv` (final metrics),
  `reference_point.json`. Findings: U2 HV > U1 (higher prefs); diversity ON raises avg distinct
  groups (e.g. SPEA2 U1 8.7 vs 7.2) at a small HV cost; 26–41 fully-feasible (5/5) menus per front.
  Example U1 feasible menu: pref 90, all 5 nutrients in DRI.
- **2026-05-26 (Phase 5 ✅):** Wrote `viz.py` (headless matplotlib). Generated 12 artefacts into
  `results/figures/`: per-user Pareto pairwise scatter (pref-cost/pref-time/cost-time, NSGA-II vs
  SPEA2, feasible highlighted), 3D Pareto scatter, convergence curves (HV/gen, div vs nodiv),
  user-comparison (Exp 1), diversity-impact bars (Exp 3), and sample-menu tables + markdown
  (`sample_menus_user{1,2}.md`). Convergence is monotone & plateaus < gen 100; sample menus all
  5/5 feasible; U2 menus confirmed meat-free.
- **2026-05-26 (Phase 6 ✅):** Wrote `README.md` (runnable instructions, backend options,
  structure, decisions), installed reportlab, wrote `report_gen.py` → `report/MODP_Report.pdf`
  (6 pp, full report: formulation, DB, chromosome/decode, penalty, diversity, algorithms,
  setup, 3 experiments, sample menus, discussion; DejaVuSans for Turkish). Built
  `MODP_submission.zip` (1.9 MB, src+results+report+README+requirements+CLAUDE+diet.sql, no venv).
  Verified zero-setup: deleting diet.sqlite → db.py auto-rebuilds it. **PROJECT COMPLETE** — all
  6 phases done; pipeline reproducible: load_sqlite → experiments → viz → report_gen.
