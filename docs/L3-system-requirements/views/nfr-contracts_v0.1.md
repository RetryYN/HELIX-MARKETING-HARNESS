<!-- GENERATED FILE — 編集禁止。正本は docs/L3-system-requirements/canonical/nonfunctional/nfr-contracts.json。再生成 = python3 scripts/render_views.py -->

# 非機能要件 計測契約（NFR contracts）v0.1

> status: **confirmed**（2026-08-01 PO 承認 — receipt f69c6e989f78）。JSON 内容正本の生成ビュー（全層再降下 §3）
> 各 NFR に測定対象・測定方法・閾値・測定環境・違反時動作・証跡を必須化（G-NFR-MEASURABLE）。

## NFR-1 fail-close（判定不能は通さない）

- **測定対象**: 全ゲート（要件 CI ゲート＋実行時ゲート層）の判定不能時挙動と、ゲート無効化フラグの非存在
- **測定方法**: ①`python3 tools/gates/run_all.py`が docs/L3-system-requirements/verification/fixtures/ の invalid fixture を全て拒否すること（negative test 常設 — 毎 push）。② pytest（tests/gates/ と tests/unit/ の拒否系 — python-ci ジョブ）で allowlist 空・schema 破損・リスト破損等の判定不能入力が全て拒否になることを検証。③`rg -n 'gate.*disable|bypass' src/helix config`を対象パス実在後に実行し、ゲート無効化フラグ・バイパス経路が 0 件であることを検査する。
- **閾値**: invalid fixture の拒否率 100%（1 件でも通過で fail）・ゲート無効化フラグ検出 0 件・判定不能入力の通過 0 件
- **測定環境**: CI（GitHub Actions: python-ci／requirements-gates 相当ジョブ）＋ローカル pytest
- **違反時の動作**: CI 赤で merge を遮断（fail-close）。実行時は該当操作を拒否し、未定義状態遷移は業務状態不変で state_transitions.guard_result=rejected、その他の送信前ゲート拒否は秘匿化済み構造化ログへ記録する。外部送信を開始した操作だけを external_operations と対応する operation_log に記録する。ゲート／遷移表自体の破損は task を event=escalate、親 loop_run を event=fatal_failure でそれぞれ escalated にする。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: validate_requirements.py の実行ログ（negative test 結果）／pytest レポート（拒否系 TC）／拒否の構造化ログ（FN-704。状態遷移拒否は state_transitions の拒否行）（実行時）
- **検証観点**: NFR-1:invalid-rejection NFR-1:disable-path-absence NFR-1:indeterminate-rejection NFR-1:evidence-channel NFR-1:fatal-escalation
- **trace**: 上流 = requirements_v0.1 §3 BR-B4 ／ 下流 = AC-901 TCC-NFR-01

## NFR-2 決定性（同一入力→同一出力）

- **測定対象**: 制作・集計・digest 算出の決定性と、非決定要素（生成 AI・外部サイト）出力の証跡固定
- **測定方法**: ① pytest: 同一 brief draft から issue_strategic_brief を 2 回（別プロセス可）実行し digest（正準化 JSON SHA-256）の完全一致を検証（STC-I-04 = AC-SR-01）。② pytest: 同一 fixture からの制作・集計パイプラインを 2 回実行し出力の SHA-256 一致を比較。③ SQL:`SELECT count(*) FROM evidence WHERE kind IN ('commit_hash','file_hash')`で非決定要素の出力が hash 固定されていることを、対象 task の必須証跡と突合。Clock/Rng は注入（ハードコード禁止）でテスト時に固定する。
- **閾値**: 2 回実行の出力 SHA-256 一致率 100%・digest 決定性テスト green・非決定出力の hash 証跡欠落 0 件
- **測定環境**: CI（python-ci — pytest）＋ローカル
- **違反時の動作**: 不一致検出時は該当テスト red で CI 遮断。実行時の hash 不一致（再計算不一致）は該当 task を failed とし投入しない（WF-MEAS-1 ステップ 2 と同規律）。
- **証跡**: pytest レポート（STC-I-04・二重実行比較）／evidence 行（commit_hash／file_hash — 出力固定）
- **検証観点**: NFR-2:deterministic-hash NFR-2:brief-digest NFR-2:nondeterministic-output-evidence NFR-2:clock-rng-injection
- **trace**: 上流 = requirements_v0.1 §3 BR-B3 ／ 下流 = AC-902 TCC-NFR-02

## NFR-3 再開性（SQLite 状態からの復旧）

