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


D = ROOT / "docs/design/json"

# G-JSON: 全 JSON が構文的に妥当
bad = []
for f in glob.glob(str(J / "**/*.json"), recursive=True) + glob.glob(str(D / "**/*.json"), recursive=True):
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
gate("G-CNT-WF", len(wf) == 49, f"WF=49 (JSON={len(wf)})")

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

# G-DDL-APPLY: DDL が空 DB へ適用でき、FK/integrity が通り、テーブル 25・トリガ 11（append-only 10＋TLP 整合）
con = sqlite3.connect(":memory:")
try:
    con.executescript(ddl)
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    ntab = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    ntrg = con.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
    gate("G-DDL-APPLY", not fk and integ == "ok" and ntab == 25 and ntrg == 11,
         f"DDL 適用 (fk={fk}, integrity={integ}, tables={ntab}, triggers={ntrg})")
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
    for s in (t.get("from"), t.get("to"))
    if s and s not in enum[t["entity"]]
]
gate("G-TRN-ST", not badst, f"遷移状態が DDL enum 内・複合表記なし (不明={badst})")

# G-TRN-UNIQ/REACH/TERM/GUARD: 状態機械の決定性（レビュー P0-1 対応）
keys = [(t["entity"], t["from"], t["event"]) for t in titems]
dupkeys = sorted({k for k in keys if keys.count(k) > 1})
gate("G-TRN-UNIQ", not dupkeys, f"(entity, from, event) が一意 (重複={dupkeys})")
INITIAL = {"loop_runs": {"pending"}, "tasks": {"pending"}}
TERMINAL = {"loop_runs": {"completed", "failed", "escalated", "cancelled"},
            "tasks": {"done", "failed", "escalated"}}
