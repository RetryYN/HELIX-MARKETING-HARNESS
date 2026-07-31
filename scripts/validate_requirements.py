#!/usr/bin/env python3
"""要件整合ゲート（fail-close）。

docs/requirements/ の MD と JSON 正本の整合を検証する。1 件でも FAIL があれば exit 1。
ゲート一覧は docs/governance/requirements-gates.md を正本とする。
"""

import glob
import hashlib
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


def committed_max_skipped():
    """**親コミット**の baseline.json から skip 上限を読む。

    CI では検査対象コミット自身が HEAD になるため、HEAD を比較元にすると引き上げを
    コミットするだけで検査を素通りできる。親（HEAD^）= 変更前の状態を比較元にする。
    親が無い（初回コミット）場合は None を返し、ラチェット検査を適用しない。
    """
    for rev in ("HEAD^", "HEAD"):  # 親が無いリポジトリでは HEAD へフォールバック
        out = subprocess.run(  # noqa: S603
            ["git", "show", f"{rev}:docs/governance/baseline.json"],  # noqa: S607
            capture_output=True, text=True, check=False, cwd=ROOT)
        if out.returncode == 0:
            try:
                return json.loads(out.stdout).get("max_skipped")
            except json.JSONDecodeError:
                return None
        if rev == "HEAD^" and "unknown revision" not in (out.stderr or ""):
            continue
    return None


def skip_raise_approved(prev, new) -> bool:
    """skip 上限の引き上げに対する **PO 承認行**（構造化テーブル行）が approvals.md にあるか。"""
    appr = (ROOT / "docs/governance/approvals.md").read_text(encoding="utf-8")
    pat = re.compile(
        rf"^\|[^|]*\|\s*skip-budget\s*\|[^|]*{prev}→{new}[^|]*\|\s*approved\s*\|\s*PO\s*\|",
        re.MULTILINE)
    return bool(pat.search(appr))


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
gate("G-CNT-BR", len(br) == 38 == md_count(MD / "br-backbone_v0.1.md", r"\*\*(BR-[A-I]\d)\*\*"), "BR=38 (MD/JSON)")

req = load(J / "req.json")["items"]
gate("G-CNT-REQ", len(req) == 52 == md_count(MD / "requirement-list_v0.1.md", r"(REQ-\d{3})"), "REQ=52 (MD/JSON)")

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
gate("G-TRC-BR", trbr == allbr, f"trace 38 行が全 BR をカバー (欠落={sorted(allbr - trbr)})")

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

# G-DDL-APPLY: DDL が空 DB へ適用でき、FK/integrity が通り、テーブル 25・トリガ 14（append-only 10＋TLP 整合 3＋brief 不変 1）
con = sqlite3.connect(":memory:")
try:
    con.executescript(ddl)
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    ntab = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    ntrg = con.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
    gate("G-DDL-APPLY", not fk and integ == "ok" and ntab == 25 and ntrg == 14,
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
         and "tactical_learning_packets_integrity" in ddl
         and "同一 transaction で tactical_learning_packet の" in s0md
         and "packet を持たない終端 lower run = 0 件" in s0md,
         "TLP の接続＋UNIQUE＋整合トリガ＋最低 1 件の kernel 契約/孤児検査宣言＋未接続 fixture を拒否")

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
                " target_hypothesis_ids_json, assessment_reason, causal_interpretation,"
                " alternative_explanations_json, confidence,"
                " evidence_ids_json, recommended_next_action, created_at)"
                " VALUES ('TLP-G', 'learning', 2, 1, ?, '[\"OBS-1\"]', 'supported', '[]', 'r', 'c',"
                " '[\"ALT-1\"]', 0.5, '[\"EV-1\"]', 'continue', 't')",
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
    skip_budget = json.loads((ROOT / "tests" / "skip-budget.json").read_text(encoding="utf-8"))
    # クロージャー §3: 主要分母は新契約体系。旧 AC19／TC59／UTC69 は historical_counts へ退避
    duc_now = load(D / "du-contracts.json")["items"]
    contract_counts = {
        "AC_CONTRACT": len(load(J / "ac" / "ac-contracts.json")["items"]),
        "TCC": len(load(J / "verification" / "tc-contracts.json")["items"]),
        "API": sum(len(x["apis"]) for x in duc_now),
        "API_UT": len({u for x in duc_now for a in x["apis"] for u in a.get("ut", [])}),
    }
    historical_counts = {"AC_LEGACY": 19, "AC_DEFERRED_LEGACY": 17, "TC_LEGACY": 59, "UTC_LEGACY": 69}
    prev_skip = committed_max_skipped()
    if prev_skip is not None and skip_budget["max_skipped"] > prev_skip \
            and not skip_raise_approved(prev_skip, skip_budget["max_skipped"]):
        print(f"REFUSED: skip 上限の引き上げ（{prev_skip}→{skip_budget['max_skipped']}）には "
              "approvals.md の構造化 PO 承認行（skip-budget 列・approved 判定・承認者 PO）が必要")
        sys.exit(1)
    BASELINE.write_text(json.dumps({
        "updated": "see git log", "counts": current_counts,
        "gate_count": gate_count_now, "max_skipped": skip_budget["max_skipped"],
        "contract_counts": contract_counts, "historical_counts": historical_counts,
        "confirmed_docs": current_hashes, "artifacts": current_artifacts,
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
    _duc = load(D / "du-contracts.json")["items"]
    cur_cc = {"AC_CONTRACT": len(load(J / "ac" / "ac-contracts.json")["items"]),
              "TCC": len(load(J / "verification" / "tc-contracts.json")["items"]),
              "API": sum(len(x["apis"]) for x in _duc),
              "API_UT": len({u for x in _duc for a in x["apis"] for u in a.get("ut", [])})}
    shrunk += [f"{k}:{base.get('contract_counts', {}).get(k)}→{v}" for k, v in cur_cc.items()
               if v < base.get("contract_counts", {}).get(k, 0)]
    # skip 上限のラチェット: 比較対象は **git HEAD にコミット済みの** baseline（作業ツリーの
    # 同時改変では回避できない）。引き上げには approvals.md の PO 承認行が別途必要。
    cur_skip = json.loads((ROOT / "tests" / "skip-budget.json").read_text(encoding="utf-8"))["max_skipped"]
    committed = committed_max_skipped()
    skip_raised = committed is not None and cur_skip > committed
    skip_ok_by_approval = skip_raised and skip_raise_approved(committed, cur_skip)
    skip_up = skip_raised and not skip_ok_by_approval
    skip_note = "承認済み引上げ" if skip_ok_by_approval else ("引上げなし" if not skip_raised else "未承認引上げ")
    gate("G-BASE-RATCHET", not shrunk and gate_count_now >= base["gate_count"] and not skip_up,
         f"分母縮小/ゲート削減なし・skip 上限は{skip_note} (縮小={shrunk}, "
         f"gates={gate_count_now}>={base['gate_count']}, skip={cur_skip} vs 親={committed})")
    # 実装入力（JSON 正本・DDL・validator・CI・規律・hook）の無断改変検出
    adrift = sorted(set(
        [a for a, h in base.get("artifacts", {}).items() if current_artifacts.get(a) != h]
        + [a for a in current_artifacts if a not in base.get("artifacts", {})]
    ))
    gate("G-BASE-ART", "artifacts" in base and not adrift,
         f"実装入力 artifact の無断改変/未登録なし (差分={adrift or '[]'}; 意図的なら --update-baseline)")
else:
    gate("G-BASE-EXIST", False, "baseline.json が存在しない（--update-baseline で生成）")

# G-REQ-CONTRACT: BR 構造化契約（全層再降下 §2 — 1 行要求の禁止・12 要求群の被覆・生成ビュー同期）
MANDATED_GROUPS = {
    "brand-isolation", "upstream-downstream-separation", "hypothesis-refutation-revision",
    "kpi-crossover", "multi-media-campaign", "content-value-definition", "zero-ad-spend",
    "ethics-line", "human-ai-boundary", "evidence-resume-idempotency", "external-ops-approval",
    "learning-failure-packet",
}
try:
    brc_schema = load(J / "br" / "br-contract.schema.json")
    brc = load(J / "br" / "br-contracts.json")["items"]
    brc_errs: list[str] = []
    for it in brc:
        brc_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(brc_schema, it)]
    brc_ids = {it["id"] for it in brc}
    br_ids = {i["id"] for i in br}
    req_ids = {i["id"] for i in req}
    covered_groups = {g for it in brc for g in it["mandated_groups"]}
    bad_req_refs = [f"{it['id']}→{r}" for it in brc for r in it["trace_down"]["req"] if r not in req_ids]
    view_sync = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "scripts/render_views.py"), "--check"],
        capture_output=True, text=True, check=False,
    ).returncode == 0
    gate("G-REQ-CONTRACT",
         not brc_errs and brc_ids == br_ids and covered_groups == MANDATED_GROUPS
         and not bad_req_refs and view_sync,
         "BR 契約: schema 適合＋全 BR 被覆＋12 要求群被覆＋REQ 参照実在＋ビュー同期 "
         f"(schema={brc_errs[:3]}, BR差={sorted(brc_ids ^ br_ids)}, "
         f"群欠落={sorted(MANDATED_GROUPS - covered_groups)}, REQ参照={bad_req_refs[:3]}, view={view_sync})")
