"""
report_gen.py
=============
Generates the term-project report (PDF, <= 15 pages) from the result artefacts.
Uses reportlab + matplotlib's bundled DejaVuSans (full Unicode -> Turkish food
names render correctly). Text is written here; tables/figures are pulled from
results/.

Run AFTER experiments.py and viz.py.
"""
from __future__ import annotations

import csv
import os

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
FIGS = os.path.join(RESULTS, "figures")
OUT = os.path.join(ROOT, "report", "MODP_Report.pdf")

_TTF = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(_TTF, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(_TTF, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Italic", os.path.join(_TTF, "DejaVuSans-Oblique.ttf")))

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontName="DejaVu", fontSize=9.5,
                      leading=13, alignment=TA_JUSTIFY, spaceAfter=6)
H1 = ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=14, leading=17, spaceBefore=10,
                    spaceAfter=6, textColor=colors.HexColor("#1F3864"))
H2 = ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=11, leading=14, spaceBefore=8,
                    spaceAfter=4, textColor=colors.HexColor("#2E4D7B"))
TITLE = ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=20, leading=24,
                       alignment=TA_CENTER, spaceAfter=6)
SUB = ParagraphStyle("sub", fontName="DejaVu", fontSize=12, leading=15, alignment=TA_CENTER,
                     textColor=colors.HexColor("#444444"))
MONO = ParagraphStyle("mono", parent=BODY, fontName="DejaVu", fontSize=8.5, leading=11,
                      backColor=colors.HexColor("#F2F2F2"), alignment=TA_JUSTIFY,
                      leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=4)
CAP = ParagraphStyle("cap", parent=BODY, fontSize=8.5, alignment=TA_CENTER,
                     textColor=colors.HexColor("#555555"), spaceBefore=2, spaceAfter=10)


def P(t, s=BODY):
    return Paragraph(t, s)


def fig(name, width=16 * cm, caption=None):
    path = os.path.join(FIGS, name)
    img = Image(path)
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = width
    img.drawHeight = width * ratio
    out = [img]
    if caption:
        out.append(P(caption, CAP))
    return out


