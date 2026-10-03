"""Stage 2 groundwork probe (2026-10-03): which real-data problems must Network 1 construction solve?

Read-only. Measures repeated measurements per pair, disagreement between repeats, compounds that
share an InChIKey connectivity block (stereo/isotope variants), and salt/scaffold statistics on a
FIXED random sample of 40,000 compounds (seed 0). Sample-based numbers (salts, scaffolds) are
estimates, not full-universe counts. Output is saved to reports/stage0/stage2_probe_output.txt.

Run: python -m src.ingest.probe_stage2_issues > reports/stage0/stage2_probe_output.txt
"""
import sqlite3, numpy as np, pandas as pd
from src import config
a = pd.read_parquet(config.INTERIM/"chembl37_human_sp_activities.parquet",
    columns=["molregno","inchikey","tid","standard_type","standard_relation","standard_value","standard_units","pchembl_value","potential_duplicate"])
t = pd.read_parquet(config.INTERIM/"chembl37_human_sp_targets.parquet").sort_values(["tid","component_id"]).drop_duplicates("tid")[["tid","accession"]]
a = a.merge(t,on="tid")
# 1. rows per pair
g = a.groupby(["molregno","accession"]).size()
print("pairs:",len(g)," rows/pair mean %.2f median %d max %d  share>1 row: %.1f%%"%(g.mean(),g.median(),g.max(),(g>1).mean()*100))
# 2. disagreement among repeated exact potencies
e = a[(a.standard_relation=="=")&(a.standard_units=="nM")&(a.standard_type.isin(["IC50","Ki","Kd","EC50"]))&(a.standard_value>0)].copy()
e["p"]=9-np.log10(e.standard_value)
s = e.groupby(["molregno","accession"]).p.agg(["count","min","max"])
m = s[s["count"]>1]; spread = m["max"]-m["min"]
print("exact-potency pairs:",len(s)," with >1 measurement:",len(m),"(%.1f%%)"%(len(m)/len(s)*100))
print("  of those, spread >=1 log: %.1f%%  >=2 log: %.1f%%  median spread %.2f"%((spread>=1).mean()*100,(spread>=2).mean()*100,spread.median()))
# 3. same molecule, several IDs: salts/stereo -> InChIKey first block
k = a[["molregno","inchikey"]].drop_duplicates().dropna()
k["block1"]=k.inchikey.str[:14]
print("molregno:",k.molregno.nunique()," distinct full InChIKey:",k.inchikey.nunique()," distinct connectivity block:",k.block1.nunique())
multi = k.groupby("block1").molregno.nunique(); print("  connectivity blocks shared by >1 ChEMBL compound IDs:",(multi>1).sum())
# 4. example: imatinib and its salt/related records
con = sqlite3.connect(f"file:{config.CHEMBL_DB}?mode=ro",uri=True)
ik = con.execute("select cs.standard_inchi_key from compound_structures cs join molecule_dictionary m on m.molregno=cs.molregno where m.chembl_id='CHEMBL941'").fetchone()[0]
rows = con.execute("select m.chembl_id, m.pref_name, cs.canonical_smiles from compound_structures cs join molecule_dictionary m on m.molregno=cs.molregno where cs.standard_inchi_key like ?",(ik[:14]+"%",)).fetchall()
print("records sharing imatinib connectivity block:"); [print("  ",r[0],r[1],(r[2] or "")[:70]) for r in rows]
# 5. scaffolds on a 40k sample
from rdkit import Chem, RDLogger; RDLogger.DisableLog("rdApp.*")
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.Chem.SaltRemover import SaltRemover
ids = k.molregno.drop_duplicates().sample(40000,random_state=0).tolist()
q = "select molregno, canonical_smiles from compound_structures where molregno in (%s)"%",".join(map(str,ids))
df = pd.read_sql_query(q,con)
sc=[];salts=0;bad=0
for smi in df.canonical_smiles:
    mol = Chem.MolFromSmiles(smi) if smi else None
    if mol is None: bad+=1; continue
    if "." in smi: salts+=1
    sc.append(MurckoScaffold.MurckoScaffoldSmiles(mol=mol))
sc = pd.Series(sc); vc = sc.value_counts()
print("sample 40k: unparseable",bad," multi-component (salt/mixture) SMILES: %.1f%%"%(salts/len(df)*100))
print("  distinct scaffolds:",sc.nunique()," empty scaffold (acyclic): %.1f%%"%((sc=='').mean()*100)," scaffolds with 1 compound: %.1f%%"%((vc==1).sum()/len(vc)*100)," top scaffold share: %.1f%%"%(vc.iloc[0]/len(sc)*100))
print("  top-5 scaffold sizes:",vc.head(5).tolist())