except FileNotFoundError as e:
    gate("G-REQ-CONTRACT", False, f"BR 契約正本が存在しない: {e}")

# ---- 全層再降下 §3-§8: 粒度ゲートの検出関数（本番ゲートと G-DESCENT-SELFTEST が共用） ----
POLARITIES = {"normal", "reject", "boundary-recovery"}


def detect_polarity_gaps(contracts, acs) -> list[str]:
    """S0 契約で 3 極性が AC でも理由付き N/A でも満たされない箇所を列挙する。"""
    by_t: dict[str, set] = {}
    for a in acs:
        by_t.setdefault(a["target"], set()).add(a["polarity"])
    bad: list[str] = []
    for c in contracts:
        if c["slice"] != "S0":
            continue
        have = by_t.get(c["id"], set())
        na = set(c.get("ac_na", {}).keys())
        if (have | na) < POLARITIES or (have & na):
            bad.append(f"{c['id']}:{sorted(POLARITIES - have - na) or '重複NA'}")
    return bad


def detect_invariant_gaps(contracts, acs) -> list[str]:
    """S0 契約の各不変条件が『固有の』負方向 AC を持たない箇所を列挙する。

    同一 AC を複数の invariant に使い回すと意味的な個別対応にならないため、
    契約内で負方向 AC の重複使用も欠陥として扱う（Sol major 対応）。
    """
    by_id = {a["id"]: a for a in acs}
    bad: list[str] = []
    for c in contracts:
        if c["slice"] != "S0":
            continue
        imap = c.get("invariant_ac_map")
        if not imap or len(imap) != len(c["invariants"]):
            bad.append(f"{c['id']}:map{len(imap or [])}!=inv{len(c['invariants'])}")
            continue
        used_neg: set[str] = set()
        for i, grp in enumerate(imap):
            refs = [by_id.get(a) for a in grp]
            if any(r is None for r in refs):
                bad.append(f"{c['id']}[{i}]:AC不在")
                continue
            if any(r["target"] != c["id"] for r in refs):
                bad.append(f"{c['id']}[{i}]:target不一致")
                continue
            neg = {r["id"] for r in refs
                   if (r["polarity"] == "reject" and r["error_type"] not in ("なし", ""))
                   or r["polarity"] == "boundary-recovery"}
            if not neg:
                bad.append(f"{c['id']}[{i}]:負方向AC欠落")
            elif neg & used_neg:
                bad.append(f"{c['id']}[{i}]:負方向AC使い回し{sorted(neg & used_neg)}")
            else:
                used_neg |= neg
    return bad


def detect_unknown_tables(dus, tables) -> list[str]:
    """DU の db_read/db_write に DDL 非実在テーブルが含まれる箇所を列挙する。"""
    return sorted({f"{d['id']}:{t}" for d in dus for t in d["db_read"] + d["db_write"]
                   if t.split("（")[0] not in tables})


def detect_contract_table_faults(contracts, tables, trn_states) -> list[str]:
    """FR/SR 契約の tables 表記・state_transitions が DDL/遷移正本と食い違う箇所を列挙する。

    接頭辞に一致しない表記や未知 entity は『検査対象外』にせず欠陥として扱う（fail-open の排除）。
    """
    bad: list[str] = []
    for c in contracts:
        for entry in c["tables"]:
            m = re.match(r"^(?:r|w|rw)[:：]\s*([a-z_]+)", entry)
            if m:
                if m.group(1) not in tables:
                    bad.append(f"{c['id']}:未知表{m.group(1)}")
            elif not entry.startswith("参照:"):
                bad.append(f"{c['id']}:表記不正『{entry[:24]}』")
        for entry in c["state_transitions"]:
            ent = entry.split(":")[0].split("：")[0].strip()
            if ent in trn_states:
                # 正準状態機械（loop_runs/tasks）— from/to が enum 内であること
                for fr_s, to_s in re.findall(r"([a-z_]+)\s*→\s*([a-z_]+)", entry):
                    if fr_s not in trn_states[ent] or to_s not in trn_states[ent]:
                        bad.append(f"{c['id']}:未知状態{fr_s}→{to_s}")
            elif entry.startswith("テーブル列:"):
                # 状態機械外のテーブル列寿命 — テーブルが DDL に実在すること
                m2 = re.match(r"テーブル列:\s*([a-z_]+)\.([a-z_]+)\s*:", entry)
                if not m2:
                    bad.append(f"{c['id']}:列寿命表記不正『{entry[:24]}』")
                elif m2.group(1) not in tables:
                    bad.append(f"{c['id']}:未知表{m2.group(1)}（列寿命）")
            elif not entry.startswith("参照:"):
                bad.append(f"{c['id']}:未知entity『{ent[:20]}』")
    return bad