- **測定対象**: プロセス強制終了後の全ループ・タスクの再開可能性（s0-contract §3.3 の再開規則）と外部操作の二重送信防止
- **測定方法**: pytest の kill-point テスト（python-ci）: §3.3 の各状態（pending／in_progress 外部操作前・中・後／verifying／waiting／終端）で SIGKILL → 再起動 → 再開規則どおりの継続を検証。最危険 kill point（WP 側成功・ローカル external_operations = 'sent' のままクラッシュ）では再起動後に照合（external operation ID／remote object ID／idempotency key）が走り再送 0 回であることを mock WP の受信回数で検証。SQL:`SELECT count(*) FROM external_operations WHERE status='unknown'`で照合不能の滞留を監視。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **閾値**: 全 kill-point テスト green・最危険 kill point での外部再送 0 回・遷移は書込み後実行（証跡先行）の違反 0 件
- **測定環境**: CI（python-ci — pytest＋mock WP）／E2E は Docker WP
- **違反時の動作**: 再開不能・二重送信検出は該当テスト red で CI 遮断。実行時に sent 照合不能の場合は unknown とし再送せず escalate（fail-close）。
- **証跡**: pytest レポート（kill-point 系）／external_operations 行（prepared→sent→confirmed 遷移）／operation_log 行（照合結果）
- **検証観点**: NFR-3:all-kill-points NFR-3:no-resend NFR-3:evidence-before-transition NFR-3:unknown-escalation
- **trace**: 上流 = requirements_v0.1 §3 BR-A1 ／ 下流 = AC-903 TCC-NFR-03

## NFR-4 秘匿（平文 credential ゼロ）

- **測定対象**: SQLite 全テーブル・構造化ログ・evidence payload・リポジトリへの平文 credential・secret の混入件数
- **測定方法**: ① pytest: SQL:`SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name`で全テーブルを列挙し、`PRAGMA table_info(<quoted_table>)`から得た全列を安全にquoteして走査する。Application Password形式・token接頭辞・既知テストcredential値の検出0件を検証する。② CIのsecret-scanジョブ（gitleaks）でリポジトリとコミット履歴を走査する。③ pytest: operation_log生成時のrequest_fingerprintに本文・credentialを含めないことをfixtureで検証する。credentialは暗号化ストアから実行時注入のみ（環境契約 §6）。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **閾値**: 平文 credential 検出 0 件（DB・ログ・repo とも）・マスキング欠落 0 件
- **測定環境**: CI（python-ci＋secret-scan ジョブ）＋ローカル
- **違反時の動作**: 検出時は CI 赤で merge 遮断。実行時に秘匿違反を検知した tasks.in_progress は event=escalate で tasks.escalated（FR-47）とし、state_transitions.guard_result=passed の1行と、混入credentialの失効・再発行要求を同じ秘匿化済み escalation に記録する。non_retryable_failure→failed へ分類しない。
- **証跡**: secret-scan の CI ログ／pytest レポート（マスキング検証）／operation_log 行（fingerprint のみ — 本文なし）
- **検証観点**: NFR-4:secret-zero NFR-4:masking NFR-4:runtime-failure NFR-4:credential-rotation-escalation
- **trace**: 上流 = BR-F4 requirements_v0.1 §3 ／ 下流 = AC-904 TCC-NFR-04

## NFR-5 可観測性（1 クエリで滞留を答える）

