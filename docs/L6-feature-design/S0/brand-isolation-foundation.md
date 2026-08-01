---
artifact_id: L6-S0-BRAND-ISOLATION-FOUNDATION
lifecycle_status: confirmed
slice: S0
traces: [FR-71, FR-72]
forward_refs: [FR-34]
dus: [DU-12]
---

# 機能設計: ブランド隔離 S0 基盤（schema 共存・単一ブランド運転・拡張点）

> status: **confirmed**（2026-08-01 全層再降下 §7 — AI 起草。構造分類是正で S0／S1 に分割）
> 上位設計: [brand-isolation-design_v0.1.md](../../L4-basic-design/canonical/brand-isolation/brand-isolation-design_v0.1.md)（隔離の設計正本 — 隔離単位・帰属方式・分離資源の一覧は同書 §1〜§3。本書は再掲しない）
> 対スライス文書: [brand-isolation-completion.md](../S1/brand-isolation-completion.md)（S1 = 強制実装・複数ブランド。**スコープ型・解決関数・例外の実行時契約は同書が正本**）
> スキーマ = [s0-contract_v0.1.md §2](../../L3-system-requirements/canonical/s0-contract_v0.1.md)（`business_profiles`・FK スコープ列 — DDL 再掲禁止）。
> 位置づけ: S0 で**現行 DU／API だけで成立する**隔離基盤（schema 共存・単一ブランド運転・
> 名前空間規約・将来拡張点）に責務を限定する。S0 で実装しない API・型・実行時強制は本書に書かない。

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

本書が**実装単位まで降下させる**のは DU-12（config store）だけである。schema 共存と初期 seed は
正準 DDL と migrate の責務であり、その機能設計は [migration.md](migration.md)（DU-10・DU-11）が正本
— 本書は隔離の観点から要件面を述べるだけで、実装単位・API を二重に持たない。

| 実装単位 | 所属 | S0 での責務 | 失敗方針 |
|---|---|---|---|
| `profile_key` 名前空間規約 | config store（DU-12） | config キー・brief_key・credential 名の `<profile_key>.` 接頭を S0 から使う | 規約外命名は発行時に拒否（config 行の命名規約） |

隔離の観点から、S0 の schema・初期化に対して要求する事項（実装単位は migration.md 側）:

| 要求事項 | 降下先（機能設計の正本） | 内容 |
|---|---|---|
| `business_profiles` と FK スコープ列の schema 共存 | migration.md（DU-10 接続入口・DU-11 migrate/verify） | 列と制約が正準 DDL に**存在する**こと。NOT NULL 強制・deny-by-default は課さない |
| 単一プロファイルの seed | migration.md（DU-11 の初期 migrate） | 既定 profile を **1 件だけ**作る。2 件目の解禁は S1。重複は `profile_key` の UNIQUE 制約で拒否 |

### S0 で採用しないもの（対スライス文書が正本）

以下は S0 の DU／API に存在しないため、本書は設計を持たない。すべて
[brand-isolation-completion.md](../S1/brand-isolation-completion.md) が正本である。

- `ScopeContext` 値オブジェクトの実装と生成契約
- `resolve_scope(profile_key)` の解決経路
- 全ストア API への scope 伝搬・WHERE／INSERT 焼き込み・deny-by-default
- `CrossProfileAccessDenied` の実行時強制（越境の拒否と拒否の証跡化）
- 親チェーン検査・越境 negative test 6 項目・認証／storage_state の物理分離・2 プロファイル目の解禁

## §2 schema 共存の契約

- `business_profiles` の行は S0 では常に 1 件（cli 初期化が作る既定 profile）。`profile_key` は
  UNIQUE であり、重複登録は DB 制約で拒否される（アプリ層の重複検査を S0 で持たない）。
- 直接スコープ列（`business_profile_id`）は**列として存在するだけ**で、S0 では NOT NULL 強制と
  参照時の絞込みを課さない。S0 の全行は既定 profile に属するため、値は初期化時に決まる。
- `strategic_briefs`・`playbooks` は S0 では profile 列を持たない（S1 の expand 対象 — §3）。
- 本節は DDL を再掲しない。列・制約の正準は s0-contract §2 であり、矛盾したら契約を優先し本書を改訂する。

## §3 将来拡張点（対スライス文書へ渡す接続面）

| 拡張点 | S0 での姿 | S1 で足すもの（completion 文書が正本） |
|---|---|---|
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

本書が降下させる実装単位（frontmatter の `dus` と一致）:

| 実装単位 | DU | AC | TCC | 備考 |
|---|---|---|---|---|
| config の profile 名前空間 | DU-12（config store） | AC-33-1 | TCC-33-1 | `<profile_key>.` 接頭の運用開始 |

隔離の観点から要求し、**他文書が降下させる**事項（本書は DU を持たない）:

| 要求事項 | 機能設計の正本 | AC | TCC |
|---|---|---|---|
| `business_profiles` schema 共存・FK スコープ列 | migration.md（DU-10・DU-11） | AC-71-1 | TCC-71-1 |
| 単一プロファイル seed | migration.md（DU-11） | AC-71-1（準用） | TCC-71-1（準用） |
