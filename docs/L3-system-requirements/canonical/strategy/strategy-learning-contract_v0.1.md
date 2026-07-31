# 戦略学習契約（brief／TLP／revision）v0.1

> status: **confirmed**（2026-08-01 PO 承認 — 上流戦略インフィニティループ再強化指示。AI 起草）
> pair: [strategy-loop-test-design_v0.1.md](../../../L4-basic-design/integration-tests/strategy-loop-test-design_v0.1.md)（戦略層テスト設計 — HELIX 式文書ペア）
> 上位文書: [strategy-loop-requirements_v0.1.md](strategy-loop-requirements_v0.1.md)（SR）
> 位置づけ: 上流↔下流の**唯一の接続契約** 3 本 — 発注（strategic_brief）・還流（tactical_learning_packet）・
> 改訂（strategy_revision）— の実行契約。フィールドの正準は [json/strategy/](./) の schema、
> S0 の永続化は [s0-contract_v0.1.md](../s0-contract_v0.1.md) §2 の DDL（strategic_briefs／
> tactical_learning_packets）が正準。

---

## 1. 発注契約 — strategic_brief（上流→下流）

1. 下流ループは、`status = active` かつ有効期間内（valid_from ≤ now ≤ valid_until。valid_until NULL は無期限）
   の strategic_brief なしに開始できない。開始時に brief の `digest`（内容 sha256）を loop_run に固定保存し、
   run の全期間で brief の同一性を検証可能にする（digest 不一致 = 契約違反で開始拒否）。
2. brief は strategic_choice_id → segment_context_id → value_hypothesis_id の trace を必須で持ち、
   「期待する認識変化」「戦術目標」「媒体役割（media-roles.json の語彙）」「メッセージ仮説」
   「禁止パターン」「計測計画」を宣言する。**計測計画は「何を観測すれば仮説を判定できるか」であり、
   KPI 目標値の割当だけでは無効**。
2bis. **digest 算出規則（決定的）**: digest = brief 内容の**正準化 JSON の SHA-256**。正準化 =
   キー昇順ソート・区切り `(",", ":")`（空白なし）・UTF-8／NFC 正規化・`digest`／`status`／`created_at` を
   算出対象から除外。キー順・空白差で digest は変化しない（AC-SR-01 が決定性を検証）。
3. brief の改訂は supersedes_id による新版発行のみ（内容列の UPDATE は DDL トリガが拒否）。
   旧版は superseded へ遷移し、旧版に紐づく実行中 run は完走を許すが、新規 run は新版のみ参照する。
4. S0 では brief はシードコマンドで投入する（strategic_choice 等の上流モデル ID は S1 の上流実装まで
   JSON 正本上の ID 参照とする — schema 適合は投入時に検証）。

## 2. 還流契約 — tactical_learning_packet（下流→上流）

1. **全終端下流 run**（completed／failed／escalated／cancelled）は TLP を**ちょうど 1 件**持つ
   （DDL の `UNIQUE(loop_run_id)`）。TLP は loop_run_id・strategic_brief_id・strategic_brief_digest・
   evidence_ids を必須で持ち、DDL の整合トリガが「run は lower かつ終端」「TLP.brief_id = run.brief_id」
   「TLP.digest = run.digest = brief.digest」「二重 packet 禁止」を INSERT 時に強制する（AC-SR-06）。**最低 1 件**は、終端遷移と packet INSERT を同一 transaction で行う kernel 契約（completed=learning、failed/escalated/cancelled=failure）と、DU-11 verify()／LP-OPS ヘルスチェックの孤児検査（packet なし終端 lower run = 0 件）で強制する。
1bis. **packet_kind の二分**: `learning`（観測から学習を還流 — causal_interpretation・
   hypothesis_assessment 必須）と `failure`（観測前に失敗した run の事実還流 — failure_fact・
   reproduction_conditions・recovery_conditions 必須で、**causal_interpretation を持てない**）。
   観測が成立しなかった run へ因果解釈を捏造させない（DDL CHECK が強制）。
