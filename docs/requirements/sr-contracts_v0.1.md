<!-- GENERATED FILE — 編集禁止。正本は docs/requirements/json/strategy/sr-contracts.json。再生成 = python3 scripts/render_views.py -->

# 戦略要件 実行契約（SR contracts） v0.1

> status: **draft（再降下中）**（2026-08-01 全層再降下 §3 — JSON 内容正本の生成ビュー）
> 各 SR に 18 観点の実行契約を必須化。brief／TLP／revision の正準は strategy-learning-contract。

## SR-01 二重ループの責務分離

- **入力**: loop_run 生成要求（loop_kind: upper/lower/micro — cli/kernel）／各ループの成果物提出要求（型付き payload — 上流 = 意味モデル群、下流 = TLP/公開物/計測）
- **出力**: 上流 run: 意味モデル（market_model〜strategic_choice — json/strategy schema 準拠）のみ／下流 run: 公開物・計測・tactical_learning_packets 行のみ／越境提出時: LoopScopeViolation 例外
- **事前条件**: loop_runs.loop_kind が DDL CHECK（upper/lower/micro）で確定している／成果物型と loop_kind の対応表（設計固定）がロード済み
- **事後条件**: 上流 run に紐づく tactical_learning_packets 行が 0 件（TLP は lower のみ — DDL 整合トリガ）／下流 run から意味モデル・strategy_revision の提出が 0 件／両ループの学習正本が交差していない
- **不変条件**: tactical_learning_packets.loop_run_id の run は常に loop_kind = 'lower'（DDL 整合トリガ）／上流の学習対象（市場・価値・選択基準）と下流の学習対象（媒体・表現・運用）を単一 PDCA/OODA/スクラムへ統合する経路が存在しない
- **状態遷移**: なし
- **正常動作**: run 生成時に loop_kind を確定し、成果物提出時に「型 × loop_kind」対応表で照合する。上流 run は意味モデルのみ、下流 run は公開物・計測・TLP のみを受理し、それぞれの学習正本へ書き込む。
- **拒否・異常動作**: 下流 run からの意味モデル・strategy_revision 提出、上流 run からの TLP 提出は LoopScopeViolation を raise し、DB を変更せず operation_log 証跡に拒否理由を記録する（fail-close）。DDL 整合トリガは lower 以外の run への TLP INSERT を常時拒否する。
- **境界動作**: micro run は下流の内部検証ループであり、どちらの学習正本にも直接書かない（親 task 経由のみ）。loop_kind 判定不能（対応表にない型）は拒否側へ倒す。
- **再試行・再開・復旧**: 対応表照合は無状態のため再実行安全。クラッシュ時は提出 transaction ごと消え、越境した中間状態は残らない。再開は loop_runs の現状態から続行。
- **人間判断／escalation**: なし（全自動。責務分離の変更は要件改訂 = PO 承認事項）
- **副作用**: operation_log INSERT（拒否時のみ）
- **冪等性**: 照合は pure（同一入力→同一判定）。拒否ログは提出操作単位で 1 行。
- **証跡**: operation_log の拒否行（loop_kind・提出型・理由）
- **使用テーブル・正本**: r: loop_runs（loop_kind 判定）／r: tactical_learning_packets（lower 限定の整合検査）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 成果物型 × loop_kind 対応表（上流 = 意味モデル、下流 = 公開物/計測/TLP — 変更は要件改訂）
- **trace**: 上流 = charter v0.4 §3 BR-A1 BR-A3 ／ 下流 = AC-SR-01-1 AC-SR-01-2 SCM-06 SCM-07 SCM-08 ／ スライス = S1
- **AC 極性 N/A**: boundary-recovery: 責務分離は構造宣言（型 × loop_kind の静的対応）であり、上限・空・同時実行等の数量的境界と復旧シナリオが定義されない。復旧は各 run の SR-07/08 側 AC が担う。

## SR-02 観測と解釈の分離（market_observation）

- **入力**: リサーチ工程の観測投入要求（market_observation payload — json/strategy schema 準拠）／AI 解釈テキスト（str — TLP.causal_interpretation／revision.reason 側へ振り分け対象）
- **出力**: 受理: market_observation レコード（fact のみ — S1 で永続化、S0 は JSON 正本）／混在検知: ObservationInterpretationMixRejected 例外
- **事前条件**: market_observation の JSON Schema（json/strategy/）が確定・ロード済み／G-OBS-INTERPRETATION の invalid fixture が json/strategy/fixtures/ に存在する
- **事後条件**: 受理された observation の fact フィールドに AI 解釈が混在していない／解釈は tactical_learning_packets.causal_interpretation 又は strategy_revision.reason の別レコードのみに存在する
- **不変条件**: market_observation schema に解釈用フィールドが存在しない（観測 = 事実のみ）／fact と解釈を同一フィールドへ格納する経路が存在しない
- **状態遷移**: なし
- **正常動作**: リサーチ工程の出力を market_observation schema で検証し、fact（観測事実）のみを受理する。解釈は TLP の causal_interpretation／revision の reason へ別レコードとして経路分離する。
- **拒否・異常動作**: schema 非適合（解釈フィールドの付加・必須 fact 欠落）は ObservationInterpretationMixRejected で拒否し、operation_log 証跡に理由を記録する。schema 判定不能（fixture/schema 破損）も拒否側へ倒す（fail-close）。
- **境界動作**: 同一テキストでも別レコード（TLP.causal_interpretation）としての提出は受理する — 分離の単位はフィールド・レコードであり字句ではない。空の fact は必須欠落として拒否。
- **再試行・再開・復旧**: schema 検証は無状態。再実行は同一判定。受理 transaction がクラッシュで消えた場合は再投入で冪等に再受理。
- **人間判断／escalation**: なし（全自動。schema 改訂は要件改訂）
- **副作用**: operation_log INSERT（拒否時）／market_observation レコード追加（S1 — SCM-05）
- **冪等性**: schema 検証は pure。同一 observation の再投入は同一性キーで重複検出（S1 ストア）。
- **証跡**: operation_log の拒否行（違反フィールド・理由）／受理 observation の schema 検証結果
- **使用テーブル・正本**: w: tactical_learning_packets（causal_interpretation — 解釈の正規経路）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: market_observation schema（json/strategy/ — 変更は要件改訂）
- **trace**: 上流 = BR-A3 BR-E1 ／ 下流 = AC-SR-02-1 AC-SR-02-2 AC-SR-02-3 SCM-05 ／ スライス = S1

