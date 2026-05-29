"""
data_model.py
=============
Builds a per-user problem instance from the database. Everything is queried
live from the DB (via db.py); only *modelling decisions* (which nutrient ids are
the 5 constraints, which food groups count as breakfast) live here as documented
constants -- those are choices, not hardcoded data values.

Key modelling decisions (documented in CLAUDE.md):
  * 5 nutritional constraints -> nutrient ids {Energy 5, Protein 15,
    Carbohydrate 8, Fiber 4, Sodium 17}.
  * food_nutrients.quantity is the amount PER PORTION -> summed directly
    (verified empirically; multiplying by portion gives absurd values).
  * DRI bounds are looked up by (nutrient, user.age in [low_age,up_age],
    user.gender) -- the table is per age+gender, not per user. Gender is matched
    case-insensitively ('Female' vs 'female').
  * Breakfast pool vs lunch+dinner pool is decided by foodGroupId
    (BREAKFAST_GROUPS below). The handout's 94/311 split is illustrative.
  * Vegetarian user (id 2): foods with no/NULL preference in user_foods are not
    part of that user's candidate set.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import db

# 5 nutritional constraints (handout C1..C5) -> nutrients.id
NUTRIENT_IDS = [5, 15, 8, 4, 17]
NUTRIENT_LABELS = {5: "Energy", 15: "Protein", 8: "Carbohydrate", 4: "Fiber", 17: "Sodium"}
NUTRIENT_UNITS = {5: "kcal", 15: "g", 8: "g", 4: "g", 17: "mg"}

# Breakfast-eligible food groups (Turkish breakfast: dairy, jams, honey, olives,
# bakery, cereals, beverages, fruit). The rest are the lunch+dinner pool.
BREAKFAST_GROUPS = {1, 4, 5, 7, 8, 11, 12, 13, 14, 20, 26, 27}

# Decode tolerances (handout section 3).
EPS_RUL = 1.15          # allow 15% over the upper bound
EPS_RLL = 0.90          # allow 10% under the lower bound
BREAKFAST_FRACTION = 0.35  # breakfast targets 35% of daily DRI


@dataclass
class Food:
    id: int
    name: str
    group_id: int
    cost: float
    preference: float
    time: float                    # preparingTime + cookingTime
    co2: float
    portion: int
    nutrients: dict = field(default_factory=dict)  # nutrientId -> per-portion amount

    def nutrient(self, nid: int) -> float:
        return self.nutrients.get(nid, 0.0)


@dataclass
class Problem:
    user_id: int
    user_name: str
    age: int
    gender: str
    vegetarian: bool
    foods: dict                    # id -> Food (this user's candidate set)
    breakfast_ids: list            # candidate ids in the breakfast pool
    lunchdinner_ids: list          # candidate ids in the lunch+dinner pool
    dri: dict                      # nutrientId -> (RLL, RUL)

    # --- nutrient / objective helpers -------------------------------------
    def nutrient_totals(self, food_ids) -> dict:
        totals = {nid: 0.0 for nid in NUTRIENT_IDS}
        for fid in food_ids:
            f = self.foods[fid]
            for nid in NUTRIENT_IDS:
                totals[nid] += f.nutrient(nid)
        return totals

    def distinct_groups(self, food_ids) -> int:
        return len({self.foods[fid].group_id for fid in food_ids})


def _lookup_dri(age: int, gender: str) -> dict:
    """Return {nutrientId: (RLL, RUL)} for the user's age+gender."""
    g = (gender or "").strip().lower()
    out = {}
    for nid in NUTRIENT_IDS:
        rows = db.query(
            "SELECT RLL, RUL, gender, low_age, up_age FROM dri "
            "WHERE nutrient_id=? AND low_age<=? AND up_age>=?",
            (nid, age, age),
        )
        match = None
        for r in rows:
            if (r["gender"] or "").strip().lower() == g:
                match = r
                break
        if match is None and rows:           # fall back to any age-matching row
            match = rows[0]
        if match is None:
            raise ValueError("No DRI row for nutrient %d age %d gender %s" % (nid, age, gender))
        out[nid] = (float(match["RLL"]), float(match["RUL"]))
    return out


def build_problem(user_id: int) -> Problem:
    u = db.query("SELECT id, name, age, gender FROM user WHERE id=?", (user_id,))
    if not u:
        raise ValueError("User %d not found" % user_id)
    u = u[0]

    dri = _lookup_dri(int(u["age"]), u["gender"])

    # Per-user preferences (handout: use user_foods, not foods.preference).
    # A preference of -1 is a sentinel meaning "this user does not eat this food"
    # (vegetarian user 2 excludes meat/chicken/fish this way). NULL is the same.
    pref_rows = db.query(
        "SELECT foodId, preference FROM user_foods WHERE userId=?", (user_id,)
    )
    pref = {
        r["foodId"]: r["preference"]
        for r in pref_rows
        if r["preference"] is not None and r["preference"] >= 0
    }

    # All candidate foods + objective values.
    food_rows = db.query(
        "SELECT id, name, foodGroupId, cost, preparingTime, cookingTime, co2, portion FROM foods"
    )

    # Nutrient matrix (only our 5 nutrients).
    nut_rows = db.query(
        "SELECT foodId, nutrientId, quantity FROM food_nutrients WHERE nutrientId IN (%s)"
        % ",".join(str(n) for n in NUTRIENT_IDS)
    )
    nut_by_food = {}
    for r in nut_rows:
        nut_by_food.setdefault(r["foodId"], {})[r["nutrientId"]] = float(r["quantity"] or 0.0)

    foods = {}
    for r in food_rows:
        fid = r["id"]
        if fid not in pref:        # vegetarian filter: no preference -> not a candidate
            continue
        foods[fid] = Food(
            id=fid,
            name=r["name"],
            group_id=int(r["foodGroupId"]),
            cost=float(r["cost"] or 0.0),
            preference=float(pref[fid]),
            time=float(r["preparingTime"] or 0.0) + float(r["cookingTime"] or 0.0),
            co2=float(r["co2"] or 0.0),
            portion=int(r["portion"] or 0),
            nutrients=nut_by_food.get(fid, {}),
        )

    breakfast_ids = [fid for fid, f in foods.items() if f.group_id in BREAKFAST_GROUPS]
    lunchdinner_ids = [fid for fid, f in foods.items() if f.group_id not in BREAKFAST_GROUPS]

    total_candidates = len(foods)
    vegetarian = total_candidates < 405  # user 2 loses ~98 meat foods

    return Problem(
        user_id=user_id,
        user_name="%s" % u["name"],
        age=int(u["age"]),
        gender=u["gender"],
        vegetarian=vegetarian,
        foods=foods,
        breakfast_ids=breakfast_ids,
        lunchdinner_ids=lunchdinner_ids,
        dri=dri,
    )


if __name__ == "__main__":
    for uid in (1, 2):
        p = build_problem(uid)
        print("=== User %d (%s, %d %s) vegetarian=%s ===" % (
            uid, p.user_name, p.age, p.gender, p.vegetarian))
        print("  candidate foods: %d  (breakfast %d / lunch+dinner %d)" % (
            len(p.foods), len(p.breakfast_ids), len(p.lunchdinner_ids)))
        print("  DRI bounds:")
        for nid in NUTRIENT_IDS:
            rll, rul = p.dri[nid]
            print("    %-13s [%g, %g] %s" % (
                NUTRIENT_LABELS[nid], rll, rul, NUTRIENT_UNITS[nid]))
