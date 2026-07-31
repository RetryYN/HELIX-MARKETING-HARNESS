# 機能設計: ブランド隔離（ScopeContext・ストア層スコープ強制）

> status: **draft（再降下中）**（2026-08-01 全層再降下 §7 — AI 起草）
> 上位設計: [brand-isolation-design_v0.1.md](../brand-isolation-design_v0.1.md)（隔離の設計正本 — 隔離単位・帰属方式・分離資源の一覧は同書 §1〜§3。本書は再掲しない）
> 正準参照: 要求 = BR-I1（[br-contracts.json](../../requirements/json/br/br-contracts.json)）・REQ-046・FR-34。
> スキーマ = [s0-contract_v0.1.md §2](../../requirements/s0-contract_v0.1.md)（`business_profiles`・FK スコープ列 — DDL 再掲禁止）。
> 位置づけ: 上位設計が確定した隔離構造を、実装単位（型・関数シグネチャ・検査点・テスト実装方針）まで降下させる。

---

## §0 位置づけ・動機

ブランド越境（参照・書込み・認証・学習の混線）を**構造的に不可能**にする実装の詳細。
上位設計の方針「スコープ解決はストア層で一元化・呼出側 WHERE 依存の禁止」（BR-I1 constraint）を、
型シグネチャと例外契約に落とす。FR-34 の強制実装はスライス S1 — S0 は schema 共存＋単一ブランド
運転であり、本書は S0 で先取りする範囲と S1 で完成させる範囲を実装順として画定する（§5）。

## §1 責務分離

| 実装単位 | 所属 | 責務 | 失敗方針 |
|---|---|---|---|
| `ScopeContext`（値オブジェクト） | `db/scope.py`（新設・CMP-05 副層） | `business_profile_id`＋`profile_key`＋`mode`（read_write／read_only）の frozen 保持。直接コンストラクトを封じ、生成は `resolve_scope` のみ | 生成経路外のインスタンス化は実行時 assert で拒否 |
| `resolve_scope(profile_key)` | プロファイルストア（`db/profiles.py`） | profile_key → ScopeContext の唯一の生成点。active = read_write、archived = read_only、不在 = 例外 | 不在・draft は `ScopeResolutionFailed`（fail-close） |
| スコープ付きストア API | 各ストア副層（CMP-04/05/06 ほか） | 第一引数に ScopeContext を取り、WHERE / INSERT 列へ内部で焼き込む | スコープなしシグネチャを公開しない（deny-by-default） |
| 親チェーン検査 | ストア副層の書込み関数内 | 導出スコープ表（上位設計 §1）に従い、INSERT 前に親行の profile を JOIN 検証 | 不一致は `CrossProfileAccessDenied`・DB 不変 |
| 整合性クエリ | `db/verify.py`（DU-11 `verify()` に追加） | 既存データの FK チェーン profile 不一致 0 件を read-only 検査 | 不一致検出は verify 赤（escalate 誘導） |
| 越境拒否の証跡化 | 構造化ログ（NFR-2 経路） | 拒否の profile 組・API 名・行 id を記録（FR-34 postcondition） | ログ失敗でも拒否自体は成立（拒否が先） |

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
  ストア API へ渡した場合は `CrossProfileAccessDenied`（archived への新規書込み拒否 — AC-34-3）。
- 受け渡し: CLI 入口（`--profile <key>` 又は config の既定 profile）で 1 回だけ解決し、
  kernel → ゲート → ストアへ**引数として明示的に伝搬**する。スレッドローカル・グローバル変数・
  暗黙の「現在プロファイル」を持たない（単方向依存を壊さず、テストで注入可能に保つ）。

### §2.2 ストア API シグネチャ規約

| 規約 | 内容 |
|---|---|
| 第一級引数 | スコープ対象テーブル（上位設計 §1 の直接／導出帰属の全テーブル）を扱う全ストア関数は `scope: ScopeContext` を必須第一引数とする |
| WHERE 焼き込み | 読取は `WHERE business_profile_id = :scope_id`（直接列）又は集約ルート JOIN（導出）で内部絞込み。呼出側 WHERE 句への依存を禁止 |
| INSERT 焼き込み | 直接スコープ列を持つテーブルは scope から列値を焼き込む。呼出側が business_profile_id を渡す引数を設けない |
| 行 id 直指定 | id 指定の単行取得も帰属検証を通し、他 profile の行は「不在」ではなく `CrossProfileAccessDenied` を raise（存在秘匿より拒否証跡を優先 — AC-34-2） |
| 非帰属テーブル | agents・workflows・config 等（上位設計 §1 の共有基盤）はスコープ引数を取らない。config は S1 で `<profile_key>.` キー接頭の名前空間化 |