## SR-03 市場分析の出力固定（3 モデル）

- **入力**: 観測事実の集合（market_observation ID 群）／市場分析工程の生成物（market_model／segment_context／problem_model payload）
- **出力**: 受理: schema 適合の 3 モデルレコード（版付き — S1 永続化）／拒否: ModelSchemaRejected 例外（欠落フィールド一覧つき）
- **事前条件**: market_model／segment_context／problem_model の JSON Schema が json/strategy/ に確定済み／入力の market_observation が受理済み（SR-02 通過）
- **事後条件**: 受理された成果物は 3 schema のいずれかに完全適合している／schema 必須フィールドを欠く成果物・自由 JSON が正本に存在しない
- **不変条件**: 市場分析の出力型は 3 モデルのみ（自由 JSON への埋没禁止）／各モデルは market_observation への trace を保持する
- **状態遷移**: なし
- **正常動作**: 観測事実を統合して market_model／segment_context／problem_model を生成し、各 JSON Schema で必須フィールド完全性を検証してから版付きで受理する。
- **拒否・異常動作**: 必須フィールド欠落・schema 外の型・3 モデル以外の自由 JSON は ModelSchemaRejected で受理を拒否し、欠落フィールド一覧を operation_log 証跡へ記録する。判定不能も拒否側へ倒す。
- **境界動作**: additionalProperties は schema 準拠で拒否（未知フィールドの黙認をしない）。観測 0 件からのモデル生成は根拠欠落として拒否。
- **再試行・再開・復旧**: schema 検証は無状態。生成失敗は入力（観測 ID 群）から再実行可能。受理は版単位で冪等（同一内容 = 同一版）。
- **人間判断／escalation**: なし（全自動。schema 改訂は要件改訂）
- **副作用**: 3 モデルレコードの追加（S1 — SCM-06）／operation_log INSERT（拒否時）
- **冪等性**: 同一入力からの生成は同一版として重複検出（append-only 版管理 — SR-11 と同規律）。
- **証跡**: operation_log の拒否行（欠落フィールド一覧）／受理モデルの schema 検証結果と観測 trace
- **使用テーブル・正本**: なし
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: market_model／segment_context／problem_model schema（json/strategy/）
- **trace**: 上流 = BR-A3 BR-E1 ／ 下流 = AC-SR-03-1 AC-SR-03-2 AC-SR-03-3 SCM-06 ／ スライス = S1

## SR-04 状況ベースのセグメント（ペルソナ禁止）

- **入力**: segment_context payload（時間・空間・状況・制約・進行状態・問題顕在度・代替行動・意思決定条件・資源・変化トリガー）／補助変数としての人口統計属性（任意）
- **出力**: 受理: 状況ベース segment_context レコード／拒否: PersonaSegmentRejected 例外（G-SEGMENT-CONTEXT）
- **事前条件**: segment_context schema が状況フィールドを必須として確定済み／G-SEGMENT-CONTEXT の invalid fixture（人口統計のみ segment）が存在する
- **事後条件**: 受理 segment は状況ベース必須フィールドを 1 つ以上実質保持している／人口統計属性だけで構成された segment が正本に存在しない
- **不変条件**: 人口統計属性は補助変数のみ（segment の定義中心にならない）／架空人物ペルソナ型（年齢・性別・職業・趣味中心）を正本として導入する経路が存在しない
- **状態遷移**: なし
- **正常動作**: segment_context を schema 検証し、状況ベースフィールド（状況・制約・代替行動・意思決定条件等）が実質記入されていることを確認して受理する。人口統計は補助フィールドとして併記可。
- **拒否・異常動作**: 状況フィールドが全て空・欠落で人口統計属性のみの segment は PersonaSegmentRejected（G-SEGMENT-CONTEXT）で拒否し、operation_log 証跡へ記録する。判定不能は拒否。
- **境界動作**: 人口統計＋状況の混在は受理（人口統計が補助である限り）。状況フィールドが空文字・空配列のみの場合は「実質未記入」として人口統計のみと同等に拒否。
- **再試行・再開・復旧**: ゲートは無状態（判定のみ）。再実行は同一判定。修正後の segment は新版として再投入。
- **人間判断／escalation**: なし（全自動。状況フィールド定義の変更は要件改訂）
- **副作用**: operation_log INSERT（拒否時）／segment_context レコード追加（S1）
- **冪等性**: 判定は pure。同一 payload の再投入は同一判定・同一版。
- **証跡**: operation_log の拒否行（欠落した状況フィールド一覧）
- **使用テーブル・正本**: なし
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: segment_context schema の状況ベース必須フィールド集合（json/strategy/）
- **trace**: 上流 = BR-A3 BR-E1 ／ 下流 = AC-SR-04-1 AC-SR-04-2 AC-SR-04-3 SCM-06 ／ スライス = S1

## SR-05 戦略判断の完全性（棄却案・反証条件）

