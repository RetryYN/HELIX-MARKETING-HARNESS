# ブランド隔離設計書 v0.1（基本設計増補 — BR-I1・REQ-046 の設計正本）

> status: **draft（再降下中）**（2026-08-01 全層再降下 §6 — AI 起草）
> 正準参照: 要求の正準は BR-I1（[json/br/br-contracts.json](../../../L1-business-requirements/canonical/br/br-contracts.json)）・
> REQ-046・FR-34（[json/fr/fr-contracts.json](../../../L3-system-requirements/canonical/functional/fr-contracts.json)）。
> スキーマの正準は [s0-contract_v0.1.md §2](../../../L3-system-requirements/canonical/s0-contract_v0.1.md)
> （`business_profiles` と FK スコープ列 — DDL は再掲しない）。
> 上位設計: [basic-design_v0.1.md](../basic-design_v0.1.md)／[db-design_v0.1.md](../data/db-design_v0.1.md)
> 位置づけ: ブランド越境（参照・書込み・認証・学習の混線）を**構造的に不可能**にする設計の正本。
> FR-34 はスライス S1 — S0 は schema 共存＋単一ブランド運転、S1 でスコープ強制を実装する（§6）。

---

## 1. 隔離単位とスコープ列の設計方針

- **隔離単位 = `business_profiles` 1 行**（S0 では business_profile = brand。ブランド＝事業
  プロファイルの 1:1 を既定とし、1 プロファイル内複数ブランドの細分化は S1+ の expand で扱う）。
- **識別は `profile_key`（UNIQUE）のみ**を制約とし、複数プロファイルの共存はスキーマとして常に
  許される（FR-34 invariant）。S0 の単一ブランド運転は「active なプロファイルが 1 件」という
  **運用状態**であって、スキーマ制約ではない。
- **スコープ列の設計**: 全業務データは次のいずれかで profile に帰属する。

| 帰属方式 | 対象テーブル | 方針 |
|---|---|---|
| 直接スコープ列（`business_profile_id` FK） | business_profiles（root）・brand_plans・action_plans・kpi_nodes | 集約ルートに直接列を持つ（DDL 済み） |
| 親チェーン経由の導出スコープ | sprints（→action_plans）・loop_runs（→sprints）・tasks（→loop_runs）・evidence／external_operations／assets／approvals／spend_ledger（→tasks）・measurements／pair_kpi_measure・learnings・pair_plan_quality・tactical_learning_packets | FK 連鎖で一意に導出できるため列を重複させない（非正規化による二重管理を避ける） |
| S1 で直接列を expand 追加 | strategic_briefs・playbooks | §6 参照。現 DDL は profile 列を持たない — S0 単一運転では安全、複数運転の前提条件として追加 |
| プロファイル非帰属（共有基盤） | agents・agent_executions・workflows・config・schema_version・state_transitions | エンジン側の資源。ただし config はキー命名で名前空間化できる（`<profile_key>.` 接頭 — S1） |

- 導出スコープの正しさは FK（全て ON DELETE RESTRICT）が保証する。**チェーンをまたぐ FK の
  プロファイル不一致**（例: action_plan の brand_plan と business_profile_id の不一致）は、
  ストア層の書込み時検査＋§4 の整合性クエリで検出する。

## 2. ストア層でのスコープ解決一元化（呼出側 WHERE 依存の禁止）

FR-34 の constraint「スコープ解決はストア層で一元化」を次の構造で実装する。

1. **ScopeContext 値オブジェクト**: `business_profile_id` を保持する検証済み値オブジェクト。
   生成はプロファイルストアの `resolve_scope(profile_key)` のみ（active でないプロファイルの
   書込みスコープは生成拒否 — archived は読取専用スコープのみ発行）。
2. **ストア API はスコープ必須引数**: スコープ対象テーブルを扱う全ストア関数は第一級引数に
   ScopeContext を取り、内部で WHERE / INSERT 列に焼き込む。**呼出側が WHERE 句で絞る設計を
   禁止**し、スコープなしのアクセス経路を型シグネチャで存在させない（deny-by-default）。
3. **越境は例外で拒否**: 要求スコープと行の帰属が食い違う参照・書込みは
   `CrossProfileAccessDenied` を raise し、DB を変更せず構造化ログに拒否を証跡化する（FR-34）。
   `profile_key` 重複は UNIQUE 制約で `ProfileKeyConflict`。
4. **導出スコープの検査点**: 親チェーン帰属のテーブルは、書込み時に親行のスコープを JOIN で
   検証してから INSERT する（例: task 生成時に loop_run→sprint→action_plan の profile を確認）。
   読取は集約ルート側の API を経由させ、子テーブル単独の全件クエリを公開しない。
5. **1 件でも省略しない**: プロファイルが 1 件のみでもスコープ強制は省略されない（FR-34
   boundary）。S0 実装がこの構造を先取りするほど S1 の差分は小さくなるが、S0 の完了条件には
   含めない（§6）。

## 3. 認証・攻略地図・KPI ツリー・TLP のブランド別分離

