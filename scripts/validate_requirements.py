#!/usr/bin/env python3
"""要件整合ゲート（fail-close）。

docs/requirements/ の MD と JSON 正本の整合を検証する。1 件でも FAIL があれば exit 1。
ゲート一覧は docs/governance/requirements-gates.md を正本とする。
"""

import glob
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = ROOT / "docs/requirements/json"
MD = ROOT / "docs/requirements"

failures: list[str] = []


def gate(gate_id: str, cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"{status} [{gate_id}] {msg}")
    if not cond:
        failures.append(f"{gate_id}: {msg}")


def load(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def md_count(path: Path, pattern: str) -> int:
    text = path.read_text(encoding="utf-8")
    return len(set(re.findall(pattern, text)))


# G-JSON: 全 JSON が構文的に妥当
bad = []
for f in glob.glob(str(J / "**/*.json"), recursive=True):
    try:
        load(Path(f))
    except Exception as e:  # noqa: BLE001
        bad.append(f"{f}: {e}")
gate("G-JSON", not bad, f"全 JSON 構文妥当 {bad or ''}")

# G-CNT: JSON 件数 = MD 分母
br = load(J / "br.json")["items"]
gate("G-CNT-BR", len(br) == 31 == md_count(MD / "br-backbone_v0.1.md", r"\*\*(BR-[A-H]\d)\*\*"), "BR=31 (MD/JSON)")

req = load(J / "req.json")["items"]
gate("G-CNT-REQ", len(req) == 45 == md_count(MD / "requirement-list_v0.1.md", r"(REQ-\d{3})"), "REQ=45 (MD/JSON)")

r = load(J / "requirements.json")["items"]
fr = [i for i in r if i["kind"] == "FR"]
nfr = [i for i in r if i["kind"] == "NFR"]
md_fr = md_count(MD / "requirements_v0.1.md", r"\*\*(FR-\d+)\*\*")
md_nfr = md_count(MD / "requirements_v0.1.md", r"\*\*(NFR-\d+)")
gate("G-CNT-FR", len(fr) == 36 == md_fr, f"FR=36 (MD={md_fr}/JSON={len(fr)})")
gate("G-CNT-NFR", len(nfr) == 10 == md_nfr, f"NFR=10 (MD={md_nfr}/JSON={len(nfr)})")

ac = load(J / "ac.json")
md_ac = md_count(MD / "requirements_v0.1.md", r"\| (AC-\d+) \|")
gate("G-CNT-AC", len(ac["items"]) == 19 == md_ac, f"AC=19 (MD={md_ac}/JSON={len(ac['items'])})")
gate("G-CNT-ACDEF", len(ac.get("deferred", [])) == 17, "AC deferred=17")

fn = load(J / "fn.json")["items"]
md_fn = md_count(MD / "function-list_v0.1.md", r"\| (FN-\d{3}) \|")
gate("G-CNT-FN", len(fn) == 61 == md_fn, f"FN=61 (MD={md_fn}/JSON={len(fn)})")

bm = sum(len(load(Path(f))["items"]) for f in glob.glob(str(J / "br-media/*.json")) if "index" not in f)
md_bm = md_count(MD / "br-media_v0.1.md", r"\*\*(BR-M-[A-Z]+-\d+)\*\*")
gate("G-CNT-BRM", bm == 70 == md_bm, f"BR-M=70 (MD={md_bm}/JSON={bm})")

mr = sum(len(load(Path(f))["items"]) for f in glob.glob(str(J / "mr/*.json")) if "index" not in f)
gate("G-CNT-MR", mr == 54, f"MR=54 (JSON={mr})")

wf = load(J / "ltw/workflows.json")["items"]
gate("G-CNT-WF", len(wf) == 44, f"WF=44 (JSON={len(wf)})")

# G-UNIQ: ID 重複ゼロ
for name, items in [("BR", br), ("REQ", req), ("FR/NFR", r), ("AC", ac["items"]), ("FN", fn)]:
    ids = [i["id"] for i in items]
    gate(f"G-UNIQ-{name.split('/')[0]}", len(ids) == len(set(ids)), f"{name} ID 重複ゼロ")

# G-TRC: trace が全 BR をカバー
tr = load(J / "s0/trace.json")
rows = tr.get("items") or tr.get("rows")
allbr = {i["id"] for i in br}
trbr = {x.get("br") or x.get("BR") for x in rows}
gate("G-TRC-BR", trbr == allbr, f"trace 31 行が全 BR をカバー (欠落={sorted(allbr - trbr)})")

# G-TRC-AC: AC target が実在 FR
frids = {i["id"] for i in fr}
tgt = {i["target"] for i in ac["items"]}
gate("G-TRC-AC", tgt <= frids, f"AC target 全実在 (不明={sorted(tgt - frids)})")

# G-GWT: AC 全件に非空 Given/When/Then
nogwt = [i["id"] for i in ac["items"] if not (i.get("given") and i.get("when") and i.get("then"))]
gate("G-GWT", not nogwt, f"AC 全件 GWT 非空 (欠落={nogwt})")

# G-S0: updates の fn_ids = 25 件・重複なし・function-list の slice=S0 と一致
up = load(J / "s0/updates.json")
uitems = up.get("items") or up.get("updates")
fnids = [f for u in uitems for f in u["fn_ids"]]
s0fn = {i["id"] for i in fn if str(i.get("slice")) == "S0"}
gate("G-S0-CNT", len(fnids) == 25 and len(set(fnids)) == 25, "S0 fn_ids=25・重複なし")
gate("G-S0-SET", set(fnids) == s0fn, f"fn_ids == slice S0 集合 (差分={sorted(set(fnids) ^ s0fn)})")

# G-DDL: ddl.sql が MD の DDL ブロックと一致（空行・行末空白は無視）
md_sql = subprocess.run(
    ["awk", "/^```sql$/,/^```$/", str(MD / "s0-contract_v0.1.md")],
    capture_output=True, text=True, check=True,
).stdout
norm = lambda s: [ln.rstrip() for ln in s.splitlines() if ln.rstrip() and not ln.startswith("```")]  # noqa: E731
ddl = (J / "s0/ddl.sql").read_text(encoding="utf-8")
gate("G-DDL-SYNC", norm(md_sql) == norm(ddl), "ddl.sql == MD DDL ブロック")

# G-DDL-APPLY: DDL が空 DB へ適用でき、FK/integrity が通り、テーブル数 21
con = sqlite3.connect(":memory:")
try:
    con.executescript(ddl)
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    ntab = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    gate("G-DDL-APPLY", not fk and integ == "ok" and ntab == 21, f"DDL 適用 (fk={fk}, integrity={integ}, tables={ntab})")
except sqlite3.Error as e:
    gate("G-DDL-APPLY", False, f"DDL 適用失敗: {e}")
finally:
    con.close()

# G-EVK: evidence kind 集合が JSON 契約と DDL CHECK で同一・10 種
ek = load(J / "s0/evidence-kinds.json")
kinds = {k["kind"] for k in (ek.get("items") or ek.get("kinds"))}
m = re.search(r"kind TEXT NOT NULL CHECK \(kind IN \(([^)]*)\)", ddl)
dk = set(re.findall(r"'([a-z_]+)'", m.group(1))) if m else set()
gate("G-EVK", kinds == dk and len(kinds) == 10, f"evidence kind 10 種一致 (差分={sorted(kinds ^ dk)})")

# G-TRN: 遷移表の entity と状態が DDL の enum に含まれる
tra = load(J / "s0/transitions.json")
titems = tra.get("items") or tra.get("transitions")
ents = {t["entity"] for t in titems}
gate("G-TRN-ENT", ents == {"loop_runs", "tasks"}, f"遷移 entity = loop_runs/tasks ({ents})")
enum = {
    "loop_runs": set(re.findall(r"'(\w+)'", re.search(r"loop_runs[\s\S]*?state TEXT NOT NULL CHECK \(state IN \(([^)]*)\)", ddl).group(1))),
    "tasks": set(re.findall(r"'(\w+)'", re.search(r"CREATE TABLE tasks[\s\S]*?state TEXT NOT NULL CHECK \(state IN \(([^)]*)\)", ddl).group(1))),
}
badst = [
    f"{t['entity']}:{s}"
    for t in titems
    for s in ([t.get("from"), t.get("to")] if isinstance(t.get("from"), str) else (t.get("from") or []) + [t.get("to")])
    if s and "/" not in s and s not in enum[t["entity"]]
]
gate("G-TRN-ST", not badst, f"遷移状態が DDL enum 内 (不明={badst})")

print()
if failures:
    print(f"NG: {len(failures)} 件のゲート違反")
    sys.exit(1)
print("OK: 全ゲート PASS")