- **入力**: strategic_choice payload（選択案＋rejected_options＋棄却理由）／value_hypothesis payload（disconfirming_conditions 必須）／category_definition／positioning_hypothesis／causal_assumption payload
- **出力**: 受理: 5 種の戦略モデルレコード（版付き）／拒否: IncompleteStrategyRejected 例外（欠落要素つき）
- **事前条件**: strategic_choice schema の rejected_options が minItems 1 で確定済み／value_hypothesis schema の disconfirming_conditions が必須で確定済み
- **事後条件**: 受理された strategic_choice は棄却案 1 件以上と各棄却理由を保持している／受理された value_hypothesis は反証条件を保持している
- **不変条件**: 棄却案・棄却理由なしの strategic_choice が正本に存在しない／反証条件なしの value_hypothesis が正本に存在しない（反証不能な仮説の禁止）
- **状態遷移**: なし
- **正常動作**: マーケティング戦略工程の出力（VH/CAT/POS/CA/SC）を各 schema で検証し、strategic_choice は rejected_options（棄却理由つき）を、value_hypothesis は disconfirming_conditions を必須確認して版付きで受理する。
- **拒否・異常動作**: rejected_options 空・棄却理由欠落・disconfirming_conditions 欠落は IncompleteStrategyRejected で拒否し、operation_log 証跡へ欠落要素を記録する。schema 判定不能も拒否。
- **境界動作**: rejected_options ちょうど 1 件（minItems 境界）は受理。棄却理由が空文字の場合は欠落と同等に拒否。反証条件が「なし」と明記された仮説は反証不能として拒否。
- **再試行・再開・復旧**: schema 検証は無状態。欠落補完後は新版として再投入（append-only — SR-11）。
- **人間判断／escalation**: なし（検証は全自動。戦略内容そのものの妥当性判断は上流ループの改善工程 = SR-10 側）
- **副作用**: 5 種戦略モデルレコードの追加（S1 — SCM-07）／operation_log INSERT（拒否時）
- **冪等性**: 同一 payload は同一版として重複検出。判定は pure。
- **証跡**: operation_log の拒否行（欠落要素一覧）／受理モデルの schema 検証結果
- **使用テーブル・正本**: なし
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: strategic_choice schema（rejected_options minItems 1）／value_hypothesis schema（disconfirming_conditions 必須）
- **trace**: 上流 = BR-A3 BR-E1 ／ 下流 = AC-SR-05-1 AC-SR-05-2 AC-SR-05-3 SCM-07 ／ スライス = S1

## SR-06 strategic_brief 発行（digest・版・有効期間）

- **入力**: brief draft（strategic_choice_id／segment_context_id／value_hypothesis_id・認識変化・戦術目標・media_role・メッセージ仮説・禁止パターン・計測計画・valid_from/valid_until）／発行コマンド（S0 はシードコマンド — cli 経由）
- **出力**: strategic_briefs 行（version・digest・status = active）／拒否時: BriefSchemaRejected 例外（欠落・無効理由つき）
- **事前条件**: DB マイグレーション適用済み（strategic_briefs テーブル・保護トリガ存在 — DU-10/11）／media_role が media-roles.json 台帳の語彙である（SR-14）／計測計画が「何を観測すれば仮説を判定できるか」を宣言している（KPI 目標値の割当だけでは無効）
- **事後条件**: strategic_briefs に version ≥ 1・UNIQUE(brief_key, version) の 1 行が INSERT されている／digest = 正準化 JSON（キー昇順・(",",":")・UTF-8/NFC・digest/status/created_at 除外）の SHA-256 64 桁で保存されている／strategic_choice_id → segment_context_id → value_hypothesis_id の trace 3 列が非 NULL
- **不変条件**: 同一内容の brief は常に同一 digest を得る（決定性 — キー順・空白差で不変）／brief の内容列は発行後 UPDATE 不可（strategic_briefs_no_update トリガ）／改訂は supersedes_id による新版 INSERT のみ
- **状態遷移**: テーブル列: strategic_briefs.status: draft→active（発行）、active→superseded（新版発行時 — status 列のみ遷移可）、active→retired
- **正常動作**: brief draft を schema・trace・計測計画の実質性で検証 → 正準化 JSON の SHA-256 で digest を算出 → version・digest・status = active で strategic_briefs へ INSERT する（1 発行 = 1 transaction）。
- **拒否・異常動作**: trace ID 欠落・media_role 台帳外・計測計画が KPI 目標値だけ・schema 非適合は BriefSchemaRejected で INSERT せず operation_log に理由を記録する（fail-close）。digest 長 64 以外は DDL CHECK でも拒否。
- **境界動作**: valid_until NULL は無期限として有効。supersedes による新版発行時、旧版は superseded へ遷移し、旧版に紐づく実行中 run は完走を許すが新規 run は新版のみ参照する。同一 (brief_key, version) の再 INSERT は UNIQUE 制約で拒否。
- **再試行・再開・復旧**: 発行 transaction がクラッシュで消えた場合は再発行で同一 digest の行を得る（決定性）。シードコマンドの再実行は UNIQUE(brief_key, version) で重複検出。
- **人間判断／escalation**: S0 の brief 内容は人間（PO）がシードとして与える。発行処理・digest 算出は全自動。
- **副作用**: strategic_briefs INSERT／旧版 status UPDATE（superseded — 新版発行時のみ）／operation_log INSERT（拒否時）
- **冪等性**: digest 決定性により同一内容の再発行は同一 digest。UNIQUE(brief_key, version) が二重発行を検出。
- **証跡**: strategic_briefs 行そのもの（digest・版が証跡）／operation_log の拒否行
- **使用テーブル・正本**: w: strategic_briefs／w: evidence（operation_log 系拒否・操作証跡）（拒否時）／r: config（シード投入時の検証設定）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: digest 正準化規則（キー昇順・(",",":")・UTF-8/NFC・digest/status/created_at 除外 — strategy-learning-contract §1 2bis）／media-roles.json 台帳（S0 は JSON 正本）
- **trace**: 上流 = BR-A2 REQ-050 ／ 下流 = AC-SR-01 AC-SR-06-1 AC-SR-06-2 AC-SR-06-3 AC-SR-06-4 AC-SR-06-5 SCM-02 ／ スライス = S0

## SR-07 brief なし下流開始不可（開始ガード）