| 資源 | 分離設計 | 禁止事項（BR-I1 prohibitions） |
|---|---|---|
| 認証（CMP-07 秘匿ストア） | credential 名を `<profile_key>/<service>/<name>` で名前空間化し、**物理ファイルもプロファイル別**に分ける（test/prod の物理分離と直交）。ScopeContext なしで credential を取得する API を設けない | ブランド共有の認証セッション。プロファイル横断の credential 参照 |
| ブラウザセッション（CMP-08） | Playwright `storage_state` をプロファイル別ファイルに永続化（`<profile_key>/` 配下）。起動引数に ScopeContext を必須化 | 別ブランドの storage_state 再利用（ログイン混線＝アカウント停止の伝染経路） |
| 攻略地図（CMP-09 playbooks） | S0: 単一運転のため共有。S1: `business_profile_id` を expand 追加し、UNIQUE を `(profile, service, operation, route_type)` の新 index で置換（§6）。セレクタ・手順にブランド固有値を焼き込まない（充填は config/profile_json 側） | 他ブランドで学習した selector・手順の無断流用（サイト構造が別物） |
| KPI ツリー（CMP-13 kpi_nodes） | DDL 済み: `business_profile_id` 直接列＋`UNIQUE (business_profile_id, node_key)`。node_key はプロファイル内でのみ一意 — ツリーはブランドごとに独立 | ブランド横断の集計ノード（メタ学習は S1+ で隔離を保ったまま別設計） |
| 上流戦略・学習（strategic_briefs / TLP） | brief はブランドの認識変化仮説そのものであり越境流用禁止。S0: brief_key の命名規約 `<profile_key>-...` で運用分離。S1: `business_profiles` FK を expand 追加し、lower run の start ガード（brief ガード）に「run のプロファイル = brief のプロファイル」を追加。TLP は loop_run・brief 両 FK から帰属が導出され、digest 三者一致トリガが別ブランド brief への付替えを既に拒否する | 他ブランド TLP の無断流用。他ブランド brief での下流運転 |

## 4. 越境検出（negative test 方針）

隔離は「越境できないことのテスト」が完了証跡である（BR-I1 completion_evidence）。S1 の
スコープ強制実装時に以下の negative test 群を必須とする（AC-34-1〜3 に接続）。

1. **越境読取 0 件**: プロファイル A のスコープで B のデータ（brand_plans / kpi_nodes /
   measurements / TLP）を要求 → 結果 0 件、かつストア API 直指定（B の行 id）は
   `CrossProfileAccessDenied`。
2. **越境書込み拒否**: A スコープで B の action_plan 配下に sprint / task を生成 → 例外＋
   DB 不変＋拒否の構造化ログ。
3. **FK 不一致検出**: `action_plans.business_profile_id` と親 `brand_plans` のプロファイルを
   故意に食い違わせる INSERT → ストア層検査で拒否。整合性クエリ（db-design §6 の read-only
   検査に追加）で既存データの不一致 0 件を常時確認。
4. **認証・セッション越境**: A の ScopeContext で B の credential 名・storage_state を要求 →
   取得不能（fail-close）。テストは mock 秘匿ストアで実施。
5. **brief 越境運転拒否**: B の brief を A の lower run に与えて start → brief ガードで開始拒否
   （guard_result = rejected が state_transitions に残る）。
6. **スコープ未指定 deny-by-default**: ScopeContext なしの API 呼出しが型・実行時の双方で
   成立しないこと（レビュー規律＋実行時 assert）。

検査は「拒否されること」だけでなく「拒否が証跡に残ること」（FR-34 postcondition）まで assert する。

## 5. 障害の非伝染（設計原則）

BR-I1 の failure_impact（1 ブランドの事故の全ブランド伝染）に対する設計上の防波堤:

- 停止・escalate はプロファイル帰属の loop_run / task 単位で発生し、他プロファイルの run を
  巻き込む共有状態を持たない（共有はエンジン資源のみ — §1 の非帰属表）。
- credential 失効・アカウント停止（fatal_failure）はそのプロファイルの run を escalated に
  するだけで、他プロファイルの認証には物理的に触れない（§3 認証分離）。
- ブランドの追加・廃止は人間の意思決定（BR-I1 human_judgement）。廃止は archived 化
  （読取可・新規書込み不可）であり、参照行がある限り DELETE は FK が拒否する。

## 6. S0 → S1 の段階導入計画

| 段階 | 導入内容 | 完了証跡 |
|---|---|---|
| **S0（schema ＋単一運転）** | 正準 DDL の `business_profiles`・直接スコープ列・FK 連鎖（適用済み）。CLI init で単一プロファイルを seed し、active 1 件で運転。brief_key・credential 名の profile 接頭規約を運用開始 | DDL 生成検証（FR-71）・単一プロファイル seed の存在 |
| **S1 前半（expand）** | `strategic_briefs.business_profile_id`・`playbooks.business_profile_id` を NULL 許容で expand 追加 → 既存行を backfill（単一プロファイルなので決定的・冪等）→ 新 UNIQUE index 追加。config キーの名前空間規約導入 | migration ＋ backfill evidence・DU-11 verify() green |
| **S1 後半（スコープ強制 = FN-306 / FR-34）** | ScopeContext・`resolve_scope`・全ストア API のスコープ必須化、書込み時の親チェーン検査、brief ガードへのプロファイル一致追加、認証・storage_state の物理分離 | §4 の negative test 全 green・越境拒否ログ・ハードコード検出ゲート green |
| **S1 完了（複数運転解禁）** | 2 プロファイル目の登録を解禁し、分離監査（§4-3 整合性クエリ＋越境テストの定常実行）を LP-OPS ヘルスチェックに組込み | ブランド別データの分離監査（BR-I1 completion_evidence） |

段階導入の不変条件: 各段階は前方参照のみ（rename・意味変更なし — FR-72）、ラチェット
（スコープ検査の削減・緩和は禁止）、S0 構造の変更を要しない（基本設計 §6 と同じ載せ方 —
ScopeContext はストア層引数の追加であり、層分離・単方向依存を変えない）。