2. TLP は次を**別フィールドで分離**する: 観測された事実（observations — market_observation ID
   または事実文のみ）／計測値（metrics — KPI ツリー参照）／定性シグナル／異常／
   反証可能な仮説の判定（hypothesis_assessment: supported・weakened・rejected・inconclusive ＋対象仮説 ID＋理由）／
   AI による因果解釈（causal_interpretation）／対立説明（alternative_explanations）／
   推奨判断（recommended_next_action: continue・modify_tactic・request_strategy_review・stop）。
3. **下流は TLP を提出するだけであり、上流戦略正本を直接更新できない**（DDL 保護トリガ＋kernel 書込み経路。
   媒体コネクタ・計測処理も同様）。TLP の推奨判断は上流への入力であり、決定ではない。
4. 単一の KPI 変動だけで上流モデルを自動変更してはならない。上流は複数の観測・反証・信頼度・時間差を
   評価して revision を決定する（§3）。

## 3. 改訂契約 — strategy_revision（上流の改善工程）

1. 上流の改善工程は「行動計画の微修正」に閉じない。市場モデル・セグメント・問題定義・制約・代替行動・
   価値仮説・カテゴリー・ポジショニング・因果仮説・戦略判断・行動計画の**どれを更新するか**を
   strategy_revision の target_type で明示する。
2. revision は根拠（supporting_evidence_ids）・反証（counter_evidence_ids — 評価した反証がない場合も
   空配列を明示）・信頼度・対象版（target_version）を必須で持つ。
   **accepted には支持根拠 2 件以上を要求し、単一の計測値だけを根拠とした自動 accept を拒否する**。
3. **revision と新版生成の原子性**: `status = accepted` かつ `revision_type != maintain` では
   (a) `new_version_id` 必須、(b) 新版の `supersedes_id = target_id`、(c) 対象旧版の status 遷移
   （active → superseded／retired）、(d) revision accepted と新版 INSERT・旧版 status 遷移を
   **単一 transaction** で実行する。支持根拠 ID は重複禁止（uniqueItems）— 単一 KPI や同一根拠の
   重複で 2 件扱いしない。maintain（維持）も明示的な revision として記録し、
   「見ていない」と「見て維持した」を区別する。
4. revision が accepted になったとき、affected_brief_ids の brief は新版発行の対象になる
   （上流の行動計画工程が新 brief を発行 → 下流の次回転から適用）。

## 4. コンテンツ企画の価値定義宣言

主要コンテンツ企画（T-PLAN の plan_record payload）は
[content-plan-contract.json](content-plan-contract.json) の 5 キー —
**defined_problem（定義する問題）・recognition_change（変化させる認識）・comparison_axes（提示する比較軸）・
defined_value（定義する価値）・target_hypothesis_ids（対象となる戦略仮説）** — を必須で宣言する。
どの認識変化も起こさないコンテンツ企画は、集客物であっても主要企画として承認しない
（G-CONTENT-VALUE-DEFINITION）。

## 5. KPI ツリーとの関係

KPI ツリー（kpi_nodes／measurements）は両ループが読む**観測背骨**として維持する。
TLP の metrics は KPI ノード参照で記録し、計測の重複定義をしない。
KPI ツリーは「何が起きたか」を、意味モデル（market_model〜strategic_choice）は
「なぜ起きたと考えるか」を保持する — 前者から後者への自動書込み経路は存在しない。

## 6. S0／S1 の実装割当

| 項目 | S0 | S1+（上流戦略スライス） |
|---|---|---|
| strategic_briefs テーブル・シード・digest 保持・開始ガード | ○ | — |
| tactical_learning_packets テーブル・生成 | ○（最小: WP 週次回転の完了時） | 集約・評価 |
| 上流正本の直接変更拒否（トリガ＋経路） | ○ | — |
| 12 モデルの JSON Schema 確定 | ○（本コミットで確定） | — |
| market_observation〜strategic_choice の永続化・生成 | —（schema のみ） | ○ |
| revision エンジン（TLP 集約→提案→judge） | — | ○ |
| 媒体役割台帳の DB 化・コンテンツ企画ゲートの実行時強制 | —（JSON 台帳＋docs ゲート） | ○ |