def detect_tc_bidir_faults(tcs, acs) -> list[str]:
    """TC の AC 参照が実在しない箇所を列挙する。"""
    ids = {a["id"] for a in acs}
    return [f"{t['id']}→{a}" for t in tcs for a in t["ac"] if a not in ids]


def detect_api_ut_faults(dus, tests_dir) -> list[str]:
    """API 単位の UT 割当・参照実在・設計リンクの欠陥を列挙する。

    設計フェーズでは UT は test-first スタブだが、各スタブは
    「どの DU のどの API を検証するか」を skip 理由で宣言していなければならない
    （名目 UT の匿名化を禁止 — 実行検証は S0.1 で red→green）。
    """
    bad: list[str] = []
    for d in dus:
        uts = set(d["trace"]["ut"])
        api_uts: set[str] = set()
        for a in d["apis"]:
            refs = a.get("ut") or []
            if not refs:
                bad.append(f"{d['id']}:{a['signature'][:28]}:UTなし")
                continue
            api_uts |= set(refs)
            if not set(refs) <= uts:
                bad.append(f"{d['id']}:{a['signature'][:28]}:trace外UT")
        if uts - api_uts:
            bad.append(f"{d['id']}:宙吊りUT{sorted(uts - api_uts)[:2]}")
        owner_apis: dict[str, set] = {}
        for a in d["apis"]:
            m0 = re.match(r"def (\w+)", a["signature"])
            if m0:
                for u in a.get("ut", []):
                    owner_apis.setdefault(u, set()).add(m0.group(1))
        for ref in sorted(uts):
            if "::" not in ref:
                bad.append(f"{d['id']}:{ref}:形式")
                continue
            fname, tname = ref.split("::", 1)
            fp = tests_dir / fname
            if not fp.exists():
                bad.append(f"{d['id']}:{ref}:ファイル不在")
                continue
            txt = fp.read_text(encoding="utf-8")
            m = re.search(rf"\ndef {re.escape(tname)}\b", txt)
            if m is None:
                bad.append(f"{d['id']}:{ref}:def 不在")
                continue
            # デコレータは複数行に折り返される場合があるため、直前の空行までを装飾部とみなす
            head = txt[:m.start()]
            decos = head[head.rfind("\n\n"):]
            body = txt[m.start():][:600]
            if "skip" in decos or "NotImplementedError" in body:
                # スタブは「DU-xx」と**この UT を所有する API 名**を skip 理由に宣言すること
                owners = owner_apis.get(ref, set())
                if d["id"] not in decos or not (owners and any(n in decos for n in owners)):
                    bad.append(f"{d['id']}:{ref}:設計リンク不備")
    return bad


# ---- 全層再降下 §3-§4: FR/SR/NFR/AC の粒度ゲート群 ----
try:
    frc_schema = load(J / "fr" / "fr-contract.schema.json")
    acc_schema = load(J / "ac" / "ac-contract.schema.json")
    nfc_schema = load(J / "nfr" / "nfr-contract.schema.json")
    frc = load(J / "fr" / "fr-contracts.json")["items"]
    sr_c = load(J / "strategy" / "sr-contracts.json")["items"]
    acc = load(J / "ac" / "ac-contracts.json")["items"]
    nfc = load(J / "nfr" / "nfr-contracts.json")["items"]
    allc = frc + sr_c

    # G-FRSR-CONTRACT: 全 FR/SR に 18 観点契約（schema 適合＋分母完全被覆）
    c_errs: list[str] = []
    for it in allc:
        c_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(frc_schema, it)]
    fr_md_ids = {i["id"] for i in fr}
    sr_ids = {i["id"] for i in load(J / "strategy" / "sr.json")["items"]}
    cov_ok = {i["id"] for i in frc} == fr_md_ids and {i["id"] for i in sr_c} == sr_ids
    # DDL・遷移正本との突合（Sol major 対応）: tables のテーブル名実在＋loop_runs/tasks の遷移状態実在
    ddl_tables_f = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)",
                                  (J / "s0" / "ddl.sql").read_text(encoding="utf-8")))
    trn_items = load(J / "s0" / "transitions.json")["items"]
    trn_states: dict[str, set] = {}
    for t in trn_items:
        trn_states.setdefault(t["entity"], set()).update({t["from"], t["to"]})
    tbl_faults = detect_contract_table_faults(allc, ddl_tables_f, trn_states)
    gate("G-FRSR-CONTRACT", not c_errs and cov_ok and not tbl_faults,
         f"FR/SR 実行契約: schema 適合＋FR36/SR16 完全被覆＋DDL/遷移正本と突合 "
         f"(err={c_errs[:3]}, cov={cov_ok}, 突合={sorted(set(tbl_faults))[:5]})")

    # G-NFR-MEASURABLE: 全 NFR に計測契約
    n_errs: list[str] = []
    for it in nfc:
        n_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(nfc_schema, it)]
    nfr_ids = {i["id"] for i in nfr}
    nfr_json_ids = {i["id"].replace("NFR-0", "NFR-") for i in nfc} | {i["id"] for i in nfc}
    gate("G-NFR-MEASURABLE", not n_errs and all(i in nfr_json_ids for i in nfr_ids),
         f"NFR 計測契約: schema 適合＋NFR10 完全被覆 (err={n_errs[:3]})")

    # G-AC-COVERAGE: AC 契約 schema 適合・target 実在・S0 契約に AC ≥1・ID 一意
    a_errs: list[str] = []
    for it in acc:
        a_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(acc_schema, it)]
    ac_ids = [a["id"] for a in acc]
    dup_ac = len(ac_ids) != len(set(ac_ids))
    valid_targets = fr_md_ids | sr_ids | nfr_ids | {i["id"] for i in nfc}
    orphan_tgt = [a["id"] for a in acc if a["target"] not in valid_targets]
    ac_by_tgt: dict[str, list] = {}
    for a in acc:
        ac_by_tgt.setdefault(a["target"], []).append(a)
    s0_no_ac = [c["id"] for c in allc if c["slice"] == "S0" and not ac_by_tgt.get(c["id"])]
    gate("G-AC-COVERAGE", not a_errs and not dup_ac and not orphan_tgt and not s0_no_ac,
         f"AC 検証契約: schema 適合＋target 実在＋S0 要件の AC 実在 "
         f"(err={a_errs[:3]}, dup={dup_ac}, orphan={orphan_tgt[:3]}, S0欠落={s0_no_ac})")

    # G-AC-POLARITY: S0 の各 FR/SR は 3 極性（正常/拒否/境界復旧）を AC か理由付き N/A で被覆
    pol_bad = detect_polarity_gaps(allc, acc)
    gate("G-AC-POLARITY", not pol_bad, f"S0 要件の 3 極性被覆（AC or 理由付き N/A） (欠落={pol_bad[:5]})")

    # G-HUMAN-JUDGE: 全契約に人間判断点の明示（なし宣言 or 具体主体）
    hj_bad = [c["id"] for c in allc
              if not (c["human_judgement"].startswith("なし")
                      or any(k in c["human_judgement"] for k in ("PO", "人間", "運用者", "承認")))]
    gate("G-HUMAN-JUDGE", not hj_bad, f"人間判断点の明示（なし宣言 or 主体特定） (不明={hj_bad[:5]})")

    # G-INVARIANT-TRACE: S0 契約の**各**不変条件が invariant_ac_map で固有の負方向 AC に対応づく
    inv_bad = detect_invariant_gaps(allc, acc)
    gate("G-INVARIANT-TRACE", not inv_bad,
         f"S0 の各不変条件に固有の負方向 AC（invariant_ac_map 個別対応） (欠落={inv_bad[:5]})")