unreach = []
for e, states in enum.items():
    edges: dict[str, set] = {}
    for t in titems:
        if t["entity"] == e:
            edges.setdefault(t["from"], set()).add(t["to"])
    seen = set(INITIAL[e])
    stack = list(INITIAL[e])
    while stack:
        for nxt in edges.get(stack.pop(), set()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    unreach += [f"{e}:{s}" for s in sorted(states - seen)]
gate("G-TRN-REACH", not unreach, f"enum の全状態が初期状態から BFS 到達可能 (到達不能={unreach})")
fromterm = [f"{t['entity']}:{t['from']}" for t in titems if t["from"] in TERMINAL[t["entity"]]]
gate("G-TRN-TERM", not fromterm, f"終端状態からの遷移なし (違反={fromterm})")
noguard = [f"{t['entity']}:{t['from']}:{t['event']}" for t in titems if not (t.get("guard") or "").strip()]
gate("G-TRN-GUARD", not noguard, f"全遷移に非空ガード (欠落={noguard})")

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

# G-CONFIRM-DIGEST: 承認は内容へ束縛する（レビュー P0-4 対応）。
# confirmed 文書ごとに、approvals.md のいずれかの行の digest 列（sha256 先頭 12）が現内容と一致すること。
import hashlib


def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


# 行単位で束縛: (対象, 版, confirmed) の承認行が持つ digest 集合と照合する（digest の行間移植を封じる）
receipt_index: dict[tuple, set] = {}
for row in approvals.splitlines():
    cells = [c.strip() for c in row.split("|")]
    if len(cells) >= 8 and re.match(r"\d{4}-\d{2}-\d{2}", cells[1]):
        # cells: ['', 日付, 対象, 版, 判断, 承認者, digest, 備考, '']
        if cells[4] == "confirmed" and re.fullmatch(r"[0-9a-f]{12}", cells[6]):
            receipt_index.setdefault((cells[2], cells[3]), set()).add(cells[6])


def has_receipt(p: Path) -> bool:
    base = re.sub(r"_v[\d.]+$", "", p.stem)
    mver = re.search(r"_v([\d.]+)$", p.stem)
    ver = f"v{mver.group(1)}" if mver else "-"
    return sha12(p) in receipt_index.get((base, ver), set())


unbound = []
for f in glob.glob(str(ROOT / "docs/**/*.md"), recursive=True):
    p = Path(f)
    if p.name == "approvals.md":
        continue
    if re.search(r"status:\s*\*{0,2}confirmed\*{0,2}", p.read_text(encoding="utf-8")[:600]):
        if not has_receipt(p):
            unbound.append(f"{p.name}:{sha12(p)}")
gate("G-CONFIRM-DIGEST", not unbound,
     f"confirmed 文書の現内容 digest が同一 (対象, 版, confirmed) の承認行に存在 (未束縛={unbound})")

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

# G-CMP / G-ITC / G-PAIR2: 基本設計②↔総合テスト設計④ のペアゲート
cmp_path, itc_path = D / "components.json", D / "itest.json"
if cmp_path.exists() and itc_path.exists():
    comps = load(cmp_path)["items"]
    itest = load(itc_path)
    itcs = itest["items"]
    cmpids = [c["id"] for c in comps]
    itcids = [t["id"] for t in itcs]
    gate("G-CMP-CNT", len(comps) == 13, f"CMP=13 (実={len(comps)})")
    gate("G-CMP-UNIQ", len(cmpids) == len(set(cmpids)), "CMP ID 重複ゼロ")
    # CMP の fn_ids が S0 25 機能を重複なく完全被覆
    cfn = [f for c in comps for f in c["fn_ids"]]
    gate("G-CMP-FN", len(cfn) == len(set(cfn)) and set(cfn) == s0fn,
         f"CMP が S0 25 FN を重複なく完全被覆 (差分={sorted(set(cfn) ^ s0fn)})")
    gate("G-ITC-CNT", len(itcs) == 16, f"ITC=16 (実={len(itcs)})")
    gate("G-ITC-UNIQ", len(itcids) == len(set(itcids)), "ITC ID 重複ゼロ")
    # ②↔④ 双方向: ITC の参照 CMP 実在＋全 CMP が 1 件以上の ITC に登場
    refcmp = {c for t in itcs for c in t["cmp"]}
    gate("G-ITC-CMP", refcmp == set(cmpids),
         f"ITC↔CMP 双方向カバー (不明={sorted(refcmp - set(cmpids))}, 未カバー={sorted(set(cmpids) - refcmp)})")
    # AC 連結: 参照 AC 実在＋全 19 AC が総合テストからも参照される
    acids2 = {i["id"] for i in ac["items"]}
    refac = {a for t in itcs for a in t["ac"]}
    gate("G-ITC-AC", refac == acids2,
         f"ITC↔AC 双方向カバー (不明={sorted(refac - acids2)}, 未カバー={sorted(acids2 - refac)})")
    rej2 = [t for t in itcs if t.get("polarity") == "reject"]
    gate("G-ITC-REJ", len(rej2) >= 7, f"総合テストの fail-close 拒否系 >=7 (実={len(rej2)})")
    badup2 = [t["id"] for t in itcs if t.get("update") not in ("S0.1", "S0.2", "S0.3")]
    gate("G-ITC-UPD", not badup2, f"全 ITC が S0.1〜S0.3 に割当 (未割当={badup2})")
    # ②↔④ 対称ヘッダ＋ペア台帳の文書実在
    bd_head = (ROOT / "docs/design/basic-design_v0.1.md").read_text(encoding="utf-8")[:800]
    it_head = (ROOT / "docs/design/integration-test-design_v0.1.md").read_text(encoding="utf-8")[:800]
    pair_docs_ok = all((ROOT / "docs/design" / p[k]).exists()
                       for p in itest.get("pairs", []) for k in ("design_doc", "test_doc"))
    gate("G-PAIR2-HDR",
         "pair:" in bd_head and "integration-test-design" in bd_head
         and "pair:" in it_head and "basic-design" in it_head
         and bool(itest.get("pairs")) and pair_docs_ok,
         "②↔④ 対称 pair 参照＋ペア台帳文書実在")
else:
    gate("G-PAIR2-EXIST", False, "components.json / itest.json（②↔④ ペア正本）が存在しない")

# G-DU / G-UTC / G-PAIR3: 詳細設計⑤↔単体テスト設計⑥ のペアゲート
du_path, ut_path = D / "detailed.json", D / "utest.json"
if du_path.exists() and ut_path.exists():
    dus = load(du_path)["items"]
    utest = load(ut_path)
    uitems2 = utest["items"]
    duids = [d["id"] for d in dus]
    gate("G-DU-CNT", len(dus) == 23, f"DU=23 (実={len(dus)})")
    gate("G-DU-UNIQ", len(duids) == len(set(duids)), "DU ID 重複ゼロ")
    # DU の cmp 実在＋全 CMP に 1 件以上の DU、FN 被覆は CMP と同一集合
    ducmp = {d["cmp"] for d in dus}
    dufn = [f for d in dus for f in d["fn_ids"]]
    gate("G-DU-CMP", ducmp == set(cmpids) if cmp_path.exists() else False,
         f"DU↔CMP 双方向 (不明={sorted(ducmp - set(cmpids))}, 未カバー={sorted(set(cmpids) - ducmp)})")
    gate("G-DU-FN", len(dufn) == len(set(dufn)) and set(dufn) == s0fn,
         f"DU が S0 25 FN を重複なく完全被覆 (差分={sorted(set(dufn) ^ s0fn)})")
    # 単体割当: 全 59 TC が重複なく実在 DU へ、全 DU が 1 件以上のテストを持つ
    tcall = {t["id"] for t in load(J / "verification.json")["items"]}
    asg = [u for u in uitems2 if u["kind"] == "tc-assignment"]
    extra = [u for u in uitems2 if u["kind"] == "unit-extra"]
    asgids = [u["id"] for u in asg]
    gate("G-UTC-TC", len(asgids) == len(set(asgids)) and set(asgids) == tcall,
         f"全 TC 59 を重複なく DU へ割当 (差分={sorted(set(asgids) ^ tcall)})")
    baddu = sorted({u["du"] for u in uitems2} - set(duids))
    covdu = {u["du"] for u in uitems2}
    gate("G-UTC-DU", not baddu and set(duids) <= covdu,
         f"割当 DU 実在＋全 DU にテストあり (不明={baddu}, 未カバー={sorted(set(duids) - covdu)})")
    gate("G-UTC-CNT", len(uitems2) == 69 and len(extra) == 10, f"UTC=69（割当59＋UT10）(実={len(uitems2)}/{len(extra)})")
    # テストファイルは DU と 1 対 1（衝突なし・DU 内は単一ファイル）
    du2f: dict[str, set] = {}
    for u in uitems2:
        du2f.setdefault(u["du"], set()).add(u.get("test_file"))
    multi = [d for d, fs in du2f.items() if len(fs) != 1 or None in fs]
    files = [next(iter(fs)) for fs in du2f.values()]
    gate("G-UTC-FILE", not multi and len(files) == len(set(files)),
         f"test_file が DU と 1 対 1・衝突なし (違反={multi or [f for f in files if files.count(f) > 1]})")
    # DU↔test file 実在: ⑥宣言の全 test_file と戦略層 STC-I（S0.1）の test_file がディスク上に存在する
    stc_files = []
    stc_path = D / "strategy-tests.json"
    if stc_path.exists():
        stc_files = [it["test_file"] for it in load(stc_path)["items"]
                     if it.get("kind") == "impl" and it.get("update") == "S0.1" and it.get("test_file")]
    missing_tf = sorted({tf for tf in files + stc_files if tf and not (ROOT / tf).exists()})
    gate("G-UTC-FILE-EXIST", not missing_tf,
         f"⑥/STC-I 宣言の test_file が実在（S0.1 未実装分は module-level skip で存在） (欠落={missing_tf})")
    # ⑤↔⑥ 対称ヘッダ＋ペア台帳
    dd_head = (ROOT / "docs/design/detailed-design_v0.1.md").read_text(encoding="utf-8")[:800]
    ut_head = (ROOT / "docs/design/unit-test-design_v0.1.md").read_text(encoding="utf-8")[:800]
    pair3_ok = all((ROOT / "docs/design" / p[k]).exists()
                   for p in utest.get("pairs", []) for k in ("design_doc", "test_doc"))
    gate("G-PAIR3-HDR",
         "pair:" in dd_head and "unit-test-design" in dd_head
         and "pair:" in ut_head and "detailed-design" in ut_head
         and bool(utest.get("pairs")) and pair3_ok,
         "⑤↔⑥ 対称 pair 参照＋ペア台帳文書実在")
else:
    gate("G-PAIR3-EXIST", False, "detailed.json / utest.json（⑤↔⑥ ペア正本）が存在しない")

# ---- 上流戦略ループゲート（2026-08-01 上流戦略インフィニティループ再強化） ----
# 検査は 3 層: schema 構造（required/型/enum）、fixtures/ の valid 受理・invalid 拒否（negative test 常設）、
# DDL・契約文書との突合。schema 検証は自前の最小 JSON Schema 検証器で行う（外部依存なし）。
ST = J / "strategy"
STFX = ST / "fixtures"
TMAP = {"string": str, "integer": int, "number": (int, float), "array": list,
        "object": dict, "null": type(None), "boolean": bool}


def schema_check(schema: dict, doc, path: str = "$") -> list[str]:
    errs: list[str] = []
    if schema.get("type") == "object" or "properties" in schema or "required" in schema:
        if not isinstance(doc, dict):
            return [f"{path}: object でない"]
        errs += [f"{path}.{k}: 必須欠落" for k in schema.get("required", []) if k not in doc]
        if schema.get("additionalProperties") is False:
            errs += [f"{path}.{k}: 未定義フィールド" for k in doc if k not in schema.get("properties", {})]
        for k, sub in schema.get("properties", {}).items():
            if k in doc:
                errs += schema_check(sub, doc[k], f"{path}.{k}")
        return errs
    t = schema.get("type")
    types = t if isinstance(t, list) else ([t] if t else [])
    if types and not any(isinstance(doc, TMAP[x]) for x in types):
        errs.append(f"{path}: 型不一致 {types}")
    if "enum" in schema and doc not in schema["enum"]:
        errs.append(f"{path}: enum 外 ({doc})")
    if isinstance(doc, str):
        if len(doc) < schema.get("minLength", 0):
            errs.append(f"{path}: minLength")
        if "pattern" in schema and not re.search(schema["pattern"], doc):
            errs.append(f"{path}: pattern")
    if isinstance(doc, list):
        if len(doc) < schema.get("minItems", 0):
            errs.append(f"{path}: minItems")
        if schema.get("uniqueItems"):
            seen_items = [json.dumps(x, sort_keys=True, ensure_ascii=False) for x in doc]
            if len(seen_items) != len(set(seen_items)):
                errs.append(f"{path}: uniqueItems 違反")
        if "items" in schema:
            for i2, item in enumerate(doc):
                errs += schema_check(schema["items"], item, f"{path}[{i2}]")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if "minimum" in schema and doc < schema["minimum"]:
            errs.append(f"{path}: minimum")
        if "maximum" in schema and doc > schema["maximum"]:
            errs.append(f"{path}: maximum")
    return errs


STRATEGY_SCHEMAS = [
    "market-observation", "market-model", "segment-context", "problem-model",
    "value-hypothesis", "category-definition", "positioning-hypothesis", "causal-assumption",
    "strategic-choice", "strategic-brief", "tactical-learning-packet", "strategy-revision",
]
missing_sch = [n for n in STRATEGY_SCHEMAS if not (ST / f"{n}.schema.json").exists()]
if missing_sch:
    gate("G-STRAT-BRIEF", False, f"戦略 schema 欠落: {missing_sch}")
else:
    sch = {n: load(ST / f"{n}.schema.json") for n in STRATEGY_SCHEMAS}

    def fx_errs(schema_name: str, fixture: str) -> list[str]:
        return schema_check(sch[schema_name], load(STFX / fixture))

    s0md = (MD / "s0-contract_v0.1.md").read_text(encoding="utf-8")
    slc = (MD / "strategy-learning-contract_v0.1.md").read_text(encoding="utf-8") \
        if (MD / "strategy-learning-contract_v0.1.md").exists() else ""

    # G-STRAT-BRIEF: brief 契約が完全（必須フィールド）＋DDL の保持列・lower CHECK＋開始ガードが brief を要求
    breq = set(sch["strategic-brief"]["required"])
    need_b = {"id", "version", "strategic_choice_id", "segment_context_id", "value_hypothesis_id",
              "desired_recognition_change", "tactical_objective", "media_role", "message_hypothesis",
              "prohibited_patterns", "measurement_plan", "valid_from", "digest"}
    tguard = next((t.get("guard", "") for t in titems
                   if t["entity"] == "loop_runs" and t["from"] == "pending" and t["event"] == "start"), "")
    gate("G-STRAT-BRIEF",
         need_b <= breq and not fx_errs("strategic-brief", "strategic-brief.valid.json")
         and "strategic_brief_id" in ddl and "strategic_brief_digest" in ddl
         and "loop_kind != 'lower'" in ddl and "strategic_brief" in tguard,
         f"brief 契約完全＋DDL 保持列＋下位開始ガードが brief を要求 (必須欠落={sorted(need_b - breq)})")

    # G-STRAT-TRACE: 下流run→brief→choice→VH→SEG→evidence の必須 trace 連鎖＋trace 欠落 fixture の拒否
    chain_ok = (
        {"strategic_choice_id", "segment_context_id", "value_hypothesis_id"} <= breq
        and {"selected_segment_ids", "value_hypothesis_ids", "decision_basis"} <= set(sch["strategic-choice"]["required"])
        and {"segment_context_id", "problem_model_id", "evidence_ids"} <= set(sch["value-hypothesis"]["required"])
        and {"market_model_id", "evidence_ids"} <= set(sch["segment-context"]["required"])
        and {"loop_run_id", "strategic_brief_id"} <= set(sch["tactical-learning-packet"]["required"])
    )
    # 変異自己検査: brief required から value_hypothesis_id を落とした schema では連鎖判定が FAIL すること
    import copy

    def chain_check(schset: dict) -> bool:
        return (
            {"strategic_choice_id", "segment_context_id", "value_hypothesis_id"} <= set(schset["strategic-brief"]["required"])
            and {"selected_segment_ids", "value_hypothesis_ids", "decision_basis"} <= set(schset["strategic-choice"]["required"])
            and {"segment_context_id", "problem_model_id", "evidence_ids"} <= set(schset["value-hypothesis"]["required"])
            and {"market_model_id", "evidence_ids"} <= set(schset["segment-context"]["required"])
            and {"loop_run_id", "strategic_brief_id"} <= set(schset["tactical-learning-packet"]["required"])
        )

    mut = copy.deepcopy(sch)
    mut["strategic-brief"]["required"].remove("value_hypothesis_id")
    gate("G-STRAT-TRACE",
         chain_check(sch) and not chain_check(mut)
         and bool(fx_errs("strategic-brief", "strategic-brief.no-trace.invalid.json")),
         "run→brief→choice→VH→SEG→evidence の trace 必須＋trace 欠落 fixture 拒否＋変異 schema の検出自己検査")

    # G-SEGMENT-CONTEXT: 時間・空間・制約・進行状態・代替行動が必須（minItems/minLength）。
    # 人口統計のみの fixture が拒否され、demographic は required に含まれない（補助変数のみ）
    sreq = set(sch["segment-context"]["required"])
    sprops = sch["segment-context"]["properties"]
    ctx_ok = ({"time_context", "space_context", "constraints", "progress_state",
               "alternative_behaviors", "decision_conditions"} <= sreq
              and all(sprops[k].get("minItems", 0) >= 1
                      for k in ("time_context", "space_context", "constraints", "alternative_behaviors"))
              and sprops["progress_state"].get("minLength", 0) >= 1
              and "demographic_attributes" not in sreq)
    gate("G-SEGMENT-CONTEXT",
         ctx_ok and not fx_errs("segment-context", "segment-context.valid.json")
         and bool(fx_errs("segment-context", "segment-context.demographic-only.invalid.json")),
         "状況ベースセグメント必須＋人口統計のみ fixture を拒否")

    # G-OBS-INTERPRETATION: 観測事実と解釈は別フィールド・別レコード。observation は解釈フィールドを持てず
    # （additionalProperties: false）、解釈は TLP の分離フィールドのみ
    oprops = sch["market-observation"]["properties"]
    treq = set(sch["tactical-learning-packet"]["required"])
    tprops = sch["tactical-learning-packet"]["properties"]

    # packet_kind 条件（schema の条件付き必須は validator/store が強制）
    def tlp_kind_rule(doc: dict) -> bool:
        if doc.get("packet_kind") == "learning":
            return all(k in doc for k in ("causal_interpretation", "hypothesis_assessment"))
        if doc.get("packet_kind") == "failure":
            return (all(k in doc for k in ("failure_fact", "reproduction_conditions", "recovery_conditions"))
                    and "causal_interpretation" not in doc)
        return False

    tlp_v = load(STFX / "tactical-learning-packet.valid.json")
    tlp_f = load(STFX / "tactical-learning-packet.failure.valid.json")
    tlp_fc = load(STFX / "tactical-learning-packet.failure-with-causal.invalid.json")
    gate("G-OBS-INTERPRETATION",
         sch["market-observation"].get("additionalProperties") is False
         and "fact" in sch["market-observation"]["required"]
         and not any("interpret" in k for k in oprops)
         and {"observations", "packet_kind", "recommended_next_action"} <= treq
         and {"causal_interpretation", "hypothesis_assessment", "alternative_explanations",
              "failure_fact", "reproduction_conditions", "recovery_conditions"} <= set(tprops)
         and not fx_errs("market-observation", "market-observation.valid.json")
         and bool(fx_errs("market-observation", "market-observation.mixed-interpretation.invalid.json"))
         and tlp_kind_rule(tlp_v) and tlp_kind_rule(tlp_f) and not tlp_kind_rule(tlp_fc),
         "観測/解釈の分離＋learning/failure packet 二分（failure への因果解釈捏造 fixture を拒否）")

    # G-LEARNING-TRACE: 全 TLP が loop run・brief digest・evidence へ接続
    gate("G-LEARNING-TRACE",
         {"loop_run_id", "strategic_brief_id", "strategic_brief_digest", "evidence_ids"} <= treq
         and tprops["evidence_ids"].get("minItems", 0) >= 1
         and not fx_errs("tactical-learning-packet", "tactical-learning-packet.valid.json")
         and not fx_errs("tactical-learning-packet", "tactical-learning-packet.failure.valid.json")
         and bool(fx_errs("tactical-learning-packet", "tactical-learning-packet.unlinked.invalid.json"))
         and "UNIQUE" in ddl.split("CREATE TABLE tactical_learning_packets")[1].split(");")[0]
         and "tactical_learning_packets_integrity" in ddl,
         "TLP の run/brief digest/evidence 接続＋UNIQUE(loop_run_id)＋整合トリガ＋未接続 fixture を拒否")

    # G-NO-DIRECT-STRATEGY-MUTATION: 上流正本の保護トリガが DDL に実在し、s0-contract §1 が
    # 下流・コネクタ・計測からの直接更新禁止（還流 = TLP のみ）を宣言する
    # 実 DML で拒否を実証する（トリガ名の文字列検査ではなく、UPDATE/DELETE を実行して ABORT を確認）
    def mutation_rejected() -> tuple[bool, str]:
        c2 = sqlite3.connect(":memory:")
        try:
            c2.executescript(ddl)
            c2.execute(
                "INSERT INTO strategic_briefs (brief_key, version, strategic_choice_id, segment_context_id,"
                " value_hypothesis_id, desired_recognition_change, tactical_objective, media_role,"
                " message_hypothesis, measurement_plan_json, valid_from, digest, status, created_at)"
                " VALUES ('SB-G', 1, 'SC-1', 'SEG-1', 'VH-1', 'x', 'y', 'proof', 'm', '[]',"
                " '2026-08-01', ?, 'active', 't')", ("a" * 64,))
            c2.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at)"
                       " VALUES ('upper', 'LP-U', 'running', 'kg', 't')")
            c2.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at,"
                       " parent_loop_run_id, strategic_brief_id, strategic_brief_digest)"
                       " VALUES ('lower', 'LP-W', 'completed', 'kg2', 't', 1, 1, ?)", ("a" * 64,))
            c2.execute(
                "INSERT INTO tactical_learning_packets (packet_key, packet_kind, loop_run_id,"
                " strategic_brief_id, strategic_brief_digest, observations_json, hypothesis_result,"
                " target_hypothesis_ids_json, assessment_reason, causal_interpretation, confidence,"
                " evidence_ids_json, recommended_next_action, created_at)"
                " VALUES ('TLP-G', 'learning', 2, 1, ?, '[]', 'supported', '[]', 'r', 'c', 0.5,"
                " '[\"EV-1\"]', 'continue', 't')",
                ("a" * 64,))
            # DELETE 検査は FK 参照のない brief（id=2）で行う — FK 拒否がトリガ欠落を偽装しないため
            c2.execute(
                "INSERT INTO strategic_briefs (brief_key, version, strategic_choice_id, segment_context_id,"
                " value_hypothesis_id, desired_recognition_change, tactical_objective, media_role,"
                " message_hypothesis, measurement_plan_json, valid_from, digest, status, created_at)"
                " VALUES ('SB-G2', 1, 'SC-1', 'SEG-1', 'VH-1', 'x', 'y', 'proof', 'm', '[]',"
                " '2026-08-01', ?, 'draft', 't')", ("c" * 64,))
            for stmt in ("UPDATE strategic_briefs SET digest = ? WHERE id = 1",
                         "DELETE FROM strategic_briefs WHERE id = 2",
                         "UPDATE tactical_learning_packets SET confidence = 0.9 WHERE id = 1",
                         "DELETE FROM tactical_learning_packets WHERE id = 1"):
                try:
                    c2.execute(stmt, ("b" * 64,)) if "?" in stmt else c2.execute(stmt)
                    return False, f"変異が通過: {stmt}"
                except sqlite3.IntegrityError as ie:
                    if "append-only" not in str(ie):
                        return False, f"トリガ以外の理由で拒否（トリガ欠落を偽装）: {stmt} → {ie}"
            return True, "UPDATE/DELETE 4 系すべて append-only トリガで ABORT"
        except sqlite3.Error as e2:
            return False, f"検査不能: {e2}"
        finally:
            c2.close()

    mrej, mmsg = mutation_rejected()
    gate("G-NO-DIRECT-STRATEGY-MUTATION",
         mrej and "上流戦略正本" in s0md
         and "下流ループ・媒体コネクタ・計測処理は上流戦略正本へ書き込めず" in s0md,
         f"上流正本への UPDATE/DELETE を実 DML で拒否実証（{mmsg}）＋直接更新禁止宣言")

    # G-REVISION-EVIDENCE: revision は根拠・反証・信頼度・対象版必須。
    # 単一計測値だけの自動 accept（支持根拠 <2 の accepted）を拒否する
    rreq = set(sch["strategy-revision"]["required"])

    def rev_rule(doc: dict) -> bool:
        if doc.get("status") != "accepted":
            return True
        # 重複根拠は 1 件扱い（同一 KPI・同一根拠の重複で 2 件扱いしない）
        if len(set(doc.get("supporting_evidence_ids", []))) < 2:
            return False
        # accepted かつ maintain 以外は新版必須（新版 supersedes_id = target_id、単一 transaction — 契約 §3）
        if doc.get("revision_type") != "maintain" and not doc.get("new_version_id"):
            return False
        return True

    vr = load(STFX / "strategy-revision.valid.json")
    ir = load(STFX / "strategy-revision.single-metric-accept.invalid.json")
    dr = load(STFX / "strategy-revision.duplicate-evidence.invalid.json")
    gate("G-REVISION-EVIDENCE",
         {"supporting_evidence_ids", "counter_evidence_ids", "confidence", "target_version"} <= rreq
         and sch["strategy-revision"]["properties"]["supporting_evidence_ids"].get("uniqueItems") is True
         and not schema_check(sch["strategy-revision"], vr) and rev_rule(vr)
         and not rev_rule(ir) and not rev_rule(dr),
         "revision の根拠/反証/信頼度/対象版＋accepted の新版必須＋単一根拠・重複根拠 accept fixture を拒否")

    # G-STRATEGY-VERSION: 上流正本は上書き・削除禁止、supersedes_id の append-only 版管理
    VERSIONED = ["market-model", "segment-context", "problem-model", "value-hypothesis",
                 "category-definition", "positioning-hypothesis", "causal-assumption",
                 "strategic-choice", "strategic-brief"]
    def unversioned(schset: dict) -> list[str]:
        return [n for n in VERSIONED
                if "version" not in schset[n]["required"] or "supersedes_id" not in schset[n]["properties"]]

    mut2 = copy.deepcopy(sch)
    mut2["value-hypothesis"]["required"].remove("version")
    gate("G-STRATEGY-VERSION",
         not unversioned(sch) and bool(unversioned(mut2)) and mrej
         and "supersedes_id INTEGER" in ddl,
         f"全上流モデルが version 必須＋supersedes_id 定義（変異検出自己検査込み）"
         f"＋DDL append-only を実 DML で実証 (欠落={unversioned(sch)})")

    # G-MEDIA-ROLE: 媒体役割は設定可能な台帳語彙。brief は役割と認識変化を必須で持ち、
    # 台帳外の役割（媒体名など）を使う fixture は拒否
    roles_doc = load(ST / "media-roles.json") if (ST / "media-roles.json").exists() else {"roles": []}
    roles = {r["role"] for r in roles_doc.get("roles", [])}
    vb = load(STFX / "strategic-brief.valid.json")
    bb = load(STFX / "strategic-brief.bad-media-role.invalid.json")
    gate("G-MEDIA-ROLE",
         len(roles) >= 12 and {"media_role", "desired_recognition_change"} <= breq
         and vb["media_role"] in roles and bb["media_role"] not in roles,
         f"役割台帳 >=12 語彙＋brief の役割/認識変化必須＋台帳外役割 fixture を拒否 (roles={len(roles)})")

    # G-CONTENT-VALUE-DEFINITION: 主要コンテンツ企画は 5 宣言（問題・認識・比較軸・価値・対象仮説）必須
    cpc = load(ST / "content-plan-contract.json") if (ST / "content-plan-contract.json").exists() else {}
    ckeys = {k["key"] for k in cpc.get("required_keys", [])}
    need_c = {"defined_problem", "recognition_change", "comparison_axes", "defined_value", "target_hypothesis_ids"}
    vp = load(STFX / "content-plan.valid.json")
    ip = load(STFX / "content-plan.missing-recognition.invalid.json")
    gate("G-CONTENT-VALUE-DEFINITION",
         ckeys == need_c and need_c <= set(vp) and not (need_c <= set(ip)),
         f"コンテンツ企画 5 宣言契約＋宣言欠落 fixture を拒否 (契約差分={sorted(ckeys ^ need_c)})")

    # G-STRAT-PAIR: 戦略層 4 文書の相互 pair 参照＋SR/SCM/STC の双方向カバー＋全戦略ゲートに拒否系 STC
    sr_json = load(ST / "sr.json")["items"] if (ST / "sr.json").exists() else []
    sr_md = md_count(MD / "strategy-loop-requirements_v0.1.md", r"\*\*(SR-\d{2})")
    stc = load(D / "strategy-tests.json") if (D / "strategy-tests.json").exists() else {"items": []}
    scm = load(D / "strategy-components.json")["items"] if (D / "strategy-components.json").exists() else []
    sr_ids = {i["id"] for i in sr_json}
    cov_sr = {s for it in stc["items"] for s in it.get("sr", [])}
    cov_scm = {c for it in stc["items"] for c in it.get("scm", [])}
    STRAT_GATES = ["G-STRAT-BRIEF", "G-STRAT-TRACE", "G-SEGMENT-CONTEXT", "G-OBS-INTERPRETATION",
                   "G-LEARNING-TRACE", "G-NO-DIRECT-STRATEGY-MUTATION", "G-REVISION-EVIDENCE",
                   "G-STRATEGY-VERSION", "G-MEDIA-ROLE", "G-CONTENT-VALUE-DEFINITION"]
    neg = {it.get("gate") for it in stc["items"] if it.get("kind") == "gate" and it.get("polarity") == "reject"}
    heads = {n: (p.read_text(encoding="utf-8")[:900] if (p := ROOT / n).exists() else "")
             for n in ["docs/requirements/strategy-loop-requirements_v0.1.md",
                       "docs/requirements/strategy-learning-contract_v0.1.md",
                       "docs/design/strategy-loop-design_v0.1.md",
                       "docs/design/strategy-loop-test-design_v0.1.md"]}
    pair_ok = (all("pair:" in h for h in heads.values())
               and all("strategy-loop-test-design" in heads[n] for n in list(heads)[:3])
               and "strategy-loop-design" in heads["docs/design/strategy-loop-test-design_v0.1.md"])
    missing_fx = [it["fixture"] for it in stc["items"]
                  if it.get("fixture") and not (ROOT / it["fixture"]).exists()]
    # カバレッジ検出の変異自己検査: SR カバレッジを 1 件落とした台帳では検出が働くこと
    stc_mut = [dict(it, sr=[s for s in it.get("sr", []) if s != "SR-04"]) for it in stc["items"]]
    mut_detects = sr_ids != {s for it in stc_mut for s in it.get("sr", [])}
    # AC-SR 配線: 6 件、SR/STC-I への双方向参照が実在（SR→AC-SR→STC-I→DU の一本線）
    acsr = load(ST / "ac-sr.json")["items"] if (ST / "ac-sr.json").exists() else []
    stc_ids = {it["id"] for it in stc["items"]}
    du_ids_all = {d2["id"] for d2 in load(D / "detailed.json")["items"]}
    acsr_ok = (len(acsr) == 6
               and all(a.get("given") and a.get("when") and a.get("then") for a in acsr)
               and all(set(a["sr"]) <= sr_ids and set(a["stc"]) <= stc_ids
                       and set(a["du"]) <= du_ids_all for a in acsr)
               and {x for a in acsr for x in a["stc"]} ==
                   {f"STC-I-0{i}" for i in range(1, 7)})
    gate("G-STRAT-PAIR",
         mut_detects and acsr_ok and
         len(sr_json) == 16 == sr_md and len(scm) == 10 and pair_ok
         and sr_ids == cov_sr and {c["id"] for c in scm} == cov_scm
         and all(g2 in neg for g2 in STRAT_GATES) and not missing_fx,
         f"SR16/SCM10/AC-SR6 双方向カバー＋4 文書相互 pair＋全戦略ゲートに拒否系 STC "
         f"(SR差={sorted(sr_ids ^ cov_sr)}, AC-SR={acsr_ok}, negative欠={sorted(set(STRAT_GATES) - neg)}, fixture欠={missing_fx})")