- **測定対象**: 状態遷移・ゲート判定・外部操作の構造化ログ網羅率と、滞留把握クエリの単一性
- **測定方法**: ① pytest: 全遷移（許可・拒否とも）実行後にSQL:`SELECT count(*) FROM state_transitions`=発火event数（guard_result=passed/rejected合計）を検証。② pytest: statusがconfirmed/rejected/unknownの全external_operations行はevidence.external_operation_row_idで対応するoperation_logがexactly 1、全operation_logもexternal_operations行exactly 1へ逆参照することを双方向anti-join＋GROUP BYで検証する。対応組はtask_id・内部row id・effect・policy_category・rate_scope・service・operation・correlation_key・request_hash・request_sequence・resultが一致し、orphanは双方0。providerのexternal_operation_idは任意で同一性キーに使わない。③`config.external_operation.sent_recovery_timeout_sec`はrequired integer > 0、current=300秒。注入UTC Clockから`:recovery_cutoff_utc = clock.utcnow() - 300秒`を算出し、SQL:`SELECT id FROM external_operations WHERE status='sent' AND sent_at < :recovery_cutoff_utc`で期限超過sentを検出する。sentは即時operation_logを要求せず、cutoff直前は検出、cutoff等値と直後は非検出（strict `<`）をassertする。config欠落・型不正・0以下は監視/再開をfail-closeで停止する。④ 滞留把握は次の1 statementを固定する:SQL:`SELECT 'loop_run' AS entity_type, id, state FROM loop_runs WHERE state NOT IN ('completed','failed','escalated','cancelled') UNION ALL SELECT 'task' AS entity_type, id, state FROM tasks WHERE state NOT IN ('done','failed','escalated')`。pytestで全非終端fixtureだけが返ることを検証する。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **閾値**: 未記録の状態遷移・ゲート判定=0件、終端外部操作↔operation_logのorphan/0件/複数件/不一致=0件、有効なrequired integer timeout config（current=300秒）でstrict cutoff超過sent=0件、滞留把握はSQL 1本
- **測定環境**: CI（python-ci — pytest）＋運用時はローカル SQLite への直接クエリ
- **違反時の動作**: 記録欠落・timeout超過sentを検出したテストはredでCI遮断。timeout config欠落・非integer・0以下は安全なcutoffを推測せず監視/再開をfail-close停止。実行時にログINSERTが失敗した遷移はtransactionごとrollbackする。
- **証跡**: state_transitions 行（全遷移）／external_operations終端行とexternal_operation_row_idで双方向exactly-oneに束縛したoperation_log行／pytest レポート（件数突合・滞留クエリ）
- **検証観点**: NFR-5:transition-coverage NFR-5:gate-decision-coverage NFR-5:external-operation-coverage NFR-5:single-query-backlog
- **trace**: 上流 = requirements_v0.1 §3 BR-H3 ／ 下流 = AC-905 TCC-NFR-05

## NFR-6 支出上限（月次キャップ）

- **測定対象**: 月次支出純額（spend_ledgerのcharge−reversal）とconfig.spend_cap_monthlyの比較、仕訳完全性、超過時の有償経路タスク自動停止
- **測定方法**: ① SQL:`SELECT COALESCE(SUM(CASE WHEN entry_type='charge' THEN amount_minor ELSE -amount_minor END),0) FROM spend_ledger WHERE currency='JPY' AND occurred_at >= :month_start_utc AND occurred_at < :next_month_start_utc`でUTC半開区間の既支出純額を求め、`既支出純額 + requested_amount_minor <= config.spend_cap_monthly`を開始ガードとする。② pytest: projected totalが上限直前・一致・1円超過、config欠落の4 fixtureを検証する。超過時は有償tasks.pendingをnon_retryable_failure→failedとして安全な無償代替taskを発行・claimし、config欠落時は有償taskをescalate→escalatedとして無償taskを発行・claimする。③ confirmed有償external_operations(execution_mode='actual', effect='write', policy_category='approved_paid_operation')とentry_type='charge'をexternal_operations.id=spend_ledger.external_operation_row_idで双方向anti-join＋GROUP BYしexactly-one、task_id/service一致、孤児・未記録・重複0を検証する。④ reversalはexternal_operation_row_id IS NULL、reverses_spend_ledger_idが未取消しchargeをUNIQUE参照し、元chargeとamount_minor/service/currency='JPY'一致、同一loop_runの別approved task（task_type='spend_correction'・parent_task_id=元charge.task_id・input_json.original_spend_ledger_id=元charge.id）へDBで構造束縛、1 charge最大1行を検証する。全仕訳はamount_minor>0・JPYのみでUPDATE/DELETE拒否、provider external_operation_idは任意で同一性に使わない。無料・amount=0・手動charge・FXは台帳0行とする。
- **閾値**: 既支出純額 + requested_amount_minor <= config.spend_cap_monthlyのときだけ有償経路を開始（1円でも超過なら開始0件）・無償経路は継続・confirmed approved_paid_operation actual writeとchargeがexternal_operation_row_idで双方向exactly-one・reversalは元chargeと同額/同service/JPYかつ別approved correction task、1 charge最大1行・task/service不一致、孤児、漏れ、重複、不正通貨、UPDATE/DELETE各0件
- **測定環境**: CI（python-ci — pytest＋fixture）／運用時は SQLite 直接クエリ
- **違反時の動作**: 上限超過時は安全な無償代替を自動発行できるため、有償taskをevent=non_retryable_failureでfailedとし、無償taskをclaimして継続する。config欠落時は人の是正が必要なため有償taskをevent=escalateでescalatedとし、無償taskはclaimして継続する。いずれも有償external_operations/spend_ledger差分は0で、成立した遷移はguard_result=passedとする。
- **証跡**: spend_ledger仕訳行（entry_type=charge|reversal、正額JPY、参照整合）／state_transitions 行（上限超過時の有償failed・無償claim、config欠落時の有償escalated・無償claim）／pytest レポート（境界 3 ケース）
- **検証観点**: NFR-6:projected-cap NFR-6:free-route-continuity NFR-6:ledger-completeness NFR-6:reversal-integrity NFR-6:append-only NFR-6:config-missing-failclose
- **trace**: 上流 = BR-F1 requirements_v0.1 §3 ／ 下流 = AC-906 TCC-NFR-06

