"""Helpers for censored potency measurements.

Both sources encode inexact measurements with a relation operator (Briefing §3.4):
ChEMBL keeps it in `standard_relation`; BindingDB embeds it in the value string
(e.g. ">10000"). A censored value is NOT the same as an exact potency, and these
rows must survive every extraction step, so parsing never coerces them to NaN.
"""
import re

import numpy as np
import pandas as pd

CENSORED_RELATIONS = {">", "<", ">=", "<="}

_VALUE_RE = re.compile(r"^\s*(>=|<=|>|<|~|=)?\s*([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*$")


def split_relation(raw: pd.Series) -> pd.DataFrame:
    """Split strings like '>10000', ' 0.24', '<=5' into (relation, value).

    Blank / missing -> (NaN, NaN). A bare number gets relation '='.
    Unparseable non-blank strings keep relation NaN and value NaN but are
    flagged in `unparsed` so they are counted rather than silently dropped.
    """
    s = raw.astype("string").str.strip()
    blank = s.isna() | (s == "")
    m = s.str.extract(_VALUE_RE)
    rel = m[0].where(~m[1].isna(), other=pd.NA)
    rel = rel.where(rel.notna() | m[1].isna(), "=")
    val = pd.to_numeric(m[1], errors="coerce")
    unparsed = ~blank & val.isna()
    return pd.DataFrame(
        {"relation": rel.astype("string"), "value": val.astype("float64"), "unparsed": unparsed},
        index=raw.index,
    )


def is_censored(relation: pd.Series) -> pd.Series:
    return relation.isin(CENSORED_RELATIONS).fillna(False).astype(bool)


def nm_to_p(value_nm: pd.Series) -> pd.Series:
    """-log10(molar) from nM. Only meaningful for exact ('=') values; callers must mask censored rows."""
    v = value_nm.where(value_nm > 0)
    return 9.0 - np.log10(v)