# G-BASE: デグレ検出（HELIX 日付 ratchet 相当のベースライン方式）
# confirmed 文書のサイレント改変・分母縮小・ゲート削減を停止する。
# 意図的変更は `--update-baseline` でベースラインを同一コミットで更新する。

BASELINE = ROOT / "docs/governance/baseline.json"
current_counts = {"BR": len(br), "REQ": len(req), "FR": len(fr), "NFR": len(nfr),
                  "AC": len(ac["items"]), "FN": len(fn), "BRM": bm, "MR": mr, "WF": len(wf),
                  "CMP": len(comps) if cmp_path.exists() else 0,
                  "ITC": len(itcs) if itc_path.exists() else 0,
                  "DU": len(dus) if du_path.exists() else 0,
                  "UTC": len(uitems2) if ut_path.exists() else 0}
confirmed_docs = sorted(
    str(Path(f).relative_to(ROOT)) for f in glob.glob(str(ROOT / "docs/**/*.md"), recursive=True)
    if re.search(r"status:\s*\*{0,2}confirmed\*{0,2}", Path(f).read_text(encoding="utf-8")[:600])
)
current_hashes = {d: hashlib.sha256((ROOT / d).read_bytes()).hexdigest() for d in confirmed_docs}
gate_count_now = len(re.findall(r'gate\(\s*f?"G-', Path(__file__).read_text(encoding="utf-8")))