except FileNotFoundError as e:
    for gid in ("G-FRSR-CONTRACT", "G-NFR-MEASURABLE", "G-AC-COVERAGE", "G-AC-POLARITY",
                "G-HUMAN-JUDGE", "G-INVARIANT-TRACE"):
        gate(gid, False, f"契約正本が存在しない: {e}")

# G-TRACE-BIDIR: AC ↔ TC 検証契約の双方向接続（全層再降下 §5）
try:
    tcc_schema = load(J / "verification" / "tc-contract.schema.json")
    tcc = load(J / "verification" / "tc-contracts.json")["items"]
    acc2 = load(J / "ac" / "ac-contracts.json")["items"]
    t_errs: list[str] = []
    for it in tcc:
        t_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(tcc_schema, it)]
    acc_ids = {a["id"] for a in acc2}
    tcc_ids = {t["id"] for t in tcc}
    dangling_tc = detect_tc_bidir_faults(tcc, acc2)
    tcc_by_ac: dict[str, set] = {}
    for t in tcc:
        for a in t["ac"]:
            tcc_by_ac.setdefault(a, set()).add(t["id"])
    ac_no_tc = [a["id"] for a in acc2 if not a["tc"]]
    bidir_bad = []
    for a in acc2:
        listed_tcc = {r for r in a["tc"] if r.startswith("TCC-")}
        actual = tcc_by_ac.get(a["id"], set())
        if listed_tcc != actual:
            bidir_bad.append(f"{a['id']}:{sorted(listed_tcc ^ actual)}")
    dangling_ref = [f"{a['id']}→{r}" for a in acc2 for r in a["tc"]
                    if r.startswith("TCC-") and r not in tcc_ids]
    gate("G-TRACE-BIDIR", not t_errs and not dangling_tc and not ac_no_tc and not bidir_bad and not dangling_ref,
         f"AC↔TC 双方向接続 (schema={t_errs[:3]}, TC→AC欠={dangling_tc[:3]}, "
         f"AC無TC={ac_no_tc[:3]}, 非対称={bidir_bad[:3]}, AC→TC欠={dangling_ref[:3]})")
except FileNotFoundError as e:
    gate("G-TRACE-BIDIR", False, f"TC 契約正本が存在しない: {e}")

# G-CMP-INTERFACE: CMP/SCM の 11 観点設計契約＋独立設計書の実在（全層再降下 §6）
try:
    cmpc_schema = load(D / "cmp-contract.schema.json")
    cmpc = load(D / "cmp-contracts.json")["items"]
    m_errs: list[str] = []
    for it in cmpc:
        m_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(cmpc_schema, it)]
    cmp_ids = {i["id"] for i in load(D / "components.json")["items"]}
    scm_ids = {i["id"] for i in load(D / "strategy-components.json")["items"]}
    cmpc_ids = {i["id"] for i in cmpc}
    missing_dd = sorted({dd for it in cmpc for dd in it["trace"].get("design_doc", [])
                         if not (ROOT / "docs" / "design" / dd).exists()})
    gate("G-CMP-INTERFACE",
         not m_errs and cmpc_ids == (cmp_ids | scm_ids) and not missing_dd,
         f"CMP/SCM 設計契約: schema 適合＋23 件完全被覆＋独立設計書実在 "
         f"(err={m_errs[:3]}, 差={sorted(cmpc_ids ^ (cmp_ids | scm_ids))}, 設計書欠={missing_dd})")
except FileNotFoundError as e:
    gate("G-CMP-INTERFACE", False, f"CMP 設計契約が存在しない: {e}")

