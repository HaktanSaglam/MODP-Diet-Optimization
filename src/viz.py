"""
viz.py
======
Reads the artefacts in results/ and produces the required visualisations into
results/figures/:

  * Pareto front scatter -- pairwise 2D projections (pref-cost, pref-time,
    cost-time) per user, overlaying NSGA-II vs SPEA2; feasible menus highlighted.
  * Pareto front 3D scatter per user.
  * Convergence curve -- hypervolume vs generation, per algorithm, per user.
  * Diversity impact -- avg distinct food groups, diversity ON vs OFF.
  * Sample menu table -- 3 Pareto solutions (foods, nutrient totals vs DRI,
    objectives) rendered as a figure and written as Markdown.

All plots are generated headless (Agg backend) so this runs without a display.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "results")
FIGS = os.path.join(RESULTS, "figures")
NUTRIENTS = ["energy", "protein", "carbohydrate", "fiber", "sodium"]


def load_pareto(label):
    with open(os.path.join(RESULTS, "pareto_%s.json" % label), encoding="utf-8") as f:
        return json.load(f)


def load_convergence():
    conv = defaultdict(list)
    with open(os.path.join(RESULTS, "convergence.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            conv[r["label"]].append((int(r["generation"]), float(r["hypervolume"])))
    for k in conv:
        conv[k].sort()
    return conv


def load_hv_rows():
    with open(os.path.join(RESULTS, "hypervolume.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- #
def _xy(data, kx, ky):
    return [s[kx] for s in data["solutions"]], [s[ky] for s in data["solutions"]]


def _feas_mask(data):
    return [s["feasible"] == 1 for s in data["solutions"]]


def plot_pareto_pairwise(user):
    nsga = load_pareto("u%d_nsgaii_div" % user)
    spea = load_pareto("u%d_spea2_div" % user)
    pairs = [("preference", "cost"), ("preference", "time"), ("cost", "time")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, (kx, ky) in zip(axes, pairs):
        for data, color, name in ((nsga, "tab:blue", "NSGA-II"), (spea, "tab:orange", "SPEA2")):
            xs, ys = _xy(data, kx, ky)
            mask = _feas_mask(data)
            xf = [x for x, m in zip(xs, mask) if m]
            yf = [y for y, m in zip(ys, mask) if m]
            xi = [x for x, m in zip(xs, mask) if not m]
            yi = [y for y, m in zip(ys, mask) if not m]
            ax.scatter(xi, yi, s=18, c=color, alpha=0.25, marker="x",
                       label="%s (soft)" % name)
            ax.scatter(xf, yf, s=30, c=color, alpha=0.9, edgecolors="k", linewidths=0.4,
                       label="%s (feasible)" % name)
        ax.set_xlabel(kx)
        ax.set_ylabel(ky)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8, loc="best")
    fig.suptitle("User %d -- Pareto front (NSGA-II vs SPEA2, diversity ON)" % user)
    fig.tight_layout()
    p = os.path.join(FIGS, "pareto_pairwise_user%d.png" % user)
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def plot_pareto_3d(user):
    nsga = load_pareto("u%d_nsgaii_div" % user)
    spea = load_pareto("u%d_spea2_div" % user)
    fig = plt.figure(figsize=(7.5, 6))
    ax = fig.add_subplot(111, projection="3d")
    for data, color, name in ((nsga, "tab:blue", "NSGA-II"), (spea, "tab:orange", "SPEA2")):
        xs = [s["preference"] for s in data["solutions"]]
        ys = [s["cost"] for s in data["solutions"]]
        zs = [s["time"] for s in data["solutions"]]
        ax.scatter(xs, ys, zs, s=22, c=color, alpha=0.7, label=name)
    ax.set_xlabel("preference (max)")
    ax.set_ylabel("cost (min)")
    ax.set_zlabel("time (min)")
    ax.set_title("User %d -- Pareto front in 3 objectives" % user)
    ax.legend()
    fig.tight_layout()
    p = os.path.join(FIGS, "pareto_3d_user%d.png" % user)
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def plot_user_comparison():
    """Experiment 1: User 1 vs User 2 fronts (pref vs cost)."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, (kx, ky) in zip(axes, [("preference", "cost"), ("preference", "time")]):
        for user, color in ((1, "tab:green"), (2, "tab:purple")):
            data = load_pareto("u%d_nsgaii_div" % user)
            xs, ys = _xy(data, kx, ky)
            ax.scatter(xs, ys, s=24, c=color, alpha=0.7,
                       label="User %d (%s)" % (user, "non-veg" if user == 1 else "veg"))
        ax.set_xlabel(kx)
        ax.set_ylabel(ky)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9)
    fig.suptitle("Experiment 1 -- User comparison (NSGA-II, diversity ON)")
    fig.tight_layout()
    p = os.path.join(FIGS, "user_comparison.png")
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def plot_convergence(user):
    conv = load_convergence()
    fig, ax = plt.subplots(figsize=(8, 5))
    styles = {
        "u%d_nsgaii_div" % user: ("NSGA-II (div)", "tab:blue", "-"),
        "u%d_spea2_div" % user: ("SPEA2 (div)", "tab:orange", "-"),
        "u%d_nsgaii_nodiv" % user: ("NSGA-II (no div)", "tab:blue", "--"),
        "u%d_spea2_nodiv" % user: ("SPEA2 (no div)", "tab:orange", "--"),
    }
    for label, (name, color, ls) in styles.items():
        if label not in conv:
            continue
        gens = [g for g, _ in conv[label]]
        hvs = [h for _, h in conv[label]]
        ax.plot(gens, hvs, color=color, linestyle=ls, label=name, linewidth=1.8)
    ax.set_xlabel("generation")
    ax.set_ylabel("hypervolume")
    ax.set_title("User %d -- convergence (hypervolume vs generation)" % user)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    p = os.path.join(FIGS, "convergence_user%d.png" % user)
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def plot_diversity_impact():
    """Experiment 3: avg distinct food groups, diversity ON vs OFF."""
    rows = load_hv_rows()
    labels, on_vals, off_vals = [], [], []
    for user in (1, 2):
        for algo in ("nsgaii", "spea2"):
            on = next(r for r in rows if r["label"] == "u%d_%s_div" % (user, algo))
            off = next(r for r in rows if r["label"] == "u%d_%s_nodiv" % (user, algo))
            labels.append("U%d %s" % (user, "NSGA-II" if algo == "nsgaii" else "SPEA2"))
            on_vals.append(float(on["avg_distinct_groups"]))
            off_vals.append(float(off["avg_distinct_groups"]))
    x = range(len(labels))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([i - w / 2 for i in x], on_vals, w, label="diversity ON", color="teal")
    ax.bar([i + w / 2 for i in x], off_vals, w, label="diversity OFF", color="tab:gray")
    ax.axhspan(4, 6, color="green", alpha=0.08, label="target 4-6 groups")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("avg distinct food groups in front")
    ax.set_title("Experiment 3 -- Diversity impact on menu variety")
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=9)
    fig.tight_layout()
    p = os.path.join(FIGS, "diversity_impact.png")
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def sample_menu_table(user, n=3):
    """Pick n feasible Pareto solutions and render a menu table (figure + markdown)."""
    data = load_pareto("u%d_nsgaii_div" % user)
    feas = [s for s in data["solutions"] if s["feasible"] == 1]
    pool = feas if len(feas) >= n else data["solutions"]
    # spread across the preference range
    pool = sorted(pool, key=lambda s: s["preference"], reverse=True)
    idxs = [0, len(pool) // 2, len(pool) - 1][:n] if len(pool) >= n else range(len(pool))
    picks = [pool[i] for i in idxs]
    dri = data["dri_bounds"]

    # --- Markdown ---
    lines = ["# Sample menus -- User %d (%s)\n" % (
        user, "non-vegetarian" if user == 1 else "vegetarian")]
    for k, s in enumerate(picks, 1):
        lines.append("## Menu %d\n" % k)
        lines.append("- **Objectives:** preference = %.1f (max), cost = %.2f, time = %.0f min"
                     % (s["preference"], s["cost"], s["time"]))
        lines.append("- **Foods (%d, %d groups):** %s" % (
            s["n_foods"], s["distinct_groups"], s["food_names"]))
        lines.append("- **Nutrient totals vs DRI:**")
        lines.append("")
        lines.append("| Nutrient | Total | DRI range | OK |")
        lines.append("|---|---|---|---|")
        for n_name in NUTRIENTS:
            key = {"energy": "Energy", "protein": "Protein", "carbohydrate": "Carbohydrate",
                   "fiber": "Fiber", "sodium": "Sodium"}[n_name]
            lo, hi = dri[key]
            v = s[n_name]
            ok = "OK" if lo <= v <= hi else "X"
            lines.append("| %s | %.1f | [%g, %g] | %s |" % (key, v, lo, hi, ok))
        lines.append("")
    md_path = os.path.join(RESULTS, "sample_menus_user%d.md" % user)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # --- Figure (compact nutrient table) ---
    fig, ax = plt.subplots(figsize=(9, 0.5 + 0.5 * (len(picks) + 1)))
    ax.axis("off")
    col_labels = ["Menu", "pref", "cost", "time", "foods", "groups"] + \
                 [n.capitalize()[:4] for n in NUTRIENTS]
    table_rows = []
    for k, s in enumerate(picks, 1):
        table_rows.append([
            "M%d" % k, "%.1f" % s["preference"], "%.1f" % s["cost"], "%.0f" % s["time"],
            str(s["n_foods"]), str(s["distinct_groups"]),
        ] + ["%.0f" % s[n] for n in NUTRIENTS])
    tbl = ax.table(cellText=table_rows, colLabels=col_labels, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.5)
    ax.set_title("User %d -- sample feasible Pareto menus (objectives + nutrient totals)" % user,
                 fontsize=10)
    fig.tight_layout()
    p = os.path.join(FIGS, "sample_menus_user%d.png" % user)
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return md_path, p


def main():
    os.makedirs(FIGS, exist_ok=True)
    made = []
    for user in (1, 2):
        made.append(plot_pareto_pairwise(user))
        made.append(plot_pareto_3d(user))
        made.append(plot_convergence(user))
        made.extend(sample_menu_table(user))
    made.append(plot_user_comparison())
    made.append(plot_diversity_impact())
    print("Generated %d artefacts:" % len(made))
    for m in made:
        print("  ", os.path.relpath(m, os.path.dirname(HERE)))


if __name__ == "__main__":
    main()