### §2.3 例外契約

| 例外 | 発生点 | 状態機械への写像 |
|---|---|---|
| `CrossProfileAccessDenied` | 越境の参照・書込み・read_only スコープでの書込み | ゲート拒否と同格 — task 文脈では non_retryable_failure（failed）。DB 不変＋拒否ログ |
| `ProfileKeyConflict` | profile_key 重複登録（UNIQUE 制約の翻訳） | 登録操作の拒否のみ（既存行不変 — AC-34-3） |
| `ScopeResolutionFailed` | 不在・draft プロファイルの解決要求 | 実行開始前の拒否（外部操作 0 回） |

## §3 親チェーン検査の実装

導出スコープテーブル（sprints／loop_runs／tasks／evidence 等 — 一覧は上位設計 §1）への書込みは、
同一 transaction 内で親行の帰属を確認してから INSERT する。

1. 検査 SQL は「親 FK を集約ルートまで JOIN し business_profile_id を取り出す」再帰しない固定
   チェーン（最長: evidence → tasks → loop_runs → sprints → action_plans）。各ストア関数が
   自テーブル専用の検査クエリを持つ（動的 SQL 生成をしない — 検査経路の監査可能性）。
2. 取り出した profile と `scope.business_profile_id` の不一致は INSERT せず
   `CrossProfileAccessDenied`（1 遷移 1 transaction の原則内 — 検査と INSERT は同一 transaction）。
3. FK 不一致の混入防御は二重: 書込み時検査（本節）＋ DU-11 `verify()` の整合性クエリ
   （既存全行の不一致 0 件 — 上位設計 §4-3）。verify は read-only であり修復しない（検出 → escalate）。

## §4 越境 negative test 6 項目の実装方針

上位設計 §4 の 6 項目を pytest 実装へ対応付ける（S1 で必須 green。テストファイルは⑥の規約
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

## §5 実装順（S0 → S1）

上位設計 §6 の段階表が正準。本書は実装作業の順序だけを確定する。

1. **S0（今スライス — 完了条件には含めない先取り）**: 正準 DDL の schema 共存は適用済み。
   CLI init の単一プロファイル seed、`resolve_scope` と ScopeContext の骨格、brief_key・credential
   名の `<profile_key>` 接頭規約の運用開始。ストア API の scope 引数は**新設分から**採用する
   （既存 API の一斉改修は S1 前半へ送る — S0.1 の test-first 対象を増やさない）。
2. **S1 前半（expand）**: `strategic_briefs`・`playbooks` への profile 列 expand ＋ backfill
   ＋新 UNIQUE index（migration 規律 = s0-contract §5）。全ストア API の scope 必須化と
   親チェーン検査の実装。
3. **S1 後半（強制 = FN-306／FR-34）**: §4 の negative test 6 項目を test-first で赤→実装、
   認証・storage_state の物理分離、brief ガードへの profile 一致追加。
4. **S1 完了**: 2 プロファイル目の解禁と、整合性クエリ＋越境テストの LP-OPS 定常実行。

ラチェット: スコープ検査の削減・緩和・「1 件運転だから省略」は禁止（FR-34 boundary）。

## §6 trace 表

| 実装単位 | DU | AC | TCC | 備考 |
|---|---|---|---|---|
| ScopeContext・resolve_scope・ストア API 規約 | DU-10（接続入口）・DU-11（verify 整合性クエリ）＋ S1 の FN-306 実装 DU（⑤改訂で採番） | AC-34-1 | TCC-34-1 | プロファイル共存とスコープ付きクエリ |
| 越境拒否（読取・書込み・証跡化） | 同上 | AC-34-2 | TCC-34-2 | CrossProfileAccessDenied・DB 不変・拒否証跡 |
| archived 読取専用・ProfileKeyConflict | 同上 | AC-34-3 | TCC-34-3 | read_only スコープ・UNIQUE 翻訳 |
| brief 越境運転拒否（negative #5） | DU-01（start ガード）・DU-02（brief 検証） | AC-SR-02 | STC-I-03 | S0 の brief ガードに S1 で profile 一致を追加 |
| 認証・セッション分離（negative #4） | DU-14（secrets）・DU-15（browser storage_state） | AC-34-2（準用） | — | S1 の物理分離実装時に⑥へ TC 追加 |
