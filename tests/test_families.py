import pandas as pd

from src.ingest.families import MULTIPLE, UNCLASSIFIED, assign_families

PC = pd.DataFrame({
    "protein_class_id": [0, 1, 2, 3, 4, 5, 6],
    "parent_id":        [None, 0, 1, 2, 0, 4, 0],
    "pref_name":  ["Protein class", "Enzyme", "Kinase", "Protein kinase", "Membrane receptor", "Family A GPCR", "Other"],
    "class_level":      [0, 1, 2, 3, 1, 2, 1],
})


def test_walks_to_l1_and_l2():
    cc = pd.DataFrame({"component_id": [10], "protein_class_id": [3]})
    f = assign_families(cc, PC).set_index("component_id")
    assert f.loc[10, "family_l1"] == "Enzyme"
    assert f.loc[10, "family_l2"] == "Kinase"


def test_conflicting_links_become_multiple():
    cc = pd.DataFrame({"component_id": [11, 11], "protein_class_id": [3, 5]})
    f = assign_families(cc, PC).set_index("component_id")
    assert f.loc[11, "family_l1"] == MULTIPLE
    assert f.loc[11, "n_class_links"] == 2


def test_agreeing_links_stay_single():
    cc = pd.DataFrame({"component_id": [12, 12], "protein_class_id": [2, 3]})
    f = assign_families(cc, PC).set_index("component_id")
    assert f.loc[12, "family_l1"] == "Enzyme" and f.loc[12, "family_l2"] == "Kinase"


def test_l1_only_node_is_marked():
    cc = pd.DataFrame({"component_id": [13], "protein_class_id": [6]})
    f = assign_families(cc, PC).set_index("component_id")
    assert f.loc[13, "family_l1"] == "Other"
    assert f.loc[13, "family_l2"] == "Other (no L2)"
    assert UNCLASSIFIED not in f["family_l1"].tolist()