- **入力**: 下流 loop_run の start イベント（loop_kind = 'lower'）／参照 brief の id と digest（loop_runs.strategic_brief_id／strategic_brief_digest）／現在時刻（Clock 注入 — 有効期間判定）
- **出力**: 成立時: running へ遷移した loop_runs 行（brief id・digest を固定保持）／拒否時: GateRejected 例外＋state_transitions の guard_result = rejected 行
- **事前条件**: strategic_briefs テーブルと DDL CHECK（lower は brief_id・digest 非 NULL）が適用済み／遷移表の start ガード（有効 brief: status = active・digest 一致・valid_from ≤ now ≤ valid_until）がロード済み
- **事後条件**: 開始した lower run は strategic_brief_id と strategic_brief_digest（64 桁）を保持している／run の digest = 参照 brief の digest（同一性検証可能）／拒否時は loop_runs の状態が変化していない
- **不変条件**: loop_kind = 'lower' で brief_id 又は digest が NULL の行は存在しない（DDL CHECK）／run 保持の digest は run 全期間で不変（brief 内容の同一性検証を可能にする）
- **状態遷移**: loop_runs: pending→running（start — ガード: 有効 strategic_brief の保持。s0-contract §3.1）
- **正常動作**: start イベント受領 → 参照 brief を SELECT し status = active・digest 一致・有効期間内（valid_until NULL は無期限）を検証 → 成立なら loop_runs を running へ UPDATE し brief id・digest を固定保持、state_transitions へ passed 行を INSERT（同一 transaction）。
- **拒否・異常動作**: brief なし・status = superseded/retired/draft・有効期間外・digest 不一致の各状態は GateRejected で開始を拒否し、state_transitions に guard_result = rejected で記録する。DB の業務状態は変更しない（fail-close — DDL CHECK と validate_strategic_brief の二重防御）。
- **境界動作**: valid_until = now ちょうどは有効（≤ 判定）、now 超過は拒否。valid_until NULL は無期限有効。開始後に brief が superseded になっても実行中 run は完走を許す（digest で旧版同一性を保持）。
- **再試行・再開・復旧**: 拒否は状態を変えないため、brief 投入後の再 start で成立する。クラッシュ時は transaction ごと消え、pending から再 start 可能。
- **人間判断／escalation**: なし（全自動。brief の投入自体は S0 では人間のシード — SR-06）
- **副作用**: loop_runs UPDATE（成立時）／state_transitions INSERT（成立・拒否とも）
- **冪等性**: 同一 run への再 start は現状態不一致（running）で拒否される。拒否の再試行は状態無変更のため安全。
- **証跡**: state_transitions 行（passed/rejected — ガード評価結果）／loop_runs の brief_id・digest 列（保持証跡）
- **使用テーブル・正本**: r: strategic_briefs（有効性検証）／rw: loop_runs／w: state_transitions
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 有効 brief の判定式（status = active ∧ digest 一致 ∧ valid_from ≤ now ≤ valid_until — s0-contract §3.1）
- **trace**: 上流 = BR-A2 REQ-047 ／ 下流 = AC-SR-02 AC-SR-07-1 AC-SR-07-2 SCM-03 ／ スライス = S0

## SR-08 TLP 生成（下流完了時・分離フィールド）

- **入力**: 終端遷移した lower loop_run（completed/failed/escalated/cancelled）／観測・計測・定性シグナル・異常・仮説判定・因果解釈・対立説明・推奨判断の各 payload／evidence_ids（当該 run の証跡参照）
- **出力**: tactical_learning_packets 行 1 件（packet_kind = learning 又は failure）／違反時: IntegrityError（DDL トリガ）又は TlpGenerationRejected 例外
- **事前条件**: 対象 run が loop_kind = 'lower' かつ終端状態に到達している／tactical_learning_packets の UNIQUE(loop_run_id)・整合トリガ・CHECK が適用済み／run が brief id・digest を保持している（SR-07）
- **事後条件**: 終端 lower run にちょうど 1 件の TLP が存在する（UNIQUE ＋ kernel の min-1 契約）／TLP.brief_id = run.brief_id、TLP.digest = run.digest = brief.digest（三者一致）／観測（observations）／計測（metrics）／解釈（causal_interpretation）／判定（hypothesis_result）／推奨（recommended_next_action）が別フィールドに分離格納されている
- **不変条件**: completed = learning（causal_interpretation・hypothesis_result・assessment_reason 必須）、failed/escalated/cancelled = failure（failure_fact・reproduction_conditions・recovery_conditions 必須で causal_interpretation を持てない — DDL CHECK）／TLP は append-only（UPDATE/DELETE 拒否トリガ）／packet を持たない終端 lower run = 0 件（DU-11 verify()／LP-OPS 孤児検査）
- **状態遷移**: loop_runs: running/waiting→completed/failed/escalated/cancelled（終端遷移 — 同一 transaction で TLP INSERT を伴う）
- **正常動作**: lower run の終端遷移時、kernel が同一 transaction で TLP を INSERT する。completed は learning（観測・解釈・判定・推奨を分離充填）、それ以外は failure（failure_fact・再現条件・回復条件を充填し因果解釈は NULL）。confidence（0.0〜1.0）と evidence_ids を必須で持つ。
- **拒否・異常動作**: 非終端 run・upper/micro run への生成、brief_id/digest 不一致、二重 packet、learning/failure の必須フィールド違反（failure への causal_interpretation 混入を含む）は DDL 整合トリガ・UNIQUE・CHECK が IntegrityError で拒否し、transaction 全体を rollback する（終端遷移も成立しない — fail-close）。
- **境界動作**: 観測 0 件で終端した run は failure packet として事実（failure_fact）のみ還流し、因果解釈を捏造しない。cancelled（人の取消）も failure として TLP を残す。metrics/qualitative_signals/anomalies は空配列既定値可。
- **再試行・再開・復旧**: 終端遷移＋TLP は単一 transaction のため、クラッシュ時は両方消え中間状態が残らない。再実行で遷移と packet が揃って 1 回だけ成立。孤児（packet なし終端 lower run）を verify()/ヘルスチェックが検出した場合は escalate。
- **人間判断／escalation**: なし（生成は全自動。TLP の推奨判断は上流への入力であり決定ではない — SR-09）
- **副作用**: tactical_learning_packets INSERT／loop_runs UPDATE（終端遷移）／state_transitions INSERT
- **冪等性**: UNIQUE(loop_run_id) が二重生成を検出。終端遷移済み run への再生成要求は現状態不一致で拒否。
- **証跡**: tactical_learning_packets 行そのもの（evidence_ids で run の証跡へ接続）／state_transitions の終端遷移行
- **使用テーブル・正本**: w: tactical_learning_packets／rw: loop_runs（終端遷移）／w: state_transitions／r: strategic_briefs（digest 三者一致検証）／r: evidence（evidence_ids 参照整合）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: packet_kind 二分規則（completed = learning／failed・escalated・cancelled = failure）／recommended_next_action 語彙（continue/modify_tactic/request_strategy_review/stop — DDL CHECK）
- **trace**: 上流 = BR-B2 BR-B3 REQ-049 ／ 下流 = AC-SR-03 AC-SR-06 AC-SR-08-1 AC-SR-08-2 AC-SR-08-3 SCM-04 ／ スライス = S0

