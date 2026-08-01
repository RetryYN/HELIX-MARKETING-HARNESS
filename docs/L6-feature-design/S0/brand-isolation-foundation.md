---
artifact_id: L6-S0-BRAND-ISOLATION-FOUNDATION
lifecycle_status: draft
slice: S0
traces: [FR-71, FR-72]
forward_refs: []
dus: [DU-12]
---

# 機能設計: ブランド隔離 S0 基盤（schema 共存・単一ブランド運転・拡張点）

> status: **draft**（2026-08-01 全層再降下 §7 — AI 起草。構造分類是正で S0／S1 に分割）
> 上位設計: [brand-isolation-design_v0.1.md](../../L4-basic-design/canonical/brand-isolation/brand-isolation-design_v0.1.md)（隔離の設計正本 — 隔離単位・帰属方式・分離資源の一覧は同書 §1〜§3。本書は再掲しない）
> 対スライス文書: [brand-isolation-completion.md](../S1/brand-isolation-completion.md)（S1 = 強制実装・複数ブランド）
> スキーマ = [s0-contract_v0.1.md §2](../../L3-system-requirements/canonical/s0-contract_v0.1.md)（`business_profiles`・FK スコープ列 — DDL 再掲禁止）。
> 位置づけ: S0 で**先取りして成立している**隔離基盤（schema 共存・単一ブランド運転・将来拡張点）
> だけを実装単位まで降下させる。強制実装（全ストア API の scope 必須化・越境 negative test・
> 複数ブランド解禁）は S1 側の文書が正本であり、本書は持たない。

---

## §0 位置づけ・動機

ブランド越境（参照・書込み・認証・学習の混線）を**構造的に不可能**にするための土台を、S0 の
schema と単一ブランド運転の中に先に置く。S0 の要求根拠は FR-71（主要テーブル — `business_profiles`
と FK スコープ列が正準 DDL に存在すること）であり、隔離の**強制**は S1 の要求である。
S0 でスコープ列だけ先に持つのは、後続スライスの expand migration を「列追加」ではなく
「既存列の必須化」に留めるため（前方参照のみの昇格 — FR-72）。

## §1 S0 で成立させる実装単位

| 実装単位 | 所属 | S0 での責務 | 失敗方針 |
|---|---|---|---|
| `ScopeContext`（値オブジェクト） | `db/scope.py`（新設・CMP-05 副層） | `business_profile_id`＋`profile_key`＋`mode`（read_write／read_only）の frozen 保持。直接コンストラクトを封じ、生成は `resolve_scope` のみ | 生成経路外のインスタンス化は実行時 assert で拒否 |
| `resolve_scope(profile_key)` | プロファイルストア（`db/profiles.py`） | profile_key → ScopeContext の唯一の生成点。active = read_write、archived = read_only、不在 = 例外 | 不在・draft は `ScopeResolutionFailed`（fail-close） |
| CLI init の単一プロファイル seed | cli 層 | 既定 profile を 1 件だけ作る。2 件目の解禁は後続スライス | 重複 key は `ProfileKeyConflict` |
| 命名の名前空間規約 | 運用規約 | brief_key・credential 名の `<profile_key>` 接頭を S0 から使う | 規約外命名は発行時に拒否 |

S0 で採用しないもの（対スライス文書が正本）: 全ストア API の scope 必須化、親チェーン検査、
越境 negative test 6 項目、認証・storage_state の物理分離、2 プロファイル目の解禁。

## §2 型・契約

### §2.1 ScopeContext

```python
@dataclass(frozen=True)
class ScopeContext:
    business_profile_id: int
    profile_key: str
    mode: Literal["read_write", "read_only"]
```

- 生成契約（DbC）: pre = profile 行が存在し status ∈ {active, archived}。
  post = active → `read_write`、archived → `read_only`。draft・不在は `ScopeResolutionFailed`。
- invariant: frozen（生成後の profile 付替え不可）。`mode = read_only` のスコープを書込み系
  ストア API へ渡した場合は `CrossProfileAccessDenied`（archived への新規書込み拒否）。
- 受け渡し: CLI 入口（`--profile <key>` 又は config の既定 profile）で 1 回だけ解決し、
  kernel → ゲート → ストアへ**引数として明示的に伝搬**する。スレッドローカル・グローバル変数・
  暗黙の「現在プロファイル」を持たない（単方向依存を壊さず、テストで注入可能に保つ）。

### §2.2 例外契約

| 例外 | 発生点 | 状態機械への写像 |
|---|---|---|
| `CrossProfileAccessDenied` | 越境の参照・書込み・read_only スコープでの書込み | ゲート拒否と同格 — task 文脈では non_retryable_failure（failed）。DB 不変＋拒否ログ |
| `ProfileKeyConflict` | profile_key 重複登録（UNIQUE 制約の翻訳） | 登録操作の拒否のみ（既存行不変） |
| `ScopeResolutionFailed` | 不在・draft プロファイルの解決要求 | 実行開始前の拒否（外部操作 0 回） |

### §2.3 新設 API の署名規約（S0 の先取り範囲）

- S0 で**新設する**ストア関数は `scope: ScopeContext` を必須第一引数とする。
- 既存 API の一斉改修は行わない（S0.1 の test-first 対象を増やさないため — 後続スライスへ送る）。
- 直接スコープ列を持つテーブルへの INSERT は scope から列値を焼き込み、呼出側が
  `business_profile_id` を渡す引数を設けない。

## §3 将来拡張点（対スライス文書へ渡す接続面）

| 拡張点 | S0 での姿 | 後続スライスで足すもの |
|---|---|---|
| ストア API の scope | 新設分のみ必須 | 全 API 必須化（deny-by-default） |
| 親チェーン検査 | なし | 導出スコープ表に沿った INSERT 前 JOIN 検証 |
| `strategic_briefs`・`playbooks` の profile 列 | なし | expand ＋ backfill ＋新 UNIQUE index（migration 規律 = s0-contract §5） |
| 整合性クエリ | `verify()` に不一致検査を持たない | DU-11 `verify()` へ FK チェーン profile 不一致 0 件検査を追加 |
| brief 開始ガード | brief id＋digest のみ | profile 一致条件を追加 |
| 認証・storage_state | 命名接頭のみ | 物理分離 |

ラチェット: ここに挙げた拡張点の削減・「1 件運転だから省略」は禁止。

## §4 trace 表

| 実装単位 | DU | AC | TCC | 備考 |
|---|---|---|---|---|
| `business_profiles` schema 共存・FK スコープ列 | DU-10（接続入口）・DU-11（migrate/verify） | AC-71-1 | TCC-71-1 | S0 の正準 DDL に存在すること |
| config の profile 名前空間 | DU-12（config store） | AC-33-1 | TCC-33-1 | `<profile_key>.` 接頭の運用開始 |
| ScopeContext・resolve_scope の骨格 | DU-10・DU-11 | AC-71-1（準用） | TCC-71-1（準用） | 生成点の一元化のみ。強制は後続スライス |