# ---- 全層再降下 §7-§8: DU 実装契約・UT 接続・空洞設計の禁止 ----
try:
    duc_schema = load(D / "du-contract.schema.json")
    duc = load(D / "du-contracts.json")["items"]
    du_ledger = {i["id"]: i for i in load(D / "detailed.json")["items"]}

    # G-DU-API: schema 適合＋DU 23 完全被覆＋module/cmp が⑤台帳と一致
    d_errs: list[str] = []
    for it in duc:
        d_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(duc_schema, it)]
    duc_ids = {i["id"] for i in duc}
    mod_bad = [it["id"] for it in duc
               if it["id"] in du_ledger and du_ledger[it["id"]]["module"] != it["module"]]
    gate("G-DU-API", not d_errs and duc_ids == set(du_ledger) and not mod_bad,
         f"DU 実装契約: schema 適合＋DU23 被覆＋module 一致 "
         f"(err={d_errs[:3]}, 差={sorted(duc_ids ^ set(du_ledger))}, module={mod_bad})")

    # G-DU-DBC: 全 API に非自明な pre/post（プレースホルダ禁止は G-NO-HOLLOW-DESIGN）
    dbc_bad = [f"{it['id']}:{a['signature'][:30]}" for it in duc for a in it["apis"]
               if not a["precondition"] or not a["postcondition"]]
    gate("G-DU-DBC", not dbc_bad, f"全公開 API に pre/post (欠落={dbc_bad[:3]})")

    # G-DU-ERROR: raises の型がエラー分類正本（error-taxonomy_v0.1.md）に掲載されている
    taxonomy = (ROOT / "docs/design/error-taxonomy_v0.1.md").read_text(encoding="utf-8")
    unknown_err = sorted({r["type"] for it in duc for a in it["apis"] for r in a["raises"]
                          if r["type"].split("（")[0] not in taxonomy})
    gate("G-DU-ERROR", not unknown_err, f"raises 型がエラー分類正本に掲載 (未掲載={unknown_err[:5]})")

    # G-DU-DATA: db_read/db_write が DDL の実在テーブルのみ
    ddl_tables = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)",
                                (J / "s0" / "ddl.sql").read_text(encoding="utf-8")))
    tbl_bad = detect_unknown_tables(duc, ddl_tables)
    gate("G-DU-DATA", not tbl_bad, f"DU の DB read/write が DDL 実在テーブルのみ (未知={tbl_bad[:5]})")

    # G-API-UT: **API 単位**で UT ≥1・参照テスト関数の実在・api.ut⊆trace.ut・宙吊り UT ゼロ・
    #           スタブ（NotImplementedError）は設計リンク（du-contracts DU-xx を含む skip 理由）必須
    ut_faults = detect_api_ut_faults(duc, ROOT / "tests" / "unit")
    gate("G-API-UT", not ut_faults,
         "全 DU の API 単位 UT 割当・参照実在・設計リンク（実行検証は S0.1 で red→green） "
         f"(欠陥={ut_faults[:5]})")

    # G-NO-HOLLOW-DESIGN: 全契約正本にプレースホルダ・空洞文字列がない
    HOLLOW = re.compile(r"TBD|TODO|FIXME|後で書く|後で埋め|後述予定|要検討|仮置き|placeholder|XXX")
    hollow_hits: list[str] = []
    for p in (J / "br" / "br-contracts.json", J / "fr" / "fr-contracts.json",
              J / "strategy" / "sr-contracts.json", J / "ac" / "ac-contracts.json",
              J / "nfr" / "nfr-contracts.json", J / "verification" / "tc-contracts.json",
              D / "cmp-contracts.json", D / "du-contracts.json"):
        txt = p.read_text(encoding="utf-8")
        for m in HOLLOW.finditer(txt):
            hollow_hits.append(f"{p.name}:{m.group(0)}")
    gate("G-NO-HOLLOW-DESIGN", not hollow_hits,
         f"契約正本にプレースホルダなし (検出={sorted(set(hollow_hits))[:5]})")
except FileNotFoundError as e:
    for gid in ("G-DU-API", "G-DU-DBC", "G-DU-ERROR", "G-DU-DATA", "G-API-UT", "G-NO-HOLLOW-DESIGN"):
        gate(gid, False, f"DU 契約正本が存在しない: {e}")

# ---- クロージャー §5: 意味整合（構造化参照 ↔ 正本）----
def load_canon() -> dict:
    """意味検査の正本語彙（DDL・遷移表・evidence kind・エラー分類・API）を読む。"""
    ddl_txt = (J / "s0" / "ddl.sql").read_text(encoding="utf-8")
    tbl: dict[str, set] = {}
    for m in re.finditer(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)\s*\((.*?)\n\);", ddl_txt, re.S):
        tbl[m.group(1)] = set(re.findall(r"^\s{2}(\w+)\s+[A-Z]", m.group(2), re.M))
    trn_c = load(J / "s0" / "transitions.json")["items"]
    st: dict[str, set] = {}
    ev = set()
    for t in trn_c:
        st.setdefault(t["entity"], set()).update({t["from"], t["to"]})
        ev.add(t["event"])
    kinds = {k["kind"] for k in load(J / "s0" / "evidence-kinds.json")["items"]}
    tax = (ROOT / "docs/design/error-taxonomy_v0.1.md").read_text(encoding="utf-8")
    errs = set(re.findall(
        r"[A-Z][A-Za-z]{3,}(?:Error|Rejected|Denied|Missing|Mismatch|Detected|Incomplete|"
        r"Immutable|Violation|Required|Exhausted)", tax))
    du_c = load(D / "du-contracts.json")["items"]
    apis = {m.group(1) for d_ in du_c for a in d_["apis"]
            if (m := re.match(r"def (\w+)", a["signature"]))}
    return {"tables": tbl, "states": st, "events": ev, "kinds": kinds, "errors": errs, "apis": apis}


def detect_semantic_ref_faults(items, canon) -> list[str]:
    """構造化参照が正本語彙に実在しない箇所を列挙する（G-SEMANTIC-REF／G-COLUMN-REF の本体）。"""
    bad: list[str] = []
    for it in items:
        r = it.get("semantic_refs")
        if r is None:
            bad.append(f"{it.get('id', '?')}:semantic_refs なし")
            continue
        for t in r["table_refs"]:
            if t not in canon["tables"]:
                bad.append(f"{it['id']}:table {t}")
        for c in r["column_refs"]:
            t, col = c.split(".", 1)
            if t not in canon["tables"] or col not in canon["tables"][t]:
                bad.append(f"{it['id']}:column {c}")
        for s in r["state_refs"]:
            e, name = s.split(".", 1)
            if e not in canon["states"] or name not in canon["states"][e]:
                bad.append(f"{it['id']}:state {s}")
        for e in r["event_refs"]:
            if e not in canon["events"]:
                bad.append(f"{it['id']}:event {e}")
        for k in r["evidence_kind_refs"]:
            if k not in canon["kinds"]:
                bad.append(f"{it['id']}:kind {k}")
        for x in r["error_type_refs"]:
            if x not in canon["errors"]:
                bad.append(f"{it['id']}:error {x}")
        for a in r["api_refs"]:
            if a not in canon["apis"]:
                bad.append(f"{it['id']}:api {a}")
    return bad


# operation_log（evidence kind）を証跡にできるのは外部操作・業務操作を伴うドメインのみ。
# 判定は「構造化参照が外部操作系テーブルに触れる」か「対象が外部操作を担う要件（コネクタ・制作・計測）」。
EXTERNAL_TABLES = {"external_operations", "playbooks", "approvals", "assets", "measurements", "spend_ledger"}
EXTERNAL_TARGET = re.compile(r"^(FR-4\d|FR-5\d|FR-6\d)$")


def _external_domain(refs: dict, target: str, text: str) -> bool:
    return (bool(set(refs.get("table_refs", [])) & EXTERNAL_TABLES)
            or bool(EXTERNAL_TARGET.match(target or ""))
            or "外部操作" in text)


