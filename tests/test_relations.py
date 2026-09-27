import numpy as np
import pandas as pd

from src.ingest.relations import is_censored, nm_to_p, split_relation


def test_split_relation_keeps_censored_values():
    raw = pd.Series([">10000", " 0.24", "<=5", "", None, "abc", "1.5e3", "~30"])
    out = split_relation(raw)
    assert out["relation"].tolist()[:3] == [">", "=", "<="]
    assert out["value"].tolist()[:3] == [10000.0, 0.24, 5.0]
    # censored row survives with its numeric bound — never coerced to NaN
    assert not np.isnan(out.loc[0, "value"])
    # blanks are missing, not unparsed
    assert out["relation"].isna()[3] and out["relation"].isna()[4]
    assert not out["unparsed"][3] and not out["unparsed"][4]
    # junk is counted, not silently dropped
    assert out["unparsed"][5]
    assert out.loc[6, "value"] == 1500.0 and out.loc[6, "relation"] == "="
    assert out.loc[7, "relation"] == "~"


def test_is_censored():
    rel = pd.Series([">", "<", ">=", "<=", "=", "~", None], dtype="string")
    assert is_censored(rel).tolist() == [True, True, True, True, False, False, False]


def test_nm_to_p():
    p = nm_to_p(pd.Series([1.0, 1000.0, 0.0]))
    assert p[0] == 9.0 and p[1] == 6.0 and np.isnan(p[2])