## SR-09 上流正本の直接変更禁止（還流 = TLP 提出のみ）

- **入力**: 下流ループ・媒体コネクタ・計測処理からの書込み要求（対象テーブル・操作種別）／TLP 提出（tactical_learning_packets INSERT — 唯一の還流経路）
- **出力**: TLP 提出: 受理（SR-08 の契約どおり）／上流正本への直接書込み: IntegrityError（保護トリガ）又は WritePathDenied 例外（kernel 経路制限）
- **事前条件**: strategic_briefs の内容列保護トリガ・DELETE 拒否トリガが適用済み／kernel の書込み経路制限（brief 書込みは issue/supersede_strategic_brief の 2 API のみ）が実装済み
- **事後条件**: 下流・コネクタ・計測処理の実行後、strategic_briefs の内容列が変化していない／還流は tactical_learning_packets への INSERT としてのみ記録されている
- **不変条件**: 上流戦略正本の書込み API は issue/supersede_strategic_brief の 2 本のみで、下流・コネクタから到達不能／TLP の recommended_next_action は上流への入力であり、それ自体が戦略正本を変更しない／KPI ツリー（kpi_nodes/measurements）から意味正本への自動書込み経路が存在しない
- **状態遷移**: なし
- **正常動作**: 下流は終端時に TLP を提出するだけで完結する。上流正本の変更は上流ループの改善工程（strategy_revision — SR-10）だけが新版 INSERT で行い、書込みはストア副層・kernel 経由に限定される。
- **拒否・異常動作**: 下流・コネクタ・計測処理からの strategic_briefs への UPDATE/DELETE は保護トリガが IntegrityError で常時拒否し、kernel 外経路の INSERT は WritePathDenied で拒否して operation_log に記録する。request_strategy_review 推奨を含む TLP も正本を変更しない（fail-close）。
- **境界動作**: status/valid_until 列のみの遷移（superseded 化等）は上流 API 経由でのみ許可 — トリガ WHEN 条件の境界。TLP 大量提出（同一 brief への多 run）でも正本は 1 バイトも変わらない。
- **再試行・再開・復旧**: 拒否は DB 無変更のため再実行安全。トリガは接続・プロセスに依存せず DDL として常時有効（クラッシュ後も防御が残る）。
- **人間判断／escalation**: なし（PO でもトリガ・経路制限をバイパスできない。戦略変更は SR-10 の revision 手続きのみ）
- **副作用**: operation_log INSERT（拒否時）／tactical_learning_packets INSERT（正規還流時 — SR-08）
- **冪等性**: 拒否は pure（同一要求→同一拒否）。TLP 提出の冪等性は SR-08 の UNIQUE(loop_run_id) が担う。
- **証跡**: operation_log の拒否行（要求元・対象・操作）／静的検査結果（書込み経路 2 API 限定 — STC-I-06）
- **使用テーブル・正本**: r: strategic_briefs（保護対象）／w: tactical_learning_packets（唯一の還流経路）／w: evidence（operation_log 系拒否・操作証跡）（拒否時）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 書込み許可 API 一覧（issue_strategic_brief／supersede_strategic_brief の 2 本 — 変更は要件改訂）
- **trace**: 上流 = BR-B2 BR-B3 REQ-047 ／ 下流 = AC-SR-04 AC-SR-09-1 AC-SR-09-2 AC-SR-09-3 AC-SR-09-4 SCM-01 SCM-04 ／ スライス = S0

## SR-10 strategy_revision の根拠規律

- **入力**: strategy_revision 提案（target_type・target_id・target_version・revision_type: maintain/refine/pivot/reject/retire）／supporting_evidence_ids（重複禁止）・counter_evidence_ids（評価した反証なしも空配列を明示）・confidence
- **出力**: accepted revision ＋（maintain 以外）new_version_id を持つ新版行・旧版 status 遷移／拒否: RevisionEvidenceRejected 例外（G-REVISION-EVIDENCE）
- **事前条件**: 対象の意味モデルと target_version が正本に存在する／supporting/counter evidence が TLP・観測レコードとして実在する
- **事後条件**: accepted revision は支持根拠 2 件以上（重複 ID なし）・反証明示・信頼度・対象版を保持している／accepted かつ maintain 以外では new_version_id・新版の supersedes_id = target_id・旧版 status 遷移（active→superseded/retired）が単一 transaction で成立している
- **不変条件**: 単一の計測値だけを根拠とした自動 accept が存在しない（支持根拠 ≥2・重複不可）／maintain も明示的 revision として記録される（「見ていない」と「見て維持した」の区別）／counter_evidence_ids は未評価時も空配列で明示される（省略不可）
- **状態遷移**: テーブル列: strategic_briefs.status: active→superseded/retired（revision accepted・maintain 以外 — 新版 INSERT と同一 transaction）
- **正常動作**: 上流の改善工程が TLP・観測・反証・信頼度・時間差を評価して revision を起票 → 支持根拠 ≥2（重複なし）・反証明示・対象版一致を検証 → accepted なら（maintain 以外）新版 INSERT・旧版 status 遷移・revision 記録を単一 transaction で実行する。
- **拒否・異常動作**: 支持根拠 0〜1 件・重複 ID による水増し・counter_evidence_ids 欠落・target_version 不一致・new_version_id 欠落（accepted かつ maintain 以外）は RevisionEvidenceRejected で拒否し、operation_log に理由を記録する（fail-close）。
- **境界動作**: 支持根拠ちょうど 2 件（異なる ID）は accept 可。同一根拠 ID の重複や単一 KPI の 2 期間参照は 2 件扱いしない（uniqueItems）。maintain は new_version_id 不要で revision 記録のみ残す。
- **再試行・再開・復旧**: accepted 処理は単一 transaction のため、クラッシュ時は revision・新版・旧版遷移がすべて消え不整合が残らない。再提案は同一根拠から冪等に再評価。
- **人間判断／escalation**: S1 の revision エンジンは提案まで自動、accept 判断は judge 工程（上流ループ内）。単一計測値による自動 accept は人間でも不可（機械的拒否）。
- **副作用**: strategy_revision 記録の INSERT／新版意味モデル INSERT（accepted・maintain 以外）／旧版 status UPDATE／operation_log INSERT（拒否時）
- **冪等性**: 同一 target_version への accepted revision は版遷移済みのため再適用不可（target_version 不一致で拒否）。提案の再評価は無害。
- **証跡**: strategy_revision 行（根拠・反証・信頼度・対象版）／operation_log の拒否行
- **使用テーブル・正本**: r: tactical_learning_packets（根拠参照）／r: evidence（根拠実在検証）／w: strategic_briefs（affected brief の新版発行 — accepted 後続）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: accepted の最低支持根拠数 = 2（重複不可 — strategy-learning-contract §3。変更は要件改訂）／revision_type 語彙（maintain/refine/pivot/reject/retire）
- **trace**: 上流 = BR-B2 BR-B3 REQ-048 ／ 下流 = AC-SR-10-1 AC-SR-10-2 AC-SR-10-3 SCM-08 ／ スライス = S1

