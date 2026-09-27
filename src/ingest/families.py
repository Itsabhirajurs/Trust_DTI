"""Target-family assignment from ChEMBL's protein_classification hierarchy.

A protein component can be linked to several classification nodes. We walk each
node up to its level-1 (e.g. 'Enzyme', 'Membrane receptor') and level-2 (e.g.
'Kinase', 'Family A G protein-coupled receptor') ancestors. If a component's
nodes disagree at a level, it is labelled 'Multiple' at that level rather than
picking one arbitrarily; if it has no classification at all, 'Unclassified'.
"""
import pandas as pd

UNCLASSIFIED = "Unclassified"
MULTIPLE = "Multiple"


def ancestor_at_level(class_id: int, level: int, parent: dict, lvl: dict, name: dict):
    """Return the pref_name of the ancestor of `class_id` at `level` (or None if the node is shallower)."""
    node = class_id
    seen = set()
    while node is not None and node not in seen:
        seen.add(node)
        if lvl.get(node) == level:
            return name[node]
        node = parent.get(node)
    return None


def assign_families(component_class: pd.DataFrame, protein_classification: pd.DataFrame) -> pd.DataFrame:
    """component_class: [component_id, protein_class_id]; protein_classification:
    [protein_class_id, parent_id, pref_name, class_level].
    Returns one row per component_id with family_l1, family_l2, n_class_links."""
    pc = protein_classification
    parent = {int(k): (None if pd.isna(v) else int(v)) for k, v in zip(pc.protein_class_id, pc.parent_id)}
    lvl = {int(k): int(v) for k, v in zip(pc.protein_class_id, pc.class_level)}
    name = {int(k): v for k, v in zip(pc.protein_class_id, pc.pref_name)}

    rows = []
    for comp, grp in component_class.groupby("component_id"):
        ids = [int(x) for x in grp.protein_class_id]
        out = {"component_id": comp, "n_class_links": len(ids)}
        for level in (1, 2):
            vals = {ancestor_at_level(i, level, parent, lvl, name) for i in ids} - {None}
            out[f"family_l{level}"] = vals.pop() if len(vals) == 1 else (MULTIPLE if vals else None)
        rows.append(out)
    fam = pd.DataFrame(rows, columns=["component_id", "n_class_links", "family_l1", "family_l2"])
    fam["family_l1"] = fam["family_l1"].fillna(UNCLASSIFIED)
    # a component classified at L1 but with no L2 node gets its L1 name repeated, marked
    fam["family_l2"] = fam["family_l2"].fillna(fam["family_l1"].where(fam["family_l1"] == UNCLASSIFIED,
                                                                     fam["family_l1"] + " (no L2)"))
    return fam