def detect_state_evidence_faults(acs, tcs) -> list[str]:
    """状態遷移・ゲート拒否の証跡を operation_log（外部操作証跡）で表現している箇所を列挙する。

    正: 状態遷移の拒否・成立は state_transitions、内部ゲート拒否は構造化ログ、
        operation_log kind は外部操作・業務操作の証跡に限定（クロージャー §5）。
    """
    bad: list[str] = []
    ac_by_id = {a["id"]: a for a in acs}
    for a in acs:
        r = a.get("semantic_refs", {})
        ev_txt = a.get("expected_evidence", "")
        if "operation_log" not in ev_txt:
            continue
        if not _external_domain(r, a.get("target", ""), ev_txt):
            bad.append(f"{a['id']}:内部遷移・ゲート拒否を operation_log で表現")
    for t in tcs:
        r = t.get("semantic_refs", {})
        ev_txt = t.get("verifies_evidence", "")
        if "operation_log" not in ev_txt:
            continue
        tgt = next((ac_by_id[x]["target"] for x in t.get("ac", []) if x in ac_by_id), "")
        if not _external_domain(r, tgt, ev_txt):
            bad.append(f"{t['id']}:内部遷移・ゲート拒否を operation_log で表現")
    return bad


try:
    canon = load_canon()
    sem_items = frc + sr_c + acc + tcc + cmpc + duc
    sem_bad = detect_semantic_ref_faults(sem_items, canon)
    col_bad = [b for b in sem_bad if ":column " in b or ":table " in b]
    gate("G-SEMANTIC-REF", not sem_bad,
         f"構造化参照が正本語彙に実在（table/column/state/event/kind/error/api） (不正={sem_bad[:5]})")
    gate("G-COLUMN-REF", not col_bad,
         f"table/column 参照が ddl.sql に実在 (不正={col_bad[:5]})")
    se_bad = detect_state_evidence_faults(acc, tcc)
    gate("G-STATE-EVIDENCE-CONSISTENCY", not se_bad,
         "状態遷移の拒否・成立は state_transitions／構造化ログで表現し operation_log は外部操作に限定 "
         f"(違反={se_bad[:5]})")
except (FileNotFoundError, KeyError) as e:
    for gid in ("G-SEMANTIC-REF", "G-COLUMN-REF", "G-STATE-EVIDENCE-CONSISTENCY"):
        gate(gid, False, f"意味整合の正本が読めない: {e}")

