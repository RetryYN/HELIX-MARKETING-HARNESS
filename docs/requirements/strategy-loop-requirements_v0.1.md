# 上流戦略ループ要件定義 v0.1

> status: **confirmed**（2026-08-01 PO 承認 — 上流戦略インフィニティループ再強化指示。AI 起草）
> pair: [strategy-loop-test-design_v0.1.md](../design/strategy-loop-test-design_v0.1.md)（戦略層テスト設計 — HELIX 式文書ペア）
> 上位文書: [marketing-harness-charter_v0.4.md](../L0-charter/marketing-harness-charter_v0.4.md)（北極星）／
> [loop-task-workflow_v0.1.md](loop-task-workflow_v0.1.md)（LP-U の工程名は本書でも維持）
> 機械可読正本: [json/strategy/](json/strategy/)（12 schema・媒体役割台帳・コンテンツ企画契約・[sr.json](json/strategy/sr.json)）。
> 契約詳細（brief／TLP／revision）は [strategy-learning-contract_v0.1.md](strategy-learning-contract_v0.1.md)。
> **実行契約正本（2026-08-01 全層再降下 §3）**: 各 SR の 18 観点実行契約 =
> [json/strategy/sr-contracts.json](json/strategy/sr-contracts.json)
> （ビュー [sr-contracts_v0.1.md](sr-contracts_v0.1.md)。G-FRSR-CONTRACT が fail-close 検査）。
>
> 位置づけ: 上流戦略ループが「下流の数値を受けて行動計画を微修正するだけの管理ループ」へ縮退することを
> 構造的に禁止し、市場理解・価値定義・戦略仮説そのものを継続的に更新するインフィニティループとして
> 完成させるための要件。**二重ループの再設計ではない** — 既存の上流／下流ループ・還流・媒体別非同期回転・
> KPI ツリー接続はすべて維持する。

---

## 1. 二重ループの責務分離（維持必須の前提）

- **SR-01 責務分離**: 上流戦略ループ＝「何を市場と捉え、誰のどの状況に、どの価値を定義し、どの選択基準を
  形成するか」を学習する。下流戦術ループ＝「確定した戦略仮説の範囲内で、どの媒体・表現・運用方法が
  有効か」を学習する。両者を一つの PDCA・OODA・スクラムループへ統合してはならない。
  学習対象の違いは本節と charter v0.4 §3 に明文化され、両ループの成果物型（上流 = 意味モデル群、
  下流 = 公開物＋計測＋TLP）が交差しないことで機械的に分離される。
- **SR-12 KPI ツリーの位置づけ**: KPI ツリーは維持するが**観測背骨**であり、戦略正本にしない。
  「なぜその結果が発生したと考えるか」は市場・価値・戦略モデル（意味正本）が保持する。
  数値が変化しただけで戦略を自動変更してはならない（SR-10 の複数根拠要件）。
- **SR-16 一周の判定**: 上流戦略インフィニティループが「一周した」と判定するのは、
  市場の捉え方・セグメント・問題定義・未充足価値・カテゴリー・比較軸・価値提案・ポジショニング・
  戦略仮説・戦略判断の**いずれかが strategy_revision を経て更新されたとき**である。
  行動計画の微修正だけの回転は一周と数えない。

## 2. 上流工程の成果物契約（工程名は既存のまま、出力を機械可読モデルへ固定）

| 工程 | 出力モデル（json/strategy/ の schema が正本） | SR |
|---|---|---|
| リサーチ | `market_observation`（事実のみ。AI 解釈の混在禁止） | SR-02 |
| 市場分析 | `market_model`・`segment_context`・`problem_model`（代替行動・制約は segment_context に内包） | SR-03, SR-04 |
| マーケティング戦略 | `value_hypothesis`・`category_definition`・`positioning_hypothesis`・`causal_assumption`・`strategic_choice` | SR-05 |
| 行動計画 | `strategic_brief`（媒体別作業一覧ではなく、下流へ渡す契約） | SR-06 |
| 改善 | `strategy_revision`（どの意味モデルを maintain/refine/pivot/reject/retire するかの明示） | SR-10 |

- **SR-02 観測と解釈の分離**: リサーチ工程の出力は `market_observation` に固定する。観測事実（fact）と
  AI 解釈を同一フィールドへ混在させない。解釈は TLP の `causal_interpretation` /
  revision の `reason` という別フィールド・別レコードでのみ扱う。
- **SR-03 市場分析の出力固定**: 市場分析は観測事実を統合して market_model／segment_context／
  problem_model を生成する。自由 JSON への埋没を禁止し、schema 必須フィールドを欠く成果物は拒否する。
- **SR-04 状況ベースのセグメント（ペルソナ禁止）**: セグメントは時間・空間・状況・制約・進行状態・
  問題の顕在度・既存の代替行動・意思決定条件・利用可能な資源・変化のトリガーを中心に定義する。
  年齢・性別・職業・趣味中心の架空人物ペルソナを正本として導入しない。人口統計属性は補助変数のみ。
  **人口統計属性だけで構成されたセグメントはゲートで拒否する**。
- **SR-05 戦略判断の完全性**: `strategic_choice` は選択した案だけでなく**棄却した選択肢と棄却理由**も保持する
  （schema の `rejected_options` minItems 1）。価値仮説は反証条件（disconfirming_conditions）を必須で持つ。

