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

# G-CONFIRM: status confirmed を名乗る文書は approvals.md に承認行が実在する（freeze 偽装検出）
approvals = (ROOT / "docs/governance/approvals.md").read_text(encoding="utf-8")
imposters = []
for f in glob.glob(str(ROOT / "docs/**/*.md"), recursive=True):
    p = Path(f)
    if p.name == "approvals.md":
        continue
    head = p.read_text(encoding="utf-8")[:600]
    base = re.sub(r"_v[\d.]+$", "", p.stem)  # approvals.md は対象と版を別列で持つ
    if re.search(r"status:\s*\*{0,2}confirmed\*{0,2}", head) and base not in approvals:
        imposters.append(p.name)
gate("G-CONFIRM", not imposters, f"confirmed 文書は承認ログに実在 (偽装={imposters})")

# G-SRC-FRESH: br-media の構造調査値は確認日必須・90 日で失効（出典腐敗検査）
import datetime

MAX_AGE_DAYS = 90
today = datetime.date.today()
stale = []
for f in glob.glob(str(J / "br-media/*.json")):
    if "index" in f:
        continue
    d = load(Path(f))
    c = d.get("structure_checked")
    try:
        age = (today - datetime.date.fromisoformat(c)).days
        if age > MAX_AGE_DAYS or age < 0:
            stale.append(f"{Path(f).name}:{c}")
    except (TypeError, ValueError):
        stale.append(f"{Path(f).name}:missing")
gate("G-SRC-FRESH", not stale, f"媒体構造の調査日が {MAX_AGE_DAYS} 日以内 (失効={stale})")

# G-POC-EXIT: PoC は出口 2 軸 schema に適合（confirmed には promotion_strategy 必須）
poc = load(J / "ltw/poc.json")
es = poc.get("exit_schema", {})
badpoc = []
for i in poc["items"]:
    do, ps = i.get("decision_outcome", "MISSING"), i.get("promotion_strategy", "MISSING")
    if do not in (es.get("decision_outcome", []) + [None]) or ps not in (es.get("promotion_strategy", []) + [None]):
        badpoc.append(f"{i['id']}:invalid({do},{ps})")
    elif do == "confirmed" and ps is None:
        badpoc.append(f"{i['id']}:confirmed-without-strategy")
gate("G-POC-EXIT", bool(es) and not badpoc, f"PoC 出口 2 軸 schema 適合 (違反={badpoc})")

# G-SUBSTANCE: 全エンティティに本文実体（空・スタブ本文の完了僭称を封じる — AP-13 文書版）
hollow = []
for name, items in [("BR", br), ("REQ", req), ("FR/NFR", r), ("FN", fn)]:
    for i in items:
        body = " ".join(filter(None, [i.get("title"), i.get("summary"), i.get("text")]))
        if len(body.strip()) < 8:
            hollow.append(i["id"])
for f in glob.glob(str(J / "br-media/*.json")) + glob.glob(str(J / "mr/*.json")):
    if "index" in f:
        continue
    for i in load(Path(f))["items"]:
        if len((i.get("text") or "").strip()) < 8:
            hollow.append(i["id"])
gate("G-SUBSTANCE", not hollow, f"全エンティティ本文実体あり (空={hollow})")

# G-PAIR: 対のテスト/検証設計（HELIX pair gate 相当）
ver_path = J / "verification.json"
if ver_path.exists():
    ver = load(ver_path)
    tcs = ver["items"]
    tcids = [t["id"] for t in tcs]
    gate("G-PAIR-UNIQ", len(tcids) == len(set(tcids)), "TC ID 重複ゼロ")
    # 全 19 AC が 1 件以上の TC でカバーされる（双方向: TC の ac も実在する AC）
    acids = {i["id"] for i in ac["items"]}
    covered = {t["ac"] for t in tcs if t.get("ac")}
    gate("G-PAIR-AC", acids <= covered, f"全 AC にテストケース対あり (未カバー={sorted(acids - covered)})")
    gate("G-PAIR-TC", {t["ac"] for t in tcs if t.get("ac", "").startswith("AC-")} <= acids,
         f"TC の参照 AC 全実在 (不明={sorted({t['ac'] for t in tcs if t.get('ac','').startswith('AC-')} - acids)})")
    # 拒否系（fail-close 検証）が存在し、全 TC が S0.1〜S0.3 に割当済み
    rej = [t for t in tcs if t.get("polarity") == "reject"]
    gate("G-PAIR-REJ", len(rej) >= 7, f"fail-close 拒否系テスト >=7 (実={len(rej)})")
    badup = [t["id"] for t in tcs if t.get("update") not in ("S0.1", "S0.2", "S0.3")]
    gate("G-PAIR-UPD", not badup, f"全 TC が S0.1〜S0.3 に割当 (未割当={badup})")
    # ペア台帳の双方向性: 対象文書が実在する
    missing_docs = [p["design_doc"] for p in ver.get("pairs", []) if not (ROOT / "docs/requirements" / p["design_doc"]).exists()]
    gate("G-PAIR-DOC", bool(ver.get("pairs")) and not missing_docs, f"ペア台帳の設計文書実在 (欠落={missing_docs})")
else:
    gate("G-PAIR-EXIST", False, "verification.json（対の検証設計）が存在しない")