## SR-11 上流正本の append-only 版管理

- **入力**: 上流正本への変更要求（新版 INSERT — supersedes_id つき）／直接 UPDATE/DELETE の試行（違反経路 — 検証対象）
- **出力**: 新版行（supersedes_id が旧版を指す）／UPDATE/DELETE 試行: IntegrityError（'append-only' メッセージ — 保護トリガ）
- **事前条件**: strategic_briefs_no_update/no_delete・tactical_learning_packets_no_update/no_delete トリガが migration 0001 で適用済み／旧版行が存在する（新版発行時）
- **事後条件**: 旧版行が内容不変のまま残存している（reject された仮説も履歴として残る）／新版行の supersedes_id = 旧版 id／UPDATE/DELETE 試行後に行数・内容が変化していない
- **不変条件**: strategic_briefs の内容列と tactical_learning_packets の全列は UPDATE/DELETE 不可（トリガが常時拒否）／版の連鎖（supersedes_id）は途切れず履歴を復元可能／分母の縮小（履歴の削除）が構造的に不可能
- **状態遷移**: テーブル列: strategic_briefs.status: active→superseded/retired（status 列のみ — 内容列は不変）
- **正常動作**: 上流正本の変更はすべて supersedes_id を持つ新版行の INSERT として実行し、旧版は status のみ superseded/retired へ遷移する。reject された仮説も新版（status 付き）として履歴に残す。
- **拒否・異常動作**: 内容列の UPDATE と行 DELETE は保護トリガが IntegrityError（メッセージに 'append-only'）で拒否する。FK 制約等の別要因ではなくトリガ自体が拒否主体であることをテストで区別する（AC-SR-05）。
- **境界動作**: strategic_briefs は status・valid_until のみ UPDATE 可（トリガ WHEN 条件の境界 — それ以外の列は 1 列でも変更で拒否）。TLP は全列不変。supersedes_id の自己参照・循環は FK と版番号の単調増加で防ぐ。
- **再試行・再開・復旧**: トリガは DDL として常駐し、クラッシュ・再起動後も防御が消えない。新版 INSERT の失敗は transaction rollback で旧版に影響しない。
- **人間判断／escalation**: なし（PO でもトリガを迂回した上書き・削除は不可。トリガ変更は migration = 要件改訂）
- **副作用**: 新版行 INSERT／旧版 status UPDATE（許可列のみ）
- **冪等性**: 同一新版の再 INSERT は UNIQUE(brief_key, version) で検出。拒否は DB 無変更のため再実行安全。
- **証跡**: 版連鎖そのもの（supersedes_id 履歴）／拒否テストの IntegrityError 記録（STC-I-01/02）
- **使用テーブル・正本**: rw: strategic_briefs（append-only — 内容列不変）／w: tactical_learning_packets（append-only）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 保護トリガ定義（s0-contract §2 — migration 0001 と等価）
- **trace**: 上流 = NFR-2 NFR-3 REQ-048 ／ 下流 = AC-SR-05 AC-SR-11-1 AC-SR-11-2 AC-SR-11-3 AC-SR-11-4 AC-SR-11-5 AC-SR-11-6 SCM-01 ／ スライス = S0

## SR-12 KPI ツリーの位置づけ（観測背骨・戦略正本にしない）

- **入力**: measurements 投入（WF-MEAS-1 経由）／kpi_nodes の値変動（観測背骨の更新）
- **出力**: kpi_nodes／measurements の更新のみ（意味正本は不変）／数値変動を単独根拠とする戦略変更要求: RevisionEvidenceRejected（SR-10 へ委譲）
- **事前条件**: kpi_nodes／measurements テーブルが適用済み／意味モデル正本（strategic_briefs・S1 の上流モデル群）が KPI テーブルと分離されている
- **事後条件**: 計測投入後、意味モデル正本の行が変化していない／「なぜ発生したか」は TLP の causal_interpretation と意味モデルのみが保持している
- **不変条件**: KPI ツリー（kpi_nodes/measurements）から意味正本への自動書込み経路が存在しない／数値が変化しただけで戦略を自動変更しない（変更は SR-10 の複数根拠 revision のみ）／KPI ツリーは両ループが読む観測背骨として維持される（廃止しない）
- **状態遷移**: なし
- **正常動作**: 計測は kpi_nodes／measurements にのみ記録し、TLP の metrics は KPI ノード参照で記録する（計測の重複定義をしない）。数値の解釈（なぜ）は TLP の causal_interpretation → revision の評価という別経路でのみ意味正本へ届く。
- **拒否・異常動作**: 計測処理からの意味正本書込みは SR-09 の保護トリガ・経路制限が拒否する。単一 KPI 変動のみを根拠とする revision accept は SR-10 の根拠規律（≥2・重複不可）が RevisionEvidenceRejected で拒否する。
- **境界動作**: KPI の急変（閾値超の異常値）でも自動戦略変更は発生せず、TLP の anomalies・recommended_next_action = request_strategy_review としての還流までに留まる（決定は上流）。
- **再試行・再開・復旧**: 計測投入は WF-MEAS-1 の transaction 規律（失敗時全 rollback）に従う。意味正本は計測障害の影響を構造的に受けない。
- **人間判断／escalation**: なし（分離は構造的強制。KPI を見て戦略を再考するのは上流ループの改善工程 = SR-10 の手続き内）
- **副作用**: kpi_nodes／measurements への書込み（観測背骨のみ）
- **冪等性**: measurements は UNIQUE(kpi_node_id, period_start, period_end, dimensions_json) で重複投入を検出。
- **証跡**: measurements 行（evidence_id で取得証跡へ FK 接続）／TLP の metrics（KPI ノード参照）
- **使用テーブル・正本**: r: kpi_nodes／r: measurements／r: tactical_learning_packets（metrics の参照整合）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 「何が起きたか = KPI ツリー／なぜ起きたか = 意味モデル」の分担（charter v0.4 §3 — 変更は要件改訂）
- **trace**: 上流 = charter v0.4 §3 BR-A1 BR-A3 ／ 下流 = AC-SR-12-1 AC-SR-12-2 AC-SR-12-3 SCM-08 ／ スライス = S1