## NFR-7 レート節度（ランダム化操作間隔）

- **測定対象**: ブラウザ自動化の書き込み・公開系操作の整数秒間隔分布（1〜5秒、両端包含の離散一様乱数）・日次公開上限・乱数シードの記録率
- **測定方法**: ① Rng契約はPython `random.Random(seed).randint(min_sec,max_sec)`（MT19937、両端包含）に固定する。pytestでseed=[0,1,42,4294967295]を各10,000回標本化し、全値がconfig.rate_interval_min_sec〜max_sec内、整数bucketごとのχ²適合度検定p>=0.01、分散>0を検証する。② seed・アルゴリズムID・生成値を秘匿化済み構造化実行ログへ記録し、同一seedの再生列完全一致を検証する。③ writeのexternal_operations.rate_scopeはpolicy registryがservice/endpointから解決するcanonical lowercase keyをNOT NULLで保存しoperation_log payloadと不変同値にする。readはrate_scope=NULLでpayloadにJSON nullキーを必須とする。SQL:`SELECT count(*) FROM external_operations WHERE rate_scope=:rate_scope AND effect='write' AND sent_at >= :day_start_utc AND sent_at < :next_day_start_utc`をUTC半開区間で実行し、必須`config.rate.<rate_scope>.daily_write_cap`以下を検証する。scope/cap欠落・unknown・alias/case不一致はwriteをfail-closeで拒否する。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **閾値**: 全4 seed・各10,000標本で間隔が設定範囲内100%・離散一様性χ² p>=0.01・分散>0・再生列一致100%・write件数がcanonical rate_scope別daily_write_cap以下（scope/config欠落0件、alias/case迂回0件）・seed/algorithm記録率100%
- **測定環境**: CI（python-ci — pytest＋注入 Rng）／E2E は Docker WP のブラウザ自動化
- **違反時の動作**: 上限超過・範囲逸脱を検知した書込み操作は実行前に拒否し、秘匿化済み構造化拒否ログへ記録する（fail-close）。日次上限到達後は公開系 task を pending のまま保持し、親 loop_run を翌日まで waiting とする。seed 未記録は決定性違反としてテスト red。
- **証跡**: 秘匿化済み構造化実行ログ（seed・生成間隔値）／external_operations 行（sent_at — 日次件数の根拠）／pytest レポート（分布・再現性）
- **検証観点**: NFR-7:interval-range NFR-7:uniformity NFR-7:daily-cap NFR-7:canonical-rate-scope NFR-7:seed-recording NFR-7:cap-wait-state
- **trace**: 上流 = BR-F5 requirements_v0.1 §3 ／ 下流 = AC-907 TCC-NFR-07

## NFR-8 保守性（媒体追加 = データ行追加のみ）

- **測定対象**: 新媒体追加時に必要な変更の種別（workflows・playbooks・接続レジストリの行追加のみか、外殻コードの変更を要するか）
- **測定方法**: pytest（python-ci）: テスト開始時にengine/gates/connectors配下のgit追跡ファイルを列挙してSHA-256 mapを固定し、テスト媒体fixtureをworkflows＋playbooks＋接続レジストリ行の追加だけで登録する。dry-run E2E後に同じファイル集合とhash mapが完全一致し、新規製品ファイルも0件であることを検証する（dirty worktreeやcheckout基点に依存しない）。
- **閾値**: 媒体追加時の外殻コード（engine/gates/connectors 本体）diff = 0 行・追加は workflows／playbooks／レジストリ行のみ・dry-run E2E green
- **測定環境**: CI（python-ci — pytest＋dry-run mock）
- **違反時の動作**: コード変更を要した媒体追加は設計違反としてテスト red・差戻し（外殻の拡張が必要な場合は要件・設計改訂を先行させる）。
- **証跡**: pytest レポート（媒体追加 E2E）／workflows／playbooks の追加行／git diff 検査結果
- **検証観点**: NFR-8:data-only-extension NFR-8:dry-run-e2e NFR-8:product-hash-zero-diff NFR-8:registry-row-only
- **trace**: 上流 = BR-F3 requirements_v0.1 §3 ／ 下流 = AC-908 TCC-NFR-08