# ---- クロージャー §2-§3・§7: 正本確定・旧正本の除外・test-first の実体化 ----
try:
    CANON_FILES = [J / "br/br-contracts.json", J / "fr/fr-contracts.json",
                   J / "strategy/sr-contracts.json", J / "nfr/nfr-contracts.json",
                   J / "ac/ac-contracts.json", J / "verification/tc-contracts.json",
                   D / "cmp-contracts.json", D / "du-contracts.json"]
    appr_txt = (ROOT / "docs/governance/approvals.md").read_text(encoding="utf-8")
    canon_bad: list[str] = []
    for p in CANON_FILES:
        d_ = load(p)
        if d_.get("status") != "confirmed":
            canon_bad.append(f"{p.name}:status={d_.get('status')}")
            continue
        for k in ("approved_at", "approval_digest", "authority"):
            if not d_.get(k):
                canon_bad.append(f"{p.name}:{k} 欠落")
        # 内容 digest が承認 receipt と一致（内容に束縛されない空承認の禁止）
        body = json.dumps({k: v for k, v in d_.items() if k != "approval_digest"},
                          ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        want = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
        if d_.get("approval_digest") != want:
            canon_bad.append(f"{p.name}:digest 不一致({d_.get('approval_digest')}!={want})")
        elif f"| {p.name} | v0.1 | confirmed | PO | {want} |" not in appr_txt:
            canon_bad.append(f"{p.name}:approvals 行なし")
    gate("G-CANON-CONFIRMED", not canon_bad,
         f"契約 JSON 正本 8 本が confirmed＋内容束縛 receipt (欠陥={canon_bad[:4]})")

    LEGACY = {J / "ac.json": "ac-contracts.json", J / "verification.json": "tc-contracts.json",
              D / "utest.json": "du-contracts.json"}
    legacy_bad = [f"{p.name}:{load(p).get('status')}" for p in LEGACY
                  if load(p).get("status") not in ("superseded", "historical")]
    gate("G-LEGACY-SUPERSEDED", not legacy_bad,
         f"旧正本（ac/verification/utest）が superseded で実装入力から除外 (未処理={legacy_bad})")

    # G-S0-TEST-REALITY: S0.1 対象 API の UT が skip のままなら CI を落とす（test-first の実体化）
    S0_IMPL_STARTED = bool(load(ROOT / "tests" / "skip-budget.json").get("s0_impl_started"))
    s0_dus = [x for x in duc if int(x["id"][3:]) <= 12]
    s0_skipped: list[str] = []
    for x in s0_dus:
        for a in x["apis"]:
            for ref in a.get("ut", []):
                fname, tname = ref.split("::", 1)
                fp = ROOT / "tests" / "unit" / fname
                if not fp.exists():
                    continue
                txt = fp.read_text(encoding="utf-8")
                m = re.search(rf"\ndef {re.escape(tname)}\b", txt)
                if m is None:
                    continue
                head = txt[:m.start()]
                if "skip" in head[head.rfind("\n\n"):] and S0_IMPL_STARTED:
                    s0_skipped.append(f"{x['id']}:{ref}")
    gate("G-S0-TEST-REALITY",
         not s0_skipped,
         "S0.1 実装開始後は対象 API の UT を skip のままにできない（実 red→green を要求。"
         f"開始前は tests/skip-budget.json の s0_impl_started=false で猶予） (skip 残={s0_skipped[:5]})")
except (FileNotFoundError, KeyError) as e:
    for gid in ("G-CANON-CONFIRMED", "G-LEGACY-SUPERSEDED", "G-S0-TEST-REALITY"):
        gate(gid, False, f"正本が読めない: {e}")

# G-REVIEW-BINDING: レビュー成果物が対象コミットと成果物 digest に束縛される（クロージャー §8）
try:
    rev_dir = ROOT / "docs/governance/reviews"
    rev_schema = load(rev_dir / "review.schema.json")
    revs = sorted(p for p in rev_dir.glob("*.json") if p.name != "review.schema.json")
    rev_bad: list[str] = []
    if not revs:
        rev_bad.append("レビュー成果物が 1 件もない（Go をコミットメッセージだけで記録しない）")
    for p in revs:
        r = load(p)
        rev_bad += [f"{p.name}: {e}" for e in schema_check(rev_schema, r)]
        if r.get("verdict") != "Go":
            continue
        # Go のレビューは、対象コミットが実在し、成果物が「レビュー後に変わっていない」ことを要する
        ok = subprocess.run(  # noqa: S603
            ["git", "cat-file", "-e", f"{r['target_commit']}^{{commit}}"],  # noqa: S607
            capture_output=True, text=True, check=False, cwd=ROOT).returncode == 0
        if not ok:
            rev_bad.append(f"{p.name}: target_commit がリポジトリに存在しない")
            continue
        for art, dg in r["reviewed_artifact_digests"].items():
            fp = ROOT / art
            if not fp.exists():
                rev_bad.append(f"{p.name}: {art} 不在")
                continue
            now = hashlib.sha256(fp.read_bytes()).hexdigest()[:16]
            if now != dg:
                # レビュー後の変更は、その差分を解決した後続レビュー（より新しい Go）がない限り違反
                newer = [load(q) for q in revs if load(q).get("verdict") == "Go"
                         and load(q).get("completed_at", "") > r.get("completed_at", "")]
                if not any(now == n.get("reviewed_artifact_digests", {}).get(art) for n in newer):
                    rev_bad.append(f"{p.name}: {art} がレビュー後に改変（{dg}→{now}）")
    gate("G-REVIEW-BINDING", not rev_bad,
         f"レビュー成果物が対象コミット・成果物 digest に束縛 (欠陥={rev_bad[:4]})")
except FileNotFoundError as e:
    gate("G-REVIEW-BINDING", False, f"レビュー成果物の枠組みがない: {e}")

# G-DESIGN-SUBSTANCE: 独立設計書・機能別設計の実体（行数＋trace 表＋章立て）— 参照実在だけの穴を塞ぐ
try:
    thin_docs: list[str] = []
    design_docs = [ROOT / "docs/design" / n for n in (
        "external-if-design_v0.1.md", "db-design_v0.1.md", "state-machine-design_v0.1.md",
        "approval-design_v0.1.md", "brand-isolation-design_v0.1.md", "error-taxonomy_v0.1.md")]
    feature_docs = list((ROOT / "docs/design/features").glob("*.md"))
    if len(feature_docs) < 11:
        thin_docs.append(f"features 不足:{len(feature_docs)}<11")
    for p in design_docs + feature_docs:
        txt = p.read_text(encoding="utf-8")
        lines = txt.count("\n")
        if lines < 50 or txt.count("## ") < 3:
            thin_docs.append(f"{p.name}:{lines}行/{txt.count('## ')}節")
        if p in feature_docs and "trace" not in txt.lower():
            thin_docs.append(f"{p.name}:trace表なし")
    gate("G-DESIGN-SUBSTANCE", not thin_docs, f"設計書の実体（≥50 行・≥3 節・trace） (薄い={thin_docs[:5]})")
except FileNotFoundError as e:
    gate("G-DESIGN-SUBSTANCE", False, f"設計書が存在しない: {e}")

# G-CHAIN-BIDIR: BR→REQ→FR/SR→AC→CMP→DU→API→UT の隣接エッジを双方向で突合（全層再降下 完了条件 4）
#   検出ロジックは detect_chain_asymmetry() に一元化し、G-DESCENT-SELFTEST が**同じ関数**へ変異データを
#   投入して検出能力を証明する（本体だけ変更されて自己検査が取り残される drift を防ぐ）。
def detect_chain_asymmetry(brc_, req_, allc_, acc_, cmpc_, duc_, tcc_=None) -> list[str]:
    """BR→REQ→FR/SR→AC→TC→CMP→DU→API→UT の全区間で非対称エッジを列挙する（空 = 双方向成立）。"""
    bad: list[str] = []
    up = {r["id"]: set(r["trace"]["upstream"]) for r in req_}
    down = {r["id"]: set(r["trace"]["downstream"]) | set(r.get("related", [])) for r in req_}
    # (1) BR 契約 ↔ REQ.upstream（双方向）
    for it in brc_:
        for r in it["trace_down"]["req"]:
            if it["id"] not in up.get(r, set()):
                bad.append(f"BR→REQ:{it['id']}→{r}")
    br_edges = {(b["id"], r) for b in brc_ for r in b["trace_down"]["req"]}
    for r in req_:
        for b in r["trace"]["upstream"]:
            if re.fullmatch(r"BR-[A-Z]\d", b) and (b, r["id"]) not in br_edges:
                bad.append(f"REQ→BR:{r['id']}→{b}")
    # (2) REQ ↔ FR/SR 契約（双方向）
    frsr_up_ = {c["id"]: {t for t in c["trace_up"] if t.startswith("REQ-")} for c in allc_}
    for r in req_:
        for f in down[r["id"]]:
            if f in frsr_up_ and r["id"] not in frsr_up_[f]:
                bad.append(f"REQ→FRSR:{r['id']}→{f}")
    for c in allc_:
        for r in frsr_up_[c["id"]]:
            if c["id"] not in down.get(r, set()):
                bad.append(f"FRSR→REQ:{c['id']}→{r}")
    # (3) FR/SR.trace_down.ac == {AC | AC.target == id}（厳密等号）
    ac_by_t: dict[str, set] = {}
    for a in acc_:
        ac_by_t.setdefault(a["target"], set()).add(a["id"])
    for c in allc_:
        if set(c["trace_down"]["ac"]) != ac_by_t.get(c["id"], set()):
            bad.append(f"FRSR↔AC:{c['id']}")
    # (4) CMP ↔ DU（**厳密等号** — DU は cmp＋also_implements の両方で自分の所属を宣言する）
    cmp_du_ = {c["id"]: set(c["trace"]["du"]) for c in cmpc_}
    du_cmp_: dict[str, set] = {}
    for d_ in duc_:
        for cid in [d_["cmp"], *d_.get("also_implements", [])]:
            du_cmp_.setdefault(cid, set()).add(d_["id"])
    for cid in set(cmp_du_) | set(du_cmp_):
        if cmp_du_.get(cid, set()) != du_cmp_.get(cid, set()):
            diff = sorted(cmp_du_.get(cid, set()) ^ du_cmp_.get(cid, set()))
            bad.append(f"CMP↔DU:{cid}:{diff}")
    # (5) FR/SR → CMP: 参照先 CMP が実在し、FR の FN を当該 CMP が被覆する
    cmp_by_id = {c["id"]: c for c in cmpc_}
    for c in allc_:
        if not c["trace_down"].get("cmp"):
            bad.append(f"FRSR→CMP:{c['id']}:CMP未接続")
        for cid in c["trace_down"].get("cmp", []):
            if cid not in cmp_by_id:
                bad.append(f"FRSR→CMP:{c['id']}→{cid}:不在")
            else:
                fns = set(c["trace_down"].get("fn", []))
                if fns and not fns <= set(cmp_by_id[cid]["trace"]["fn"]):
                    bad.append(f"FRSR→CMP:{c['id']}→{cid}:FN未被覆{sorted(fns - set(cmp_by_id[cid]['trace']['fn']))}")
    # (6) AC → TC → DU: TC 参照の実在と、S0 TC の DU 割当（TC↔CMP/DU 区間の到達性）
    if tcc_ is not None:
        tc_ids = {t["id"] for t in tcc_}
        du_tcs = {t for d_ in duc_ for t in d_["trace"]["tc"]}
        for d_ in duc_:
            for t in d_["trace"]["tc"]:
                if t.startswith("TCC-") and t not in tc_ids:
                    bad.append(f"DU→TC:{d_['id']}→{t}:不在")
        s0_t = {c["id"] for c in allc_ if c["slice"] == "S0"}
        s0_ac = {a["id"] for a in acc_ if a["target"] in s0_t}
        for t in tcc_:
            if t["slice"] == "S0" and set(t["ac"]) & s0_ac and t["id"] not in du_tcs:
                bad.append(f"TC→DU:{t['id']}:未割当")
    # (7) DU → API → UT: DU.trace.ut が API 側 ut の合併と一致（鎖の末端）
    for d_ in duc_:
        api_ut = {u for a in d_["apis"] for u in a.get("ut", [])}
        if api_ut != set(d_["trace"]["ut"]):
            bad.append(f"DU↔API-UT:{d_['id']}:{sorted(api_ut ^ set(d_['trace']['ut']))[:2]}")
    return bad


def detect_orphan_s0_ac(allc_, acc_, duc_) -> list[str]:
    """S0 対象でどの DU にも割当てられていない AC を列挙する（空 = 鎖の起点が全て存在）。"""
    du_acs_ = {a for d_ in duc_ for a in d_["trace"]["ac"]}
    s0_t = {c["id"] for c in allc_ if c["slice"] == "S0"}
    return sorted(a["id"] for a in acc_ if a["target"] in s0_t and a["id"] not in du_acs_)


try:
    chain_bad = detect_chain_asymmetry(brc, req, allc, acc, cmpc, duc, tcc)
    orphan_ac = detect_orphan_s0_ac(allc, acc, duc)
    gate("G-CHAIN-BIDIR", not chain_bad and not orphan_ac,
         f"全層 trace の双方向突合 (非対称={sorted(set(chain_bad))[:6]}, DU未割当S0AC={orphan_ac[:5]})")
except (FileNotFoundError, NameError) as e:
    gate("G-CHAIN-BIDIR", False, f"trace 正本が読めない: {e}")

# G-DESCENT-SELFTEST: 再降下ゲート群の mutation 自己検査。
#   各ケースは**本番ゲートが使う検出関数そのもの**へ変異データを投入する（ロジックの再記述をしない）。
#   本体の検出関数を弱めれば自己検査も同時に落ちるため、drift が構造的に起きない。
try:
    st_ok, st_msg = True, []
    # (a) 極性: S0 の victim から reject AC を全削除 → detect_polarity_gaps が検出するか
    victim = next(c for c in allc if c["slice"] == "S0"
                  and any(a["target"] == c["id"] and a["polarity"] == "reject" for a in acc))
    mut_acc = [a for a in acc if not (a["target"] == victim["id"] and a["polarity"] == "reject")]
    if not detect_polarity_gaps([victim], mut_acc):
        st_ok, _ = False, st_msg.append("polarity-mutation 未検出")
    # (b) DbC: precondition を空にした API → schema_check（本体と同じ）が検出するか
    mut_api = {**duc[0]["apis"][0], "precondition": []}
    if not schema_check(duc_schema["properties"]["apis"]["items"], mut_api):
        st_ok, _ = False, st_msg.append("dbc-mutation 未検出")
    # (c) DATA: 幽霊テーブルを注入 → detect_unknown_tables が検出するか
    mut_du = {**duc[0], "db_read": [*duc[0]["db_read"], "ghost_table_xyz"]}
    if "ghost_table_xyz" not in " ".join(detect_unknown_tables([mut_du], ddl_tables)):
        st_ok, _ = False, st_msg.append("data-mutation 未検出")
    # (d) AC↔TC: 偽 AC 参照の TC → detect_tc_bidir_faults が検出するか
    mut_tc = {**tcc[0], "ac": ["AC-99-9"]}
    if not detect_tc_bidir_faults([mut_tc], acc):
        st_ok, _ = False, st_msg.append("bidir-mutation 未検出")
    # (e) 全層 chain: BR→REQ 片方向参照を注入 → detect_chain_asymmetry が検出するか
    mut_br = [{**brc[0], "trace_down": {**brc[0]["trace_down"],
                                        "req": [*brc[0]["trace_down"]["req"], "REQ-052"]}}, *brc[1:]]
    if not detect_chain_asymmetry(mut_br, req, allc, acc, cmpc, duc, tcc):
        st_ok, _ = False, st_msg.append("chain-mutation 未検出")
    # (f) 全層 chain: CMP↔DU を片方向化（DU の also_implements を剥がす）→ 等号検査が検出するか
    mut_duc = [{k: v for k, v in d_.items() if k != "also_implements"} for d_ in duc]
    if not detect_chain_asymmetry(brc, req, allc, acc, cmpc, mut_duc, tcc):
        st_ok, _ = False, st_msg.append("cmp-du-mutation 未検出")
    # (g) invariant 個別対応: 対応表の 1 行を normal AC のみへ差し替え → 検出するか
    inv_victim = next((c for c in allc if c["slice"] == "S0" and c.get("invariant_ac_map")), None)
    if inv_victim is not None:
        normal_ac = next((a["id"] for a in acc
                          if a["target"] == inv_victim["id"] and a["polarity"] == "normal"), None)
        if normal_ac:
            mut_c = {**inv_victim,
                     "invariant_ac_map": [[normal_ac], *inv_victim["invariant_ac_map"][1:]]}
            if not detect_invariant_gaps([mut_c], acc):
                st_ok, _ = False, st_msg.append("invariant-mutation 未検出")
    # (h) API↔UT: API の ut を空にする → detect_api_ut_faults が検出するか
    mut_du2 = {**duc[0], "apis": [{**duc[0]["apis"][0], "ut": []}, *duc[0]["apis"][1:]]}
    if not detect_api_ut_faults([mut_du2], ROOT / "tests" / "unit"):
        st_ok, _ = False, st_msg.append("api-ut-mutation 未検出")
    gate("G-DESCENT-SELFTEST", st_ok, f"再降下ゲートの mutation 自己検査 (失敗={st_msg})")
except (NameError, FileNotFoundError, IndexError, StopIteration) as e:
    gate("G-DESCENT-SELFTEST", False, f"自己検査を実行できない: {e}")

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
