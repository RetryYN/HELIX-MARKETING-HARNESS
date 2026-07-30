# 単体テスト設計書 v0.1（⑥）

> status: **confirmed**（2026-07-31 PO 承認 — 詳細設計完遂指示。AI 起草）
> pair: [detailed-design_v0.1.md](detailed-design_v0.1.md)（詳細設計⑤ — HELIX 式 ⑤↔⑥ 文書ペア）
> 対象文書: detailed-design_v0.1.md の DU-01〜DU-23 全モジュール。
> 上位文書: [verification-design_v0.1.md](../requirements/verification-design_v0.1.md)（③ — TC 59 の正本。
> 本書は TC を再定義せず、**各 TC を実装先 DU へ割当てる**）
> JSON 正本: [json/utest.json](json/utest.json)（割当＋補完 UT の台帳。実装入力は JSON）

---

## 1. 位置づけと合否基準

- 本書は ③の TC 59 を **どの DU の単体テストとして pytest 化するか**を 1 対 1 で確定し、
  TC が届かない DU には補完単体テスト **UT-01〜08** を定義する。これにより
  **全 59 TC が重複なくいずれかの DU に割当てられ、全 23 DU が 1 件以上のテストを持つ**
  （ゲート G-UTC-TC / G-UTC-DU / G-UTC-FILE が機械検証）。
- TDD 運用（CLAUDE.md）: 実装は割当テストを pytest 化して赤を確認してから行う。
  テストファイルは `tests/unit/test_<パッケージ>_<モジュール>.py`（例: kernel/state.py →
  `test_kernel_state.py`。DU と 1 対 1・衝突なし — G-UTC-FILE が検査）。
- 単体の粒度: DU の公開 API を、他 DU を test double に置換して検証する。
  ③で kind=integration/e2e の TC も、**単体層では対象 DU の API 境界の検証として実装し**、
  結合実体での再検証は ④ITC が担う（③↔④↔⑥で二重実装しない）。

## 2. TC → DU 割当（59 件）

| DU | モジュール | 割当 TC |
|---|---|---|
| DU-01 | kernel/state.py | TC-011, TC-GATE-05, TC-RST-06, TC-028 |
| DU-02 | kernel/orchestrator.py | TC-012, TC-013, TC-027, TC-RST-01, TC-RST-02, TC-RST-03, TC-RST-04, TC-RST-05 |
| DU-03 | kernel/assigner.py | TC-GATE-02 |
| DU-06 | gates/publish.py | TC-021, TC-GATE-01 |
| DU-07 | gates/zero_ad.py | TC-GATE-04 |
| DU-08 | gates/evidence_check.py | TC-GATE-03 |
| DU-09 | evidence/store.py | TC-EVD-01〜10 の A/R 20 件, TC-SCH-05 |
| DU-10 | db/connect.py | TC-SCH-02 |
| DU-11 | db/migrate.py | TC-071, TC-072, TC-SCH-01, TC-SCH-03 |
| DU-12 | config/store.py | TC-033, TC-SCH-04 |
| DU-13 | registry/resolver.py | TC-041 |
| DU-14 | registry/secrets.py | TC-047 |
| DU-16 | connectors/playbooks.py | TC-042 |
| DU-17 | connectors/wp.py | TC-044-R, TC-044-A, TC-GATE-07 |
| DU-18 | connectors/approval.py | TC-046, TC-GATE-06 |
| DU-19 | content/generate.py | TC-051, TC-NFR-02 |
| DU-20 | content/versioning.py | TC-054 |
| DU-21 | measure/kpi.py | TC-023 |
| DU-23 | measure/parse.py | TC-061, TC-062 |

補足:

- 結合系 TC（TC-044-A、TC-RST-03/05 等）は、単体層では該当 DU の API 境界検証（wp は `_client` を
  mock、approval は transport mock、orchestrator は operation_log fixture）として実装し、
  実環境での通し検証は ④ITC-09/06/10 が担う。