# G-PAIR-HDR: HELIX 式 ①↔③ の対称参照 — 設計文書ヘッダに pair 行、検証設計側にも対象列挙
PAIRED_DOCS = [
    "requirements_v0.1.md", "s0-contract_v0.1.md", "br-media_v0.1.md",
    "loop-task-workflow_v0.1.md", "media-requirements_v0.1.md",
]
vd_text = (MD / "verification-design_v0.1.md").read_text(encoding="utf-8")
nopair = []
for name in PAIRED_DOCS:
    head = (MD / name).read_text(encoding="utf-8")[:800]
    if "pair:" not in head or "verification-design" not in head:
        nopair.append(f"{name}:①側 pair 行なし")
    if name not in vd_text:
        nopair.append(f"{name}:③側の対象列挙なし")
gate("G-PAIR-HDR", not nopair, f"①↔③ 対称参照 (欠落={nopair})")

# G-BASE: デグレ検出（HELIX 日付 ratchet 相当のベースライン方式）
# confirmed 文書のサイレント改変・分母縮小・ゲート削減を停止する。
# 意図的変更は `--update-baseline` でベースラインを同一コミットで更新する。
import hashlib

BASELINE = ROOT / "docs/governance/baseline.json"
current_counts = {"BR": len(br), "REQ": len(req), "FR": len(fr), "NFR": len(nfr),
                  "AC": len(ac["items"]), "FN": len(fn), "BRM": bm, "MR": mr, "WF": len(wf)}
confirmed_docs = sorted(
    str(Path(f).relative_to(ROOT)) for f in glob.glob(str(ROOT / "docs/**/*.md"), recursive=True)
    if re.search(r"status:\s*\*{0,2}confirmed\*{0,2}", Path(f).read_text(encoding="utf-8")[:600])
)
current_hashes = {d: hashlib.sha256((ROOT / d).read_bytes()).hexdigest() for d in confirmed_docs}
gate_count_now = len(re.findall(r'gate\(\s*f?"G-', Path(__file__).read_text(encoding="utf-8")))

if "--update-baseline" in sys.argv:
    BASELINE.write_text(json.dumps({
        "updated": "see git log", "counts": current_counts,
        "gate_count": gate_count_now, "confirmed_docs": current_hashes,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"baseline updated: docs={len(current_hashes)}, gates={gate_count_now}, counts={current_counts}")
    sys.exit(0)

if BASELINE.exists():
    base = load(BASELINE)
    # 改変検出: confirmed 文書のハッシュがベースラインと一致（意図的変更は baseline 同時更新）
    drift = [d for d, h in base["confirmed_docs"].items()
             if current_hashes.get(d) != h]
    gate("G-BASE-HASH", not drift,
         f"confirmed 文書の無断改変なし (差分={drift or '[]'}; 意図的なら --update-baseline を同一コミットで)")
    # 後退検出: confirmed が draft へ戻っていない（ベースラインの文書が confirmed 集合に残存）
    demoted = [d for d in base["confirmed_docs"] if d not in current_hashes]
    gate("G-BASE-STATUS", not demoted, f"confirmed の降格なし (降格={demoted})")
    # ratchet: 分母縮小・ゲート削減の禁止
    shrunk = [f"{k}:{base['counts'][k]}→{v}" for k, v in current_counts.items() if v < base["counts"].get(k, 0)]
    gate("G-BASE-RATCHET", not shrunk and gate_count_now >= base["gate_count"],
         f"分母縮小/ゲート削減なし (縮小={shrunk}, gates={gate_count_now}>={base['gate_count']})")
else:
    gate("G-BASE-EXIST", False, "baseline.json が存在しない（--update-baseline で生成）")

# G-WIRING: メタゲート — スクリプトのゲート ID と台帳・CI 配線の突合
src = Path(__file__).read_text(encoding="utf-8")
script_gates = set(re.findall(r'gate\(\s*f?"(G-[A-Z0-9-]+)', src))
ledger = (ROOT / "docs/governance/requirements-gates.md").read_text(encoding="utf-8")
# 台帳は「G-CNT-BR/REQ/FR」のスラッシュ族表記を許す: 展開して照合
ledger_gates: set[str] = set()
for m in re.findall(r"G-[A-Z0-9]+(?:-[A-Z0-9]+)*(?:/[A-Z0-9]+)*", ledger):
    parts = m.split("/")
    ledger_gates.add(parts[0])
    prefix = parts[0].rsplit("-", 1)[0]
    ledger_gates.update(f"{prefix}-{s}" for s in parts[1:])
# f-string 動的 ID（"G-UNIQ-" 等）は族プレフィクスとして照合
unwired = sorted(
    g for g in script_gates
    if not (g in ledger_gates or g.rstrip("-") in ledger_gates
            or (g.endswith("-") and any(lg.startswith(g) for lg in ledger_gates)))
)
ci = (ROOT / ".github/workflows/docs-ci.yml").read_text(encoding="utf-8")
gate("G-WIRING", "scripts/validate_requirements.py" in ci and not unwired,
     f"CI 配線 + 台帳掲載 (未掲載={unwired})")

print()
if failures:
    print(f"NG: {len(failures)} 件のゲート違反")
    sys.exit(1)
print("OK: 全ゲート PASS")