## SR-13 コンテンツ = 認識変化資産（5 宣言必須）

- **入力**: 主要コンテンツ企画（T-PLAN の plan_record payload）／5 宣言（defined_problem・recognition_change・comparison_axes・defined_value・target_hypothesis_ids）
- **出力**: 受理: 5 宣言完備の plan_record 証跡／拒否: ContentValueDeclarationRejected 例外（G-CONTENT-VALUE-DEFINITION）
- **事前条件**: content-plan-contract.json（json/strategy/）が 5 必須キーを定義済み／対象が主要コンテンツ企画（T-PLAN の plan_record）である
- **事後条件**: 承認された主要企画はすべて 5 宣言を実質保持している／どの認識変化も起こさない企画が主要企画として承認されていない
- **不変条件**: コンテンツは投稿物・集客物としてだけ扱われない（認識変化の宣言なしに主要企画になれない）／5 宣言の各値は content-plan-contract の schema に適合する
- **状態遷移**: なし
- **正常動作**: T-PLAN の plan_record payload を content-plan-contract.json で検証し、defined_problem・recognition_change・comparison_axes・defined_value・target_hypothesis_ids の 5 キーが実質記入されている企画のみ承認して evidence（plan_record）へ記録する。
- **拒否・異常動作**: 5 キーのいずれかが欠落・schema 非適合の企画は ContentValueDeclarationRejected（G-CONTENT-VALUE-DEFINITION）で承認を拒否し、operation_log に欠落キーを記録する。集客目的であることは免除理由にならない（fail-close）。
- **境界動作**: 5 キーが存在しても空文字・空配列は「未宣言」として欠落と同等に拒否。target_hypothesis_ids は実在する戦略仮説 ID を最低 1 件参照する。
- **再試行・再開・復旧**: 検証は無状態。宣言補完後の再提出で承認可。S0/S1 前半は docs ゲート（CI）、S1 で実行時強制（SCM-10）へ昇格 — いずれも同一契約。
- **人間判断／escalation**: なし（宣言の存在検証は全自動。企画内容の質は T-REVIEW の別 agent 審査が担う）
- **副作用**: evidence INSERT（kind = plan_record — 承認時）／operation_log INSERT（拒否時）
- **冪等性**: 検証は pure。plan_record は UNIQUE(task_id, kind, value) で重複投入を検出。
- **証跡**: evidence 行（kind = plan_record — 5 宣言を payload_json に保持）／operation_log の拒否行（欠落キー一覧）
- **使用テーブル・正本**: w: evidence（plan_record）／w: evidence（operation_log 系拒否・操作証跡）（拒否時）／r: tasks（T-PLAN 対象判定）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: content-plan-contract.json の 5 必須キー（変更は要件改訂）
- **trace**: 上流 = BR-G1 BR-G2 REQ-051 ／ 下流 = AC-SR-13-1 AC-SR-13-2 AC-SR-13-3 SCM-10 ／ スライス = S1

## SR-14 媒体役割語彙（media_role 台帳）

- **入力**: brief の media_role 宣言（str — strategic_briefs.media_role 列）／媒体役割台帳（json/strategy/media-roles.json — 12 役割語彙）
- **出力**: 受理: 台帳語彙に一致する media_role を持つ brief／拒否: MediaRoleRejected 例外（G-MEDIA-ROLE）
- **事前条件**: media-roles.json 台帳が存在しロード可能である／brief 発行（SR-06）の検証パイプラインに役割検証が組み込まれている
- **事後条件**: 発行済み brief の media_role はすべて台帳語彙（research/discovery/problem-framing/category-education/value-definition/proof/comparison/conversion/relationship/retention/community/revenue）のいずれかである／媒体名（wordpress 等）が media_role として保存されていない
- **不変条件**: 媒体名は役割ではない（役割 = 戦略上の機能宣言）／語彙の正本は管理台帳のみ（コード内ハードコード禁止 — 台帳追加で拡張可能）
- **状態遷移**: なし
- **正常動作**: brief 発行時に media_role を media-roles.json の語彙と照合し、一致のみ通す。台帳は設定可能な管理台帳（S1 で config 経由の追加・変更 — SCM-09）として維持する。
- **拒否・異常動作**: 台帳外の語彙（媒体名・自由記述・typo）は MediaRoleRejected（G-MEDIA-ROLE）で brief 発行を拒否し、operation_log に宣言値と台帳語彙を記録する（fail-close）。
- **境界動作**: 台帳ファイル欠損・空・パース不能時は全宣言を拒否する（deny-by-default）。大文字小文字・前後空白の揺れは正規化せず不一致として拒否（宣言の厳密性を優先）。
- **再試行・再開・復旧**: 照合は無状態。台帳更新（語彙追加）後は次回発行から反映。既発行 brief は digest 固定のため遡及変更されない。
- **人間判断／escalation**: 台帳への語彙追加・変更は PO 承認（S1 の config 経由変更 — 履歴は config の append-only 契約に従う）。照合は全自動。
- **副作用**: operation_log INSERT（拒否時のみ）
- **冪等性**: 照合は pure（同一宣言 × 同一台帳→同一判定）。
- **証跡**: operation_log の拒否行（宣言値・台帳版）／strategic_briefs.media_role 列（受理証跡）
- **使用テーブル・正本**: r: strategic_briefs（media_role 列）／w: evidence（operation_log 系拒否・操作証跡）（拒否時）／r: config（S1 — 台帳変更履歴）
- **外部依存**: なし
- **設定値**: config.media_roles_ledger（S1 — 台帳の DB 化後。S0 は json/strategy/media-roles.json） ／ **固定値**: 初期 12 役割語彙（media-roles.json v0.1）
- **trace**: 上流 = BR-A2 REQ-050 ／ 下流 = AC-SR-14-1 AC-SR-14-2 AC-SR-14-3 SCM-09 ／ スライス = S1