# baseline は confirmed MD だけでなく実装入力（JSON 正本・DDL・validator・CI・エージェント規律・hook）も束縛する
ARTIFACT_GLOBS = [
    "docs/requirements/json/**/*.json", "docs/requirements/json/**/*.sql",
    "docs/design/json/**/*.json",
    "scripts/validate_requirements.py", "scripts/hooks/pre-git-gate.sh",
    ".github/workflows/*.yml", "CLAUDE.md", "AGENTS.md",
    "pyproject.toml", "uv.lock",
]
artifact_files = sorted({
    str(Path(f).relative_to(ROOT))
    for g in ARTIFACT_GLOBS for f in glob.glob(str(ROOT / g), recursive=True)
})
current_artifacts = {a: hashlib.sha256((ROOT / a).read_bytes()).hexdigest() for a in artifact_files}

if "--update-baseline" in sys.argv:
    # receipt 束縛: confirmed 文書の現内容 digest が承認ログに存在しない限り baseline を書換えない
    no_receipt = [d for d in confirmed_docs if not has_receipt(ROOT / d)]
    if no_receipt:
        print(f"REFUSED: 承認 receipt（digest 行）のない confirmed 文書があるため baseline を更新しない: {no_receipt}")
        sys.exit(1)
    BASELINE.write_text(json.dumps({
        "updated": "see git log", "counts": current_counts,
        "gate_count": gate_count_now, "confirmed_docs": current_hashes,
        "artifacts": current_artifacts,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"baseline updated: docs={len(current_hashes)}, artifacts={len(current_artifacts)}, gates={gate_count_now}, counts={current_counts}")
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
    # 実装入力（JSON 正本・DDL・validator・CI・規律・hook）の無断改変検出
    adrift = sorted(set(
        [a for a, h in base.get("artifacts", {}).items() if current_artifacts.get(a) != h]
        + [a for a in current_artifacts if a not in base.get("artifacts", {})]
    ))
    gate("G-BASE-ART", "artifacts" in base and not adrift,
         f"実装入力 artifact の無断改変/未登録なし (差分={adrift or '[]'}; 意図的なら --update-baseline)")
else:
    gate("G-BASE-EXIST", False, "baseline.json が存在しない（--update-baseline で生成）")

# G-COUNT-SYNC: 手書きのゲート件数表記が実数と一致（意味整合レビュー対応 — 散在数値のドリフト検出）
count_files = [ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "AGENTS.md",
               ROOT / "docs/governance/requirements-gates.md"] + \
    [Path(f) for f in glob.glob(str(ROOT / "docs/design/*.md"))]
stale_counts = []
for p in count_files:
    text = p.read_text(encoding="utf-8")
    for m in re.findall(r"整合ゲート\s*(\d+)\s*本|（(\d+)\s*ゲート）|ゲート\s*(\d+)\s*本", text):
        n = int(next(x for x in m if x))
        if n != gate_count_now:
            stale_counts.append(f"{p.name}:{n}!={gate_count_now}")
gate("G-COUNT-SYNC", not stale_counts, f"ゲート件数の手書き表記が実数と一致 (乖離={stale_counts})")

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