## NFR-9 法規遵守（ステマ規制・特電法・APPI）

- **測定対象**: PR 表記ゲート（景表法）・オプトイン/配信停止ゲート（特定電子メール法 — MR-HS-3/MR-LINE-2）・リード個人情報の目的内保持の機械検証可能性
- **測定方法**: ① pytest: アフィリエイトリンクを含み PR 表記ブロックのない成果物 fixture が公開ゲートで拒否されること（FR-24 拒否系）。② pytest: オプトイン記録のない宛先への配信・配信停止導線のないメッセージ fixture が配信ゲートで拒否されること。③ 静的検査: 採用配信形態の一覧が機械ゲート化済み形態のみで構成されることを設定（MR 台帳）と突合し、ゲート化できない形態の採用 0 を確認。④ schema検査: リード個人情報の保持列が収集目的宣言と対応することを確認。
- **閾値**: PR 表記なしアフィリエイト成果物の公開 0 件（拒否率 100%）・オプトインなし配信 0 件・機械ゲート化不能な配信形態の採用 0 件
- **測定環境**: CI（python-ci — pytest＋invalid fixture）
- **違反時の動作**: 違反成果物は公開・配信前に拒否し、外部操作を生成せず秘匿化済み構造化拒否ログへ記録する（fail-close）。ゲート化できない配信形態の追加要求は採用拒否（要件改訂でもゲート化が前提）。
- **証跡**: 拒否の構造化ログ（FN-704。状態遷移拒否は state_transitions の拒否行）（PR 表記・オプトイン）／pytest レポート（法規拒否系）／MR 台帳との突合結果
- **検証観点**: NFR-9:pr-label NFR-9:opt-in NFR-9:unsubscribe NFR-9:supported-channel-only NFR-9:pii-purpose
- **trace**: 上流 = requirements_v0.1 §3 MR-HS-3 MR-LINE-2 ／ 下流 = AC-909 TCC-NFR-09

## NFR-10 バックアップ・復旧（日次＋14 世代）

- **測定対象**: SQLite 日次バックアップの実行率・世代保持数・復元可能性（integrity）、ブラウザセッション・WP の復旧手段の存在
- **測定方法**: ① config.backup_generations=N（既定14）を読取り、過去N暦日の各日についてbackup fileとkind=file_hash evidenceを日付で突合して欠落0日を検証する。破損世代は正常保持数から除外し、N正常世代を確保するまでN日より前へ探索する。② pytest: 最新世代を破損させ、正常な前世代へ遡って空環境へrestoreしPRAGMA integrity_check='ok'、foreign_key_check=0行、行数/hash原本一致を検証する。③ 暗号化ブラウザセッション複製を一時プロファイルへrestoreし復号・有効期限検査を行う。④ Docker WPのbackup artifactを一時コンテナへrestoreし、`wp core is-installed`とhealth endpoint成功を検証する。チェックリストだけを合格証拠にしない。
- **閾値**: 直近N日の日次バックアップ欠落0日・破損除外後の正常保持世代 ≥ config.backup_generations=N（既定14）・復元試験の integrity_check/foreign_key_check 成功率100%
- **測定環境**: ローカル（バックアップジョブ＋LP-OPS ヘルスチェック）／復元試験は CI・ローカル pytest
- **違反時の動作**: バックアップ欠落・復元失敗の検知で新規外部書込みタスクを保留し escalate（データ喪失リスク下での書込み継続を禁止 — fail-close）。破損バックアップは世代から除外し前世代へ遡る。
- **証跡**: evidence 行（kind = file_hash — バックアップ hash）／復元試験の pytest レポート／LP-OPS ヘルスチェック記録
- **検証観点**: NFR-10:daily-backup NFR-10:generations NFR-10:db-restore NFR-10:browser-session-copy NFR-10:wp-backup-check NFR-10:write-hold-on-failure
- **trace**: 上流 = requirements_v0.1 §3 RSK-06 ／ 下流 = AC-910 TCC-NFR-10