## 3. 上流→下流の発注契約（strategic_brief）

- **SR-06 brief 発行**: 行動計画工程は `strategic_brief`（digest 付き・有効期間付き・版付き）を発行する。
  brief は strategic_choice → segment_context → value_hypothesis へ trace し、
  期待する認識変化（desired_recognition_change）と計測計画を必ず宣言する。
- **SR-07 brief なし開始不可**: 下流ループ（loop_kind = 'lower'）は有効な strategic_brief なしに
  開始できない。下流 run は brief の ID と digest を保持する（s0-contract §2 の DDL CHECK と
  §3.1 start ガードが正準）。
- **SR-14 媒体役割語彙**: brief の `media_role` は媒体名ではなく戦略上の役割
  （research／discovery／problem-framing／category-education／value-definition／proof／comparison／
  conversion／relationship／retention／community／revenue）で宣言する。語彙は設定可能な管理台帳
  （[json/strategy/media-roles.json](json/strategy/media-roles.json)）を正本とする。

## 4. 下流→上流の還流契約（tactical_learning_packet）と改善

- **SR-08 TLP 生成**: 各下流ループは完了時に `tactical_learning_packet` を生成する。TLP は
  観測された事実／AI による解釈／因果推論／反証可能な仮説の判定／推奨判断を**別フィールドで分離**し、
  loop run・brief digest・evidence へ接続する。
- **SR-09 直接変更禁止**: 下流ループ・媒体コネクタ・計測処理は上流戦略正本を直接更新してはならない。
  還流は TLP の提出のみであり、戦略変更の決定は上流ループが複数の観測・反証・信頼度・時間差を評価して行う
  （DDL の保護トリガと kernel の書込み経路制限が実体。s0-contract §1）。
- **SR-10 revision の根拠規律**: `strategy_revision` は根拠（supporting_evidence_ids）・反証
  （counter_evidence_ids）・信頼度・対象版（target_version）を必須で持つ。
  **単一の計測値だけを根拠とした自動 accept を拒否する**（accepted には支持根拠 2 件以上を要求）。
- **SR-11 append-only 版管理**: 上流正本の上書き・削除を禁止し、変更は `supersedes_id` による
  新バージョン作成のみとする（reject された仮説も履歴として残る）。

## 5. コンテンツの位置づけ

- **SR-13 認識変化資産**: コンテンツを投稿物・集客物としてだけ扱わない。コンテンツ＝市場の問題認識・
  カテゴリー・比較軸・選択基準・価値認識を定義・変化させるマーケティング資産である。
  すべての主要コンテンツ企画（T-PLAN の plan_record）は「定義する問題／変化させる認識／提示する比較軸／
  定義する価値／対象となる戦略仮説」の 5 宣言を必須で持つ
  （[json/strategy/content-plan-contract.json](json/strategy/content-plan-contract.json) が正本）。

## 6. S0 との境界（スコープ拡大禁止）

S0 実装分の SR には受入条件 **AC-SR-01〜06**（[json/strategy/ac-sr.json](json/strategy/ac-sr.json) が
GWT 正本）を付し、検証は STC-I-01〜06、実装先は DU-01/02/10 とする。トレースは
`SR → AC-SR → STC-I → DU/CMP → S0.1 完了ゲート` の一本線で、**STC-I-01〜06 の pytest green を
S0.1 の完了条件に含める**（s0-contract §7）。戦略層は独立した別館ではなく HELIX 本線
（①〜⑥ペア＋CI）に接続される。

- **SR-15 S0 最小集合**: S0 で必須なのは (a) versioned strategic brief をシードできる、
  (b) 下流 run が brief ID と digest を保持する、(c) tactical learning packet を生成できる、
  (d) 下流から上流正本を直接変更できない、(e) 上流モデルの JSON Schema と将来実装契約が確定している —
  の 5 点のみ。市場分析・戦略生成・自動 revision の完全実装は S1 以降の上流戦略スライスで行う。
  S0 構造を壊さず追加できることは、DDL（strategic_briefs／TLP が先行配置済み）と
  戦略層テスト設計（STC）で保証する。S0 の FN 数・媒体数・制作機能は本要件で増やさない。

## 7. ゲートとトレース

本書の要件は fail-close ゲート（G-STRAT-BRIEF／G-STRAT-TRACE／G-SEGMENT-CONTEXT／
G-OBS-INTERPRETATION／G-LEARNING-TRACE／G-NO-DIRECT-STRATEGY-MUTATION／G-REVISION-EVIDENCE／
G-STRATEGY-VERSION／G-MEDIA-ROLE／G-CONTENT-VALUE-DEFINITION／G-STRAT-PAIR）で機械強制される
（台帳: [requirements-gates.md](../governance/requirements-gates.md)。各ゲートは
json/strategy/fixtures/ の invalid fixture を拒否できることを毎 push 検証 = negative test 常設）。

上流トレース: SR-01/12/16 → charter v0.4 §3・BR-A1/A3・P2/P3、SR-02..05 → BR-A3・BR-E1、
SR-06/07/14 → BR-A2・FR-11/14、SR-08..10 → BR-B2/B3・FR-15/22、SR-11 → NFR-2/3・HELIX ratchet、
SR-13 → BR-G1/G2・P5、SR-15 → charter §7 スライス駆動。
