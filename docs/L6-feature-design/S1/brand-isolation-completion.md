---
artifact_id: L6-S1-BRAND-ISOLATION-COMPLETION
lifecycle_status: planned
slice: S1
traces: [FR-34]
forward_refs: []
dus: [DU-14, DU-15, DU-18, DU-21]
---

# 機能設計: ブランド隔離 S1 完成（強制実装・複数ブランド・越境 negative test）

> status: **planned**（2026-08-01 構造分類是正で S0 基盤文書から分離。S1 実装の設計正本）
> 上位設計: [brand-isolation-design_v0.1.md](../../L4-basic-design/canonical/brand-isolation/brand-isolation-design_v0.1.md)（隔離の設計正本 — 隔離単位・帰属方式・分離資源の一覧は同書 §1〜§3。本書は再掲しない）
> 対スライス文書: [brand-isolation-foundation.md](../S0/brand-isolation-foundation.md)（S0 = schema 共存・単一ブランド運転。型定義・例外契約は同書が正本で本書は再掲しない）
> 位置づけ: S0 基盤の上に、FR-34 の**強制**（全ストア API のスコープ必須化・親チェーン検査・
> 越境 negative test・複数ブランド解禁）を積む実装計画。S0 で成立済みの型・例外は再定義しない。

---

## §0 位置づけ・動機

S0 は schema 共存と単一ブランド運転までであり、越境は「起こしても止まらない」状態にある。
本書は FR-34 の postcondition（越境の拒否と拒否の証跡化）を満たすところまでを実装単位へ降下させる。

## §1 ストア API シグネチャ規約（全 API 必須化）

| 規約 | 内容 |
|---|---|
| 第一級引数 | スコープ対象テーブル（上位設計 §1 の直接／導出帰属の全テーブル）を扱う全ストア関数は `scope: ScopeContext` を必須第一引数とする |
| WHERE 焼き込み | 読取は `WHERE business_profile_id = :scope_id`（直接列）又は集約ルート JOIN（導出）で内部絞込み。呼出側 WHERE 句への依存を禁止 |
| INSERT 焼き込み | 直接スコープ列を持つテーブルは scope から列値を焼き込む。呼出側が business_profile_id を渡す引数を設けない |
| 行 id 直指定 | id 指定の単行取得も帰属検証を通し、他 profile の行は「不在」ではなく `CrossProfileAccessDenied` を raise（存在秘匿より拒否証跡を優先 — AC-34-2） |
| 非帰属テーブル | agents・workflows・config 等（上位設計 §1 の共有基盤）はスコープ引数を取らない。config は `<profile_key>.` キー接頭の名前空間化 |

## §2 親チェーン検査の実装

導出スコープテーブル（sprints／loop_runs／tasks／evidence 等 — 一覧は上位設計 §1）への書込みは、
同一 transaction 内で親行の帰属を確認してから INSERT する。

1. 検査 SQL は「親 FK を集約ルートまで JOIN し business_profile_id を取り出す」再帰しない固定
   チェーン（最長: evidence → tasks → loop_runs → sprints → action_plans）。各ストア関数が
   自テーブル専用の検査クエリを持つ（動的 SQL 生成をしない — 検査経路の監査可能性）。
2. 取り出した profile と `scope.business_profile_id` の不一致は INSERT せず
   `CrossProfileAccessDenied`（1 遷移 1 transaction の原則内 — 検査と INSERT は同一 transaction）。
3. FK 不一致の混入防御は二重: 書込み時検査（本節）＋ DU-11 `verify()` の整合性クエリ
   （既存全行の不一致 0 件 — 上位設計 §4-3）。verify は read-only であり修復しない（検出 → escalate）。

## §3 越境 negative test 6 項目の実装方針

上位設計 §4 の 6 項目を pytest 実装へ対応付ける（本スライスで必須 green。テストファイルは⑥の規約
`tests/unit/test_scope.py`／結合系は `tests/integration/` — ⑥改訂時に正式割当）。

| # | テスト | 実装方針 |
|---|---|---|
| 1 | 越境読取 0 件 | in-memory SQLite に profile A/B を seed し、A スコープの一覧 API が B の行を含まないこと＋B の行 id 直指定が `CrossProfileAccessDenied` を raise することを assert |
| 2 | 越境書込み拒否 | A スコープで B の action_plan 配下へ sprint/task INSERT → 例外・`SELECT COUNT` 前後不変・構造化ログに拒否行（profile 組・API 名）の 3 点 assert |
| 3 | FK 不一致検出 | ストア層を迂回した生 SQL で不一致行を故意に作り、`verify()` が検出すること／ストア層経由の同 INSERT は書込み時検査で拒否されることの両面 |
| 4 | 認証・セッション越境 | mock 秘匿ストアで A スコープから B の credential 名・storage_state パスを要求 → 取得不能（fail-close）。実 credential 不使用（環境契約 §6） |
| 5 | brief 越境運転拒否 | B の brief id/digest を A の lower run start に与え、brief ガード（DU-01）が拒否し `state_transitions` に guard_result = rejected が残ることを assert |
| 6 | スコープ未指定 deny-by-default | 型面 = ストア公開 API 全関数の第一引数が ScopeContext であることの inspect 検査（ペアゲートと同型の機械検査）。実行時面 = None・素の int を渡した呼出しが即例外 |

共通規律: 各テストは「拒否されること」と「拒否が証跡（例外型・ログ・state_transitions）に残ること」
の両方を assert する（FR-34 postcondition）。fixture の profile は 2 件固定（A = active、B = active、
＋ archived 1 件を #1/#2 の派生ケースに使用）。

## §4 実装順

上位設計 §6 の段階表が正準。本書は実装作業の順序だけを確定する。

1. **前半（expand）**: `strategic_briefs`・`playbooks` への profile 列 expand ＋ backfill
   ＋新 UNIQUE index（migration 規律 = s0-contract §5）。全ストア API の scope 必須化と
   親チェーン検査の実装。
2. **後半（強制 = FN-306／FR-34）**: §3 の negative test 6 項目を test-first で赤→実装、
   認証・storage_state の物理分離、brief ガードへの profile 一致追加。
3. **完了**: 2 プロファイル目の解禁と、整合性クエリ＋越境テストの LP-OPS 定常実行。

ラチェット: スコープ検査の削減・緩和・「1 件運転だから省略」は禁止（FR-34 boundary）。

## §5 trace 表

| 実装単位 | DU | AC | TCC | 備考 |
|---|---|---|---|---|
| ストア API 規約の全面適用 | FN-306 実装 DU（⑤改訂で採番） | AC-34-1 | TCC-34-1 | プロファイル共存とスコープ付きクエリ |
| 越境拒否（読取・書込み・証跡化） | 同上 | AC-34-2 | TCC-34-2 | CrossProfileAccessDenied・DB 不変・拒否証跡 |
| archived 読取専用・ProfileKeyConflict | 同上 | AC-34-3 | TCC-34-3 | read_only スコープ・UNIQUE 翻訳 |
| brief 越境運転拒否（negative #5） | DU-01（start ガード）・DU-02（brief 検証） | AC-SR-02 | STC-I-03 | S0 の brief ガードに profile 一致を追加 |
| 認証・セッション分離（negative #4） | DU-14（secrets）・DU-15（browser storage_state） | AC-34-2（準用） | — | 物理分離実装時に⑥へ TC 追加 |