def hv_table():
    with open(os.path.join(RESULTS, "hypervolume.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    head = ["Run", "User", "Algo", "Div", "Hypervolume", "Front", "Feasible", "AvgGroups", "s"]
    data = [head]
    for r in rows:
        data.append([
            r["label"], r["user"], r["algo"], "on" if r["diversity"] == "1" else "off",
            "%.3e" % float(r["final_hypervolume"]), r["front_size"], r["feasible"],
            r["avg_distinct_groups"], r["seconds"],
        ])
    t = Table(data, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF2F8")]),
        ("ALIGN", (4, 1), (-1, -1), "CENTER"),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(OUT, pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            title="Multi-Objective Diet Optimization Problem")
    e = []

    # --- Title ---
    e += [Spacer(1, 2.5 * cm),
          P("Multi-Objective Diet Optimization Problem (MODP)", TITLE),
          P("Evolutionary Multi-Objective Optimization for Daily Menu Recommendation", SUB),
          Spacer(1, 0.6 * cm),
          P("BLM20364E / BLM22332E — Heuristic Optimization Algorithms · Term Project", SUB),
          Spacer(1, 1.2 * cm)]
    intro = ("This report presents a complete solution to the Multi-Objective Diet Optimization "
             "Problem, modelled as a Multi-Objective Multidimensional Knapsack Problem (MOMKP). "
             "A daily menu (breakfast + lunch&dinner) is recommended for two users from a "
             "database of 405 prepared foods, optimising user preference, cost and preparation "
             "time simultaneously under five nutritional constraints. Two multi-objective "
             "evolutionary algorithms — NSGA-II and SPEA2 — are implemented from scratch, "
             "together with a custom two-part permutation chromosome, a greedy decoder and a "
             "DRI-violation penalty function.")
    e += [P(intro), PageBreak()]

    # --- 1. Problem formulation ---
    e += [P("1. Problem Formulation", H1)]
    e += [P("The goal is to select a subset of foods x ∈ {0,1}<super>405</super> forming a daily "
            "menu that simultaneously optimises three objectives while keeping five aggregate "
            "nutrient totals inside per-user Daily Reference Intake (DRI) bounds. Following the "
            "handout we choose exactly three objectives (the user-preference objective is "
            "mandatory):")]
    e += [P("f1(x) = Σ x<sub>i</sub>·preference<sub>i</sub>  → MAXIMISE  (mandatory)<br/>"
            "f2(x) = Σ x<sub>i</sub>·cost<sub>i</sub>  → MINIMISE<br/>"
            "f3(x) = Σ x<sub>i</sub>·(preparingTime+cookingTime)<sub>i</sub>  → MINIMISE", MONO)]
    e += [P("subject to, for each of the j = 1..5 nutrients: "
            "RLL<sub>j</sub> ≤ Σ x<sub>i</sub>·nutrient(j,i) ≤ RUL<sub>j</sub>.", BODY)]
    e += [P("The five nutritional constraints (and their database nutrient ids) are Energy "
            "(5, kcal), Protein (15, g), Carbohydrate by difference (8, g), Fiber total dietary "
            "(4, g) and Sodium (17, mg). The problem is multidimensional (five simultaneous "
            "capacity-style constraints) and multi-objective, hence a MOMKP.")]

    # --- 2. Dataset & DB integration ---
    e += [P("2. Dataset & Database Integration", H1)]
    e += [P("All data is queried live from the provided database; nothing is hardcoded. The "
            "MySQL dump <font face='DejaVu-Italic'>diet.sql</font> is imported into a local "
            "SQLite database by a custom tokenizer (<font face='DejaVu-Italic'>load_sqlite.py</font>) "
            "that correctly handles Turkish strings containing commas, apostrophes and backslash "
            "escapes. The same standard SQL also runs against a real MySQL server "
            "(<font face='DejaVu-Italic'>db.py</font> exposes both backends). Seven tables are "
            "used: foods (405 rows), user_foods (per-user preferences), food_nutrients, "
            "nutrients, dri, food_group and user.")]
    e += [P("Two users are studied separately: <b>User 1</b> (Isla, 25 F, non-vegetarian, 405 "
            "candidate foods) and <b>User 2</b> (Zoely, 25 F, vegetarian, 307 candidate foods). "
            "The vegetarian distinction is encoded in the data as a preference value of −1 in "
            "user_foods (a sentinel meaning “does not eat”); User 2 has 98 such foods — 49 meat "
            "dishes, 32 chicken/turkey, 1 fish and a few mixed items — which are removed from "
            "that user’s candidate set.")]
    e += [P("Three handout↔database discrepancies were found and handled: (i) the dri table is "
            "keyed by nutrient + age-range + gender, not by user, so each user is mapped via age "
            "and (case-insensitive) gender to the matching bounds; (ii) the database actually "
            "contains 29 food groups (ids 0–28), not 18; (iii) food_nutrients.quantity is the "
            "amount per food portion and is summed directly (verified empirically — multiplying "
            "by portion gives absurd values such as 60 000 kcal). For both 25-year-old female "
            "users the DRI bounds are Energy [2000, 2400], Protein [40, 100], Carbohydrate "
            "[170, 300], Fiber [20, ∞) and Sodium [1500, 2300].")]

    # --- 3. Chromosome & decoding ---
    e += [P("3. Chromosome Representation & Decoding", H1)]
    e += [P("Representation. A candidate solution is a permutation of all of the user’s candidate "
            "food ids, split into two independent parts — a breakfast pool and a lunch+dinner "
            "pool. Foods are assigned to the breakfast pool by food group (dairy, jams, honey, "
            "pancakes, olives/seeds, bakery, marmalades, beverages, cereals, fruit); the rest "
            "form the lunch+dinner pool. This yields 91 / 314 foods for User 1 and 86 / 221 for "
            "User 2. Crossover and mutation operate on each part independently.")]
    e += [P("Decoding (genotype → phenotype). The chromosome is not the menu; it is decoded "
            "greedily left-to-right. The breakfast part considers only Energy and Protein at 35% "
            "of the daily DRI: each food is tentatively added and skipped if it would exceed "
            "ε·RUL<sub>b</sub>; the part stops once ε·RLL<sub>b</sub> is met for both. The "
            "lunch+dinner part carries over the breakfast totals and applies the same procedure "
            "to all five nutrients against the full daily bounds. Soft tolerances keep the "
            "feasible space non-empty: effective RUL = RUL×1.15, effective RLL = RLL×0.90, "
            "breakfast split = 35% of the daily bound.")]

    # --- 4. Penalty ---
    e += [P("4. Constraints & Penalty Function", H1)]
    e += [P("Residual violations of the hard DRI bounds are penalised proportionally, with "
            "under-nutrition weighted more heavily (0.7) than over-nutrition (0.3):")]
    e += [P("viol_low<sub>j</sub> = max(0, RLL<sub>j</sub>−v<sub>j</sub>) / (RUL<sub>j</sub>−RLL<sub>j</sub>)<br/>"
            "viol_high<sub>j</sub> = max(0, v<sub>j</sub>−RUL<sub>j</sub>) / (RUL<sub>j</sub>−RLL<sub>j</sub>)<br/>"
            "R = 0.7·Σ viol_low<sub>j</sub> + 0.3·Σ viol_high<sub>j</sub><br/>"
            "penalised objective = objective ∓ λ·R<sub>total</sub>", MONO)]
    e += [P("The penalty worsens every objective (it is subtracted from the maximised preference "
            "and added to the minimised cost and time), pushing infeasible menus off the Pareto "
            "front. The handout suggests λ = 1 as a starting point; a sweep over λ ∈ {1..120} "
            "showed the number of fully-feasible menus rising (≈9 → ≈23) as the front spread "
            "shrinks, so <b>λ = 30</b> was chosen as a balance and is reported here.")]

    # --- 5. Diversity ---
    e += [P("5. Diversity Mechanism", H1)]
    e += [P("A valid daily menu should span several food groups. We implement Option B — a "
            "penalty term R_total = R + α·(1 / distinct_group_count) with α = 1 — because it "
            "toggles cleanly on and off for the diversity experiment. The target is 4–6 distinct "
            "food groups per menu; in practice the greedy decode already produces 8–12 groups, so "
            "the term is rarely binding (analysed in Experiment 3).")]

    # --- 6. Algorithms ---
    e += [P("6. Algorithms & Operators", H1)]
    e += [P("Two MOEAs are implemented from scratch. <b>NSGA-II</b> uses fast non-dominated "
            "sorting and crowding distance with elitist (μ+λ) survival and binary-tournament "
            "selection on the crowded-comparison operator. <b>SPEA2</b> uses strength-based raw "
            "fitness plus a k-th nearest-neighbour density estimate (computed on range-normalised "
            "objectives so no single objective dominates the distance), an external archive and "
            "archive truncation. Shared permutation operators, applied independently to each "
            "chromosome part, are: Order Crossover (OX, default) or PMX with p<sub>c</sub> = 0.9; "
            "swap mutation with p<sub>m</sub> = 1/n; and binary tournament selection.")]

    # --- 7. Experimental setup ---
    e += [P("7. Experimental Setup", H1)]
    e += [P("Each configuration uses population 100, 100 generations and seed 42 for "
            "reproducibility. The run matrix is {User 1, User 2} × {NSGA-II, SPEA2} × "
            "{diversity on, off} = 8 runs. Since the true Pareto front is unknown, performance is "
            "measured by hypervolume with a single fixed reference point shared by all runs: for "
            "each objective the worst value observed across all runs and all generations, extended "
            "by 10% of the observed range. In minimisation form the reference point is "
            "(−preference, cost, time) = (16.17, 67.67, 934.50). Final-front results:")]
    e += [Spacer(1, 0.2 * cm), hv_table(), Spacer(1, 0.3 * cm)]

    # --- 8. Experiment 1 ---
    e += [P("8. Experiment 1 — User Comparison", H1)]
    e += [P("The two users yield clearly different Pareto fronts. User 2 (vegetarian) attains a "
            "higher hypervolume and higher preference totals, because the recorded preference "
            "ratings for User 2 are on average higher and the candidate set, while smaller, is "
            "well-liked. User 1’s front spreads over a wider cost range. The fronts confirm the "
            "expected preference↔cost and preference↔time trade-offs.")]
    e += fig("user_comparison.png", caption="Figure 1. Experiment 1 — User 1 vs User 2 fronts "
             "(NSGA-II, diversity ON): preference–cost (left) and preference–time (right).")

    # --- 9. Experiment 2 ---
    e += [P("9. Experiment 2 — Algorithm Comparison", H1)]
    e += [P("With identical parameters NSGA-II and SPEA2 produce comparable fronts and very "
            "similar hypervolume; SPEA2’s archive tends to keep a slightly larger and more evenly "
            "spread front, while NSGA-II is roughly twice as fast. The convergence curves show "
            "monotonically increasing hypervolume that plateaus well before generation 100, "
            "indicating both algorithms have converged.")]
    e += fig("pareto_pairwise_user1.png", caption="Figure 2. User 1 Pareto front, NSGA-II vs "
             "SPEA2 (diversity ON). Solid markers are fully-feasible (5/5 nutrients in DRI); "
             "faint × markers are soft-feasible menus.")
    e += fig("convergence_user1.png", width=13 * cm,
             caption="Figure 3. User 1 convergence — hypervolume vs generation. Diversity-OFF "
             "(dashed) reaches higher hypervolume than diversity-ON (solid), the cost of the "
             "diversity penalty.")
    e += fig("convergence_user2.png", width=13 * cm,
             caption="Figure 4. User 2 convergence — hypervolume vs generation.")

    # --- 10. Experiment 3 ---
    e += [P("10. Experiment 3 — Diversity Impact", H1)]
    e += [P("Enabling the diversity penalty consistently increases (or maintains) the average "
            "number of distinct food groups in the front, at a small hypervolume cost. Because "
            "the greedy decode already produces highly diverse menus (8–12 groups, far above the "
            "4–6 target), the effect is modest — a legitimate finding: for this dataset and "
            "decoder, diversity is largely emergent and the explicit mechanism mainly guards the "
            "few low-diversity menus.")]
    e += fig("diversity_impact.png", width=14 * cm, caption="Figure 5. Experiment 3 — average "
             "distinct food groups per front, diversity ON vs OFF. Shaded band = 4–6 target.")

    # --- 11. Sample menus ---
    e += [P("11. Sample Menus", H1)]
    e += [P("The tables below show three feasible Pareto menus per user, spanning the preference "
            "range. Every nutrient total lies inside the user’s DRI bounds, and User 2’s menus "
            "contain no meat, poultry or fish — confirming both the constraint handling and the "
            "vegetarian filtering.")]
    e += fig("sample_menus_user1.png", width=16 * cm,
             caption="Figure 6. User 1 (non-vegetarian) — three feasible Pareto menus.")
    e += fig("sample_menus_user2.png", width=16 * cm,
             caption="Figure 7. User 2 (vegetarian) — three feasible Pareto menus.")

    # --- 12. Discussion ---
    e += [P("12. Discussion & Conclusion", H1)]
    e += [P("The MOMKP formulation, the custom two-part permutation chromosome with greedy "
            "decoding, and the DRI penalty together produce realistic, nutritionally-valid daily "
            "menus tailored to each user. Both NSGA-II and SPEA2 converge to comparable, "
            "well-spread Pareto fronts containing 26–41 fully-feasible menus, and the framework "
            "cleanly separates the parts the handout requires to be our own code (representation, "
            "decoding, penalty) from the algorithmic search. Key engineering choices — per-portion "
            "nutrient summation, age/gender DRI mapping, the −1 vegetarian sentinel, λ = 30, and a "
            "shared hypervolume reference point — were all driven by direct inspection of the "
            "data and small calibration experiments. Future work could add the CO₂ objective as a "
            "fourth dimension, average results over multiple seeds, and explore an adaptive "
            "penalty weight.")]
    e += [P("Reproducibility. The entire pipeline is reproducible: "
            "<font face='DejaVu-Italic'>python src/load_sqlite.py</font> → "
            "<font face='DejaVu-Italic'>python src/experiments.py</font> → "
            "<font face='DejaVu-Italic'>python src/viz.py</font> → "
            "<font face='DejaVu-Italic'>python src/report_gen.py</font>. See README for details.")]

    doc.build(e)
    print("Report written to %s" % OUT)


if __name__ == "__main__":
    build()