- 「DB 制約とエンジン双方」を要求する TC（TC-027・TC-023・TC-028）は、DB 側に実際に INSERT を試みる
  API（issue_task／create_node）と遷移 API（transition）の所有 DU へ割当てた。
- TC-047 は DU-14 の `scan` API（repo・SQLite・ログの平文走査）の単体テストとして成立させる。
- TC-041/042 は検証設計正本で S0.3 のため S0.3 で実行する。DU-13/16 の実装は S0.2 なので、
  S0.2 完了時の単体保証は補完 UT-07/08 が担う（更新境界の空白を作らない）。

## 3. 補完単体テスト（UT-01〜08 — TC が届かない DU と更新境界の空白）

| ID | DU | 極性 | 内容 |
|---|---|---|---|
| UT-01 | DU-04 kernel/workflow.py | reject 含む | definition_json / required_evidence_json の schema 検証（壊れた定義は FatalError）、ステップ順実行、ステップ失敗が 3 系例外に正規化され勝手に done へ進まない |
| UT-02 | DU-05 gates/pair.py | reject 含む | hash 一致時のみ pair 成立・PairPass 生成が本モジュール限定、企画/commit 変更で revoked、passed なしの require_pair が GateRejected、同一 (plan, evidence) の重複成立拒否 |
| UT-03 | DU-15 connectors/browser.py | mixed | storage_state 保存→再利用（再ログイン不要）、headed/headless 両起動、起動失敗の RetryableError 正規化、screenshot の URL 到達検証 |
| UT-04 | DU-21 measure/kpi.py | reject 含む | 階層・集計式検証つき登録、metric_type が必ず zero_ad ゲートを通過（deny 型は GateRejected）、親子ツリー解決 |
| UT-05 | DU-22 measure/fetch.py | reject 含む | 解決経路（api 第一）での取得、**api 阻害時の browser フォールバック切替**、取得物の即時 SHA-256 固定＋証跡化、書込み系 operation の組立時拒否（read-only 保証） |
| UT-06 | DU-03 kernel/assigner.py | reject 含む | active な別 agent 組の割当、同一 agent のみの場合の GateRejected、T-REVIEW の critic 除外 |
| UT-07 | DU-13 registry/resolver.py | reject 含む | 優先順（mcp→api→browser→有償）の解決、無効経路スキップ、該当なし FatalError（S0.2 の基本保証） |
| UT-08 | DU-16 connectors/playbooks.py | reject 含む | 保存・参照・last_success_at 更新・連続失敗の broken 降格・ストア副層外からの生 SQL 不在（S0.2 の基本保証） |

## 4. test double・fixture 規約

| 部品 | 用途 |
|---|---|
| tmp_db（③/④と共通） | migration 適用済み一時 SQLite。単体でも実 DB を使う（SQLite は十分軽量、CHECK/FK の二重防御を実検証するため） |
| FakeClock / FixedRng | Clock/Rng 注入点の決定的置換 |
| transport/client mock | approval transport・WP `_client`・GA4 応答の成功/失敗/timeout/重複 |
| secrets fixture | テスト scope の Fernet ストア＋偽 endpoint 対（不正組合せ検証用） |

方針: DU 内部を patch しない（公開 API 経由のみ）。他 DU 依存は原則 mock だが、
DB・DDL の CHECK 制約だけは常に実物を使う（fail-close の二重防御そのものが検証対象のため）。

## 5. デグレ対策

- 本台帳は分母ラチェット対象（DU 23・UTC 67 = TC 割当 59＋UT 8）。縮小・割当解除は
  G-UTC-*／G-BASE-RATCHET が CI と pre-commit hook で fail-close。
- ③の TC を変更した場合、本書の割当は G-UTC-TC（59 件全割当・重複なし）が自動で破れを検出する。
- 実装開始後は utest.json の test_file の存在を DU ごとに検査するペアゲートを CI に追加し、
  テストのない DU・テストだけ消す退行を検出する（S0.1 着手時に配線 — CLAUDE.md）。
- 各 S0 更新の完了条件に「前更新の単体テスト全 green（回帰）」を含める（②⑤の完了定義と同一）。