## SR-15 S0 最小集合（スコープ拡大禁止）

- **入力**: S0 実装スコープの検証要求（CI・validate_requirements.py）／S0 の 5 必須点（brief シード／run の id・digest 保持／TLP 生成／直接変更不可／schema・実装契約確定）の実装物
- **出力**: S0.1 完了判定（STC-I-01〜06 pytest green ＋ 5 点の充足）／スコープ逸脱検知: CI fail（ratchet／baseline 違反）
- **事前条件**: strategic_briefs／tactical_learning_packets が DDL に先行配置済み／STC-I-01〜06 が strategy-tests.json に定義済み／baseline.json に分母（FN 数・媒体数）が固定されている
- **事後条件**: S0 で (a) versioned brief シード (b) run の brief id・digest 保持 (c) TLP 生成 (d) 直接変更不可 (e) 12 モデル schema・将来実装契約確定 の 5 点がすべて検証可能である／S0 の FN 数・媒体数・制作機能が本要件で増えていない
- **不変条件**: 市場分析・戦略生成・自動 revision の完全実装は S1 以降（S0 に混入しない）／S0 構造を壊さず S1 を追加できる（DDL 先行配置＋STC が保証）／分母の縮小・confirmed 降格・ゲート削減の禁止（HELIX ratchet）
- **状態遷移**: なし
- **正常動作**: S0.1 の完了条件に STC-I-01〜06 の pytest green を含め、python-ci が実行する。S0 の戦略層実装は 5 必須点に限定し、上流生成系（SCM-05〜10）は schema・契約の確定のみで実装しない。
- **拒否・異常動作**: S0 への生成系実装の混入・FN 数/媒体数の増加・STC-I の未達は CI（python-ci／validate_requirements.py の baseline 照合）が fail-close で検出し、S0.1 完了を認めない。
- **境界動作**: 5 点ちょうどが S0 の上限かつ下限（追加も削減も逸脱）。S1 追加時は既存 S0 テストの回帰 green を前提とする。
- **再試行・再開・復旧**: スコープ検証は無状態（CI 再実行で同一判定）。逸脱検知後は該当コミットの差戻しで復旧。
- **人間判断／escalation**: スコープ変更（5 点の増減）は PO 承認の要件改訂のみ。判定は CI 全自動。
- **副作用**: なし（pure — 検証のみ）
- **冪等性**: CI 判定は pure（同一コミット→同一判定）。
- **証跡**: python-ci の pytest レポート（STC-I-01〜06 green）／validate_requirements.py の baseline 照合ログ
- **使用テーブル・正本**: r: strategic_briefs（先行配置の存在検証）／r: tactical_learning_packets（同上）
- **外部依存**: python-ci（GitHub Actions — pytest 実行）
- **設定値**: なし ／ **固定値**: S0 必須 5 点の一覧（strategy-loop-requirements §6 — 変更は要件改訂）
- **trace**: 上流 = charter v0.4 §7 ／ 下流 = AC-SR-15-1 AC-SR-15-2 AC-SR-15-3 AC-SR-15-4 AC-SR-15-5 AC-SR-15-6 SCM-01 SCM-02 SCM-03 SCM-04 ／ スライス = S0

## SR-16 上流ループ一周の判定

- **入力**: accepted strategy_revision（target_type = 市場の捉え方/セグメント/問題定義/未充足価値/カテゴリー/比較軸/価値提案/ポジショニング/戦略仮説/戦略判断）／上流 run の回転記録（loop_runs — loop_kind = 'upper'）
- **出力**: 一周判定: True（意味モデルのいずれかが revision を経て更新されたとき）／非一周: False（行動計画の微修正だけの回転）
- **事前条件**: strategy_revision の記録（SR-10）が存在する／revision の target_type と意味モデル種別の対応が確定している
- **事後条件**: 一周と判定された回転には、対象意味モデルの新版（supersedes_id つき）を生む accepted revision が 1 件以上対応している／微修正のみの回転が一周として計上されていない
- **不変条件**: 一周の必要十分条件 = 意味モデルのいずれかの revision 経由更新（数値変化・brief 微修正では一周にならない）／一周判定は revision 記録から機械的に導出可能（主観判定を挟まない）
- **状態遷移**: なし
- **正常動作**: 上流 run の完了時に、当該回転中の accepted revision のうち target_type が意味モデル（市場〜戦略判断）であるものを検索し、1 件以上あれば一周と判定してループ計数へ記録する。
- **拒否・異常動作**: 行動計画（brief）の微修正のみ・maintain のみ・revision ゼロの回転は一周と判定しない（判定 False — 例外ではなく計数されないだけ）。判定不能（revision 記録の欠損）は一周としない側へ倒す（fail-close）。
- **境界動作**: maintain revision は「見て維持した」記録であり意味モデルを更新しないため一周に数えない。同一回転で複数モデルが更新されても一周は 1 回（重複計上しない）。
- **再試行・再開・復旧**: 判定は revision 記録からの純関数のため再実行安全。クラッシュ後も記録から同一判定を再導出できる。
- **人間判断／escalation**: なし（判定は revision 記録から機械導出。revision の accept 自体は SR-10 の手続き）
- **副作用**: ループ計数の記録（上流 run のメタデータ — S1 実装）
- **冪等性**: 判定は pure（同一 revision 集合→同一判定）。再計算しても計数は重複しない。
- **証跡**: accepted strategy_revision 行（一周の根拠）／対象意味モデルの新版行（supersedes_id 連鎖）
- **使用テーブル・正本**: r: loop_runs（upper run の回転記録）／r: strategic_briefs（brief 微修正と意味モデル更新の区別）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 一周判定の対象 target_type 一覧（市場の捉え方〜戦略判断 — strategy-loop-requirements §1）
- **trace**: 上流 = charter v0.4 §3 BR-A1 BR-A3 ／ 下流 = AC-SR-16-1 AC-SR-16-2 AC-SR-16-3 SCM-08 ／ スライス = S1
