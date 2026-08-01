---
artifact_id: L6-S0-BRAND-ISOLATION-FOUNDATION
lifecycle_status: confirmed
slice: S0
traces: [FR-71, FR-72]
forward_refs: [FR-34]
dus: []
---

# 機能設計: ブランド隔離 S0 基盤（schema 共存・単一ブランド運転・拡張点）

> status: **confirmed**（2026-08-01 全層再降下 §7 — AI 起草。構造分類是正で S0／S1 に分割）
> 上位設計: [brand-isolation-design_v0.1.md](../../L4-basic-design/canonical/brand-isolation/brand-isolation-design_v0.1.md)（隔離の設計正本 — 隔離単位・帰属方式・分離資源の一覧は同書 §1〜§3。本書は再掲しない）
> 対スライス文書: [brand-isolation-completion.md](../S1/brand-isolation-completion.md)（S1 = 強制実装・複数ブランド。**スコープ型・解決関数・例外の実行時契約は同書が正本**）
> スキーマ = [s0-contract_v0.1.md §2](../../L3-system-requirements/canonical/s0-contract_v0.1.md)（`business_profiles`・FK スコープ列 — DDL 再掲禁止）。
> 位置づけ: S0 における隔離の**姿勢**（schema 列の共存・運用規約・将来拡張点）だけを述べる。
> S0 の現行 DU／API に隔離固有の実装はなく、本書は実装単位（`implementation_units`）を持たない。

---

## §0 位置づけ・動機

ブランド越境（参照・書込み・認証・学習の混線）を**構造的に不可能**にするための土台を、S0 の
schema と単一ブランド運転の中に先に置く。S0 の要求根拠は FR-71（主要テーブル — `business_profiles`
と FK スコープ列が正準 DDL に存在すること）と FR-72（前方参照のみの昇格）であり、隔離の**強制**は
S1 の要求（FR-34）である。S0 でスコープ列だけ先に持つのは、後続スライスの expand migration を
「列追加」ではなく「既存列の必須化」に留めるためであり、S0 の時点で越境が止まることは意味しない。

**S0 は「越境が起きても止まらない」状態を明示的に許容する。** 止めるのは S1 の責務であり、
S0 の機能設計へ止める仕組みを書くと、実装されない API が設計正本に残る（本書はそれを持たない）。

## §1 S0 で成立させる実装単位

**本書は実装単位を持たない**（`implementation_units` = 空）。S0 の現行 DU／API に、ブランド隔離
固有の振る舞いを実装する API が 1 本も存在しないためである。実装のない責務を機能設計に書くと、
「設計上は済んでいる」という誤った完了感が残る（PO 指示 §2 の是正）。

| 主張 | S0 での実際 | 降下先 |
|---|---|---|
| `business_profiles` と FK スコープ列の schema 共存 | 正準 DDL に列と制約が**存在する**だけ（NOT NULL 強制・deny-by-default はない）。適用と検査は migrate の責務 | [migration.md](migration.md)（DU-10・DU-11） |
| 単一プロファイルの seed | **S0 では実装しない**。`seed_default_profile` に相当する API は現行 DU に存在せず、S0 で既定 profile 行が作られる保証はない | [brand-isolation-completion.md](../S1/brand-isolation-completion.md) §1.3（S1） |
| `profile_key` 名前空間規約 | **運用規約**（人が守る命名規約）であり、機械的強制ではない。DU-12 の汎用 `set`／`get` は key の名前空間を検査しない | S1 で profile スコープ専用 API を新設するまで規約のまま |

### S0 で採用しないもの（対スライス文書が正本）

以下は S0 の DU／API に存在しないため、本書は設計を持たない。すべて
[brand-isolation-completion.md](../S1/brand-isolation-completion.md) が正本である。

- `ScopeContext` 値オブジェクトの実装と生成契約
- `resolve_scope(profile_key)` の解決経路
- 全ストア API への scope 伝搬・WHERE／INSERT 焼き込み・deny-by-default
- `CrossProfileAccessDenied` の実行時強制（越境の拒否と拒否の証跡化）
- 親チェーン検査・越境 negative test 6 項目・認証／storage_state の物理分離・2 プロファイル目の解禁

## §2 schema 共存の契約

- `profile_key` は UNIQUE であり、重複登録は DB 制約で拒否される（アプリ層の重複検査を S0 で持たない）。
  ただし **S0 は行を作る API を持たない** — 「既定 profile が 1 件ある」ことを前提にした設計を
  S0 の他文書へ書かない。
- 直接スコープ列（`business_profile_id`）は**列として存在するだけ**で、S0 では NOT NULL 強制と
  参照時の絞込みを課さない。列値の埋め方が決まるのは seed を実装する S1 である。
- `strategic_briefs`・`playbooks` は S0 では profile 列を持たない（S1 の expand 対象 — §3）。
- 本節は DDL を再掲しない。列・制約の正準は s0-contract §2 であり、矛盾したら契約を優先し本書を改訂する。

## §3 将来拡張点（対スライス文書へ渡す接続面）

| 拡張点 | S0 での姿 | S1 で足すもの（completion 文書が正本） |
|---|---|---|
| 既定 profile の seed | なし（行を作る API を持たない） | `seed_default_profile()`（冪等・2 件目は拒否・`business_profile_id` を返す） |
| profile スコープ config キー | 運用規約のみ（機械的強制なし） | profile スコープ専用 API・global key との分類・規約外キーの拒否例外 |
| スコープ型と解決経路 | なし（型を定義しない） | `ScopeContext`＋`resolve_scope` の一元的な生成点 |
| ストア API の scope | なし | 全 API の必須第一引数化（deny-by-default） |
| 越境の実行時拒否 | なし | `CrossProfileAccessDenied` と拒否証跡（FR-34 postcondition） |
| 親チェーン検査 | なし | 導出スコープ表に沿った INSERT 前 JOIN 検証 |
| `strategic_briefs`・`playbooks` の profile 列 | なし | expand ＋ backfill ＋新 UNIQUE index（migration 規律 = s0-contract §5） |
| 整合性クエリ | `verify()` に不一致検査を持たない | DU-11 `verify()` へ FK チェーン profile 不一致 0 件検査を追加 |
| brief 開始ガード | brief id＋digest のみ | profile 一致条件を追加 |
| 認証・storage_state | 命名接頭のみ | 物理分離 |

ラチェット: ここに挙げた拡張点の削減・「1 件運転だから省略」は禁止。S0 側へ前倒しで実装を書き戻す
（＝実装されない API を S0 の設計正本に置く）ことも禁止する。

## §4 trace 表

本書は実装単位を持たないため、DU・API・AC・TC・UT への trace も持たない
（`implementation_units` = 空）。隔離の観点から要求する事項は、それを**実装する文書**が trace を持つ:

| 要求事項 | trace を持つ機能設計 |
|---|---|
| `business_profiles` schema 共存・FK スコープ列の適用と存在検査 | [migration.md](migration.md)（DU-10・DU-11） |
| 単一プロファイルの seed | [brand-isolation-completion.md](../S1/brand-isolation-completion.md)（S1） |
| profile スコープ付き config キーの機械的強制 | [brand-isolation-completion.md](../S1/brand-isolation-completion.md)（S1） |
