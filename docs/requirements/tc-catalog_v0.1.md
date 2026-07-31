<!-- GENERATED FILE — 編集禁止。正本は docs/requirements/json/verification/tc-contracts.json。再生成 = python3 scripts/render_views.py -->

# テストケース 検証契約カタログ（TC contracts）v0.1

> status: **draft（再降下中）**（2026-08-01 全層再降下 §5 — JSON 内容正本の生成ビュー）
> 全 AC 検証契約と双方向接続（G-TRACE-BIDIR）。状態・DB 差分・証跡・禁止副作用・外部呼出回数を検証。
> 既存 TC-01〜59（verification.json）は履歴として保持。

| TC | kind | AC | 検証する状態 | DB 差分 | 証跡 | 禁止副作用の不在 | 外部呼出 | slice |
|---|---|---|---|---|---|---|---|---|
| TCC-11-1 | normal | AC-11-1 | loop_runs.state = 'running'（started_at 記録） | loop_runs 1 行 UPDATE（pending→running）、state_transitions +1 行（entity_type='loop_run', event='start', guard_result='passed'） | state_transitions 行（遷移証跡 — 同一 transaction でコミット） | 他 loop_run の状態変更・operation_log への追加（状態遷移の記録に operation_log は使わない — §3） | 0 回 | S0 |
| TCC-11-2 | reject | AC-11-2 | loop_runs.state = 'running' のまま（retry_count=0 不変） | state_transitions +1 行（from_state='running', event='start', guard_result='rejected'）のみ。loop_runs 差分なし | state_transitions 拒否行（rejected — 拒否も証跡化 §3） | loop_runs の状態・retry_count の変更、遷移の部分適用 | 0 回 | S0 |
| TCC-11-3 | boundary | AC-11-3 | A='completed' 不変、B='running'（未コミット遷移は transaction ごと消滅） | A: state_transitions +1 行（guard_result='rejected'）。B: 差分なし（部分行が存在しない） | A の拒否行。B は証跡なし（原子性 — 状態と遷移ログの片方だけ残らない） | 終端からの状態変更・state_transitions の部分行（ログだけ残る／状態だけ変わる） | 0 回 | S0 |
| TCC-12-1 | normal | AC-12-1 | tasks.state = 'pending'（未 claim・idempotency_key 付与済み） | tasks +1 行（4 列すべて非 NULL、UNIQUE(loop_run_id, step_key, attempt) 充足） | tasks 行そのもの（発行記録の正本） | author_agent_id == verifier_agent_id の行・同一 (loop_run_id, step_key, attempt) の重複行の生成 | 0 回 | S0 |
| TCC-12-2 | reject | AC-12-2 | T-PUB の tasks 行が存在しない | 差分なし（tasks 0 行増） | なし（発行前拒否 — 外部操作ではないため operation_log 対象外） | tasks への T-PUB 行 INSERT・WP コネクタの呼出し | 0 回 | S0 |
| TCC-12-3 | boundary | AC-12-3 | tasks 1 行のまま（state='pending' 不変） | 差分なし | なし（無副作用の冪等再実行） | tasks への 2 行目 INSERT・attempt の暗黙増加・UNIQUE 制約例外の呼出し側への素通し | 0 回 | S0 |
| TCC-13-1 | normal | AC-13-1 | tasks.state = 'done'（completed_at 記録・retry_count=0 のまま） | tasks 1 行 UPDATE（verifying→done）、state_transitions +1 行（event='verify_pass', guard_result='passed'） | evidence: review_pass（result=PASS・reviewer は author と別 agent） | retry_count の変化・author 自身の principal による PASS 判定 | 0 回 | S0 |
| TCC-13-2 | reject | AC-13-2 | tasks.state = 'verifying' のまま（retry_count=1 不変） | state_transitions +1 行（event='verify_fail', guard_result='rejected'）のみ。tasks 差分なし | state_transitions 拒否行（差戻し理由欠如による rejected） | in_progress への差戻し・retry_count の増加 | 0 回 | S0 |
| TCC-13-3 | boundary | AC-13-3 | tasks.state = 'escalated'（終端）、retry_count=3 | tasks 1 行 UPDATE（verifying→escalated, retry_count 2→3）、state_transitions +1 行（event='verify_fail_exhausted', guard_result='passed'） | state_transitions 行＋tasks.failure_detail（最終差戻し理由） | in_progress への 4 回目の差戻し・retry_count の 2 加算・failed への誤分類 | 0 回 | S0 |
| TCC-14-1 | normal | AC-14-1 | WP sprint = 'active'、X sprint = 'blocked' のまま | sprints 1 行 UPDATE（WP のみ planned→active） | sprints 行の status 変化（列更新が正本 — 遷移ログ対象外） | X sprint 行の変更・他媒体待ち合わせによる開始保留（同期強制） | 0 回 | S1 |
| TCC-14-2 | reject | AC-14-2 | sprint = 'planned'、loop_run = 'pending'（いずれも不変） | sprints 差分なし。state_transitions +1 行（loop_run start の guard_result='rejected'） | state_transitions 拒否行（KPI target 欠如） | sprint の active 化・下位 loop_run の running 化・タスク発行 | 0 回 | S1 |
| TCC-14-3 | boundary | AC-14-3 | A = 'reviewing'、B = 再実行後 'active'（planned/active 以外の中間値なし） | A: 1 行 UPDATE（active→reviewing）。B: kill 分は差分なし → 再実行で 1 行 UPDATE（planned→active） | sprints 行の status 遷移（正本） | reviewing 移行後の A への新規タスク発行・B の状態不定 | 0 回 | S1 |
| TCC-15-1 | normal | AC-15-1 | learnings.status = 'draft'（採否は上位ループ側の判断待ち） | learnings +1 行（sprint_id・source_pair_id の FK 接続・learning_json 有効） | learnings 行（source_pair_id つき — 還流の正本） | strategic_briefs への書込み（下流からの上流正本直接変更 — SR-07 違反） | 0 回 | S1 |
| TCC-15-2 | reject | AC-15-2 | learnings 0 行のまま | 差分なし | なし（生成前拒否） | learnings INSERT・上位キューへの登録・strategic_briefs への書込み | 0 回 | S1 |
| TCC-15-3 | boundary | AC-15-3 | learnings 1 行のまま（status='draft' 不変） | 差分なし | 既存 learnings 行（重複なし） | 同一 source_pair_id の 2 行目 INSERT・summary/learning_json の上書き | 0 回 | S1 |
| TCC-16-1 | normal | AC-16-1 | tasks = 'escalated'、loop_runs = 'escalated'（終端・人の対処待ち） | tasks 1 行 UPDATE（state='escalated', failure_code='playbook_broken'）、loop_runs 1 行 UPDATE、state_transitions +2 行（escalate／fatal_failure、guard_result='passed'） | state_transitions 2 行＋tasks.failure_code（事由コード） | 通知 transport 失敗による遷移の巻き戻し・failed への誤分類・破損 playbook での外部操作継続 | 0 回 | S0 |
| TCC-16-2 | reject | AC-16-2 | A = 'done' 不変、B = 'failed'（escalated ではない） | A: state_transitions +1 行（guard_result='rejected'）。B: tasks 1 行 UPDATE（→failed, failure_code='approval_rejected'）＋state_transitions +1 行（event='non_retryable_failure', passed） | A の拒否行＋B の failure_code・state_transitions 行 | A の状態変更・B の escalated への遷移（rejected の escalate 誤分類）・公開の実行 | 0 回 | S0 |
| TCC-16-3 | boundary | AC-16-3 | 1 回目後 = 待機継続（escalated でない・承認再要求済み）、2 回目後 = tasks = 'escalated' | approvals +2 行（decision='expired'）、tasks 1 行 UPDATE（→escalated）、state_transitions +1 行（event='escalate', guard_result='passed'） | approvals の expired 2 行＋state_transitions 行（再要求系列の証跡） | 1 回目 expired での即時 escalate・expired の failed への誤分類（rejected と混同）・承認なしの公開実行 | 0 回 | S0 |
| TCC-21-1 | normal | AC-21-1 | T-PUB が公開ステップへ進行可能（pair 検証 PASS） | pair_plan_quality 差分なし（既存行を根拠に通過）、operation_log 拒否行なし | なし（正常通過は既存 pair 行が根拠） | pair 行の変更・operation_log への拒否行追加 | 0 回 | S0 |
| TCC-21-2 | reject | AC-21-2 | T-PUB = failed（failure_code = pair 不成立） | state_transitions +1 行（failed 遷移）、operation_log +1 行（拒否）、external_operations 差分なし | operation_log 拒否行（plan_id・理由 = pair 不成立） | WP API 呼出し（external_operations への行追加）・pair_plan_quality への行追加 | 0 回 | S0 |
| TCC-21-3 | boundary | AC-21-3 | 1 回目拒否・2 回目通過。revoked 行は revoked のまま保持（履歴保持） | pair_plan_quality +1 行（新 passed）、operation_log +1 行（1 回目拒否） | operation_log 拒否行（理由 = pair revoked）＋新 review_pass 証跡 | revoked 行の passed への書き戻し・revoked ペアでの外部書込み | 0 回 | S0 |
| TCC-22-1 | normal | AC-22-1 | sprint = completed、pair = passed | pair_kpi_measure +1 行（passed）、sprints 1 行 UPDATE（completed） | pair_kpi_measure 行（成立根拠 = measurement＋evidence FK） | measurement のない状態でのレビュー成立・上位還流 | 0 回 | S1 |
| TCC-22-2 | reject | AC-22-2 | sprint = reviewing のまま（遷移なし） | 差分なし（pair_kpi_measure・learnings とも 0 行のまま） | なし（不成立は状態不変で表現。state_transitions への rejected 記録は sprint 遷移要求時のみ） | レビュー成立イベント発火・learnings への行追加・上位ループへの還流 | 0 回 | S1 |
| TCC-22-3 | boundary | AC-22-3 | 1 回目 = reviewing のまま、2 回目 = completed | 2 回目のみ pair_kpi_measure +1 行・sprints UPDATE | 2 回目の pair_kpi_measure 行（passed） | 空目標での成立（fail-open）・1 回目でのレビュー成立イベント発火 | 0 回 | S1 |
| TCC-23-1 | normal | AC-23-1 | kpi_nodes に 1 行（非有料型） | kpi_nodes +1 行、operation_log 差分なし | なし（正常通過は証跡不要） | operation_log への拒否行の追加 | 0 回 | S0 |
| TCC-23-2 | reject | AC-23-2 | kpi_nodes 空のまま | operation_log +2 行（指標拒否・URL 拒否） | operation_log 拒否行（指標名・URL・理由） | kpi_nodes への行追加・外部への実遷移 | 0 回 | S0 |
| TCC-23-3 | boundary | AC-23-3 | 遷移 0 件許可 | operation_log +1 行（拒否） | operation_log 拒否行（理由 = allowlist 未設定） | URL 許可（fail-open） | 0 回 | S0 |
| TCC-24-1 | normal | AC-24-1 | T-PUB が公開ステップへ進行可能（表記検証 PASS） | operation_log 差分なし | なし（正常通過。審査側 review_pass の checked_items に表記検証結果） | operation_log への拒否行追加・表記なしでの通過 | 0 回 | S1 |
| TCC-24-2 | reject | AC-24-2 | T-PUB = failed（non_retryable_failure） | operation_log +1 行（拒否）、external_operations 差分なし | operation_log 拒否行（commit hash・検出リンク・欠落規則） | WP API 呼出し・表記なし成果物の公開ゲート通過 | 0 回 | S1 |
| TCC-24-3 | boundary | AC-24-3 | 1 回目 = 拒否（判定不能）、2 回目 = 表記有無に応じた通常判定 | operation_log +1 行（1 回目拒否）、config +1 行（リスト設定 — INSERT 履歴） | operation_log 拒否行（理由 = domainlist 未設定） | リスト未設定での通過（fail-open）・展開前 URL のみでの非該当判定 | 0 回 | S1 |
| TCC-25-1 | normal | AC-25-1 | T-REVIEW = done | evidence +1 行（review_pass）、state_transitions +1 行（verify_pass, passed） | review_pass 証跡（result=PASS、checked_items に P5 全 4 項目） | P5 チェックを省略した PASS（checked_items 欠落）の記録 | 0 回 | S1 |
| TCC-25-2 | reject | AC-25-2 | 対象 task = in_progress（retry_count=1） | tasks UPDATE（retry_count+1）、state_transitions +1 行（verify_fail）、verifier の FAIL 理由証跡 +1 行 | 差戻し理由（P5 該当項目名）を含む verifier 証跡 | review_pass 証跡の生成・done への遷移・pair_plan_quality の成立 | 0 回 | S1 |
| TCC-25-3 | boundary | AC-25-3 | 対象 task = escalated（retry_count=3、終端） | tasks UPDATE（escalated）、state_transitions +1 行（verify_fail_exhausted） | 差戻し理由証跡＋state_transitions 行（escalated 遷移） | escalated 後の自動遷移・上限超過後の verify_fail 継続（in_progress への差戻し） | 0 回 | S1 |
| TCC-26-1 | normal | AC-26-1 | 承認後に外部操作実行、task は verifying へ進行可能 | approvals +1 行（approved）、evidence +1 行（approval）、external_operations +1 行 | evidence.kind = approval（decision=approved、binding_subject/operation/at） | 承認要求前・approved 確認前の外部書込み（オートモードによるバイパス） | 0 回 | S1 |
| TCC-26-2 | reject | AC-26-2 | 対象 task = failed（failure_code = 承認却下） | approvals +1 行（rejected）、tasks UPDATE（failed）、state_transitions +1 行、external_operations 差分なし | approvals 行（decision=rejected・responder_ref）＋state_transitions 行 | 外部書込みの実行・escalated への遷移（rejected は escalate に含まない — s0-contract §3.2） | 0 回 | S1 |
| TCC-26-3 | boundary | AC-26-3 | 上限到達前 = waiting 継続、到達後 = escalated（終端） | approvals +3 行（初回＋再要求 2 回、各 expired/pending 履歴）、state_transitions +1 行（escalate） | approvals の全要求履歴＋state_transitions 行（escalate、guard に再要求回数） | expired での即 failed 化・上限到達後の再要求継続・未承認での外部書込み | 0 回 | S1 |
| TCC-27-1 | normal | AC-27-1 | task = in_progress（lease_owner_execution_id = author の execution） | tasks +1 行、state_transitions +1 行（claim, passed） | state_transitions 行（guard_result=passed）＋tasks 行の割当そのもの | verifier execution による lease 取得 | 0 回 | S0 |
| TCC-27-2 | reject | AC-27-2 | (a) 行は作られず、(b) task は pending のまま | (a) 差分なし（rollback）、(b) state_transitions +1 行（claim, rejected） | state_transitions の rejected 行（(b) の claim 拒否） | 同一 agent／同一 principal での in_progress 遷移・lease 取得 | 0 回 | S0 |
| TCC-27-3 | boundary | AC-27-3 | lease_owner_execution_id = author の新 execution、task = in_progress で再開 | tasks UPDATE（lease 列・row_version）、state_transitions +1 行（拒否 rejected） | state_transitions の rejected 行（verifier execution の claim 拒否） | verifier execution への lease 移譲・row_version を経ない lease 上書き | 0 回 | S0 |
| TCC-28-1 | normal | AC-28-1 | T-PLAN = done（終端） | tasks UPDATE（done）、state_transitions +1 行（passed） | 既存 plan_record 証跡（完備集合）＋state_transitions 行 | 証跡未検証での done 化・evidence 行の変更（append-only） | 0 回 | S0 |
| TCC-28-2 | reject | AC-28-2 | T-PUB = verifying のまま（状態・retry_count・証跡すべて不変） | state_transitions +1 行（rejected）のみ | state_transitions の rejected 行（details_json に欠落 kind='approval'） | done への遷移・retry_count の変更・既存 evidence の変更 | 0 回 | S0 |
| TCC-28-3 | boundary | AC-28-3 | 1 回目 = verifying のまま、2 回目 = done | state_transitions +2 行（rejected → passed）、workflows +1 行（新 version）、evidence +1 行（追記） | state_transitions の rejected 行（理由 = 未定義 kind）＋追記された適合証跡 | 未定義 kind の素通し（fail-open）・既存 workflow 行の required_evidence_json の書換え（rename/意味変更禁止 — 新 version で対応） | 0 回 | S0 |
| TCC-31-1 | normal | AC-31-1 | 全必須スロット充足（空き検出 0 件） | business_profiles 1 行 UPDATE（price_range 充填）、evidence +1 行（問診・回答・型検証結果） | 問診レコードと回答の紐付け行＋型検証 PASS の記録 | 未照会スロットへの値の書込み（推測充填）・他プロファイル行の変更 | 0 回 | S1 |
| TCC-31-2 | reject | AC-31-2 | tasks.state = 'pending'（遷移なし） | tasks・business_profiles 差分なし、構造化ログ +1 行（拒否） | 開始拒否ログ（未充足スロット名 = target_customer を含む） | タスクの in_progress 遷移・スロットへの推測値の自動充填 | 0 回 | S1 |
| TCC-31-3 | boundary | AC-31-3 | 質問リスト = 未充足 1 件のみ | 差分なし（再照会前の空き検出時点） | なし（空き検出は読み取りのみ） | 充填済みスロットの再照会・充填済み値の消去や上書き | 0 回 | S1 |
| TCC-32-1 | normal | AC-32-1 | draft 1 件（全値出典つき・未昇格の draft 状態） | draft +1 件、evidence +1 行（operation_log — Web 取得） | draft の出典 URL 列＋取得の operation_log 証跡 | draft の正本への自動昇格・外部への書込み | 0 回 | S1 |
| TCC-32-2 | reject | AC-32-2 | draft に出典あり 1 値のみ（出典なし値 0 件） | draft +1 件（1 値のみ）、構造化ログ +1 行（拒否） | 出典なし値の拒否ログ（値と拒否理由） | 出典なし値の draft・正本への混入 | 0 回 | S1 |
| TCC-32-3 | boundary | AC-32-3 | スロット A 未充足維持、スロット B は境界内出典のみで draft 化 | draft +1 件（スロット B のみ）、構造化ログ +1 行（鮮度拒否） | 鮮度切れ出典の拒否ログ（G-SRC-FRESH） | 空値・鮮度切れ値による draft の充填（fail-open） | 0 回 | S1 |
| TCC-33-1 | normal | AC-33-1 | 有効値 = 5、履歴 2 行（supersedes_config_id が旧行を参照） | config +1 行（INSERT のみ — 旧行の UPDATE なし） | config 履歴行（旧値 3・新値 5・reason） | 既存 config 行の UPDATE/DELETE | 0 回 | S0 |
| TCC-33-2 | reject | AC-33-2 | config 1 行のまま（値 5000 不変） | 差分なし | 構造化ログの拒否行（append-only 違反・reason 欠落） | config 行の値変更・reason なし行の混入 | 0 回 | S0 |
| TCC-33-3 | boundary | AC-33-3 | spend_cap_monthly = 5000（保守的既定値）、unknown_key = 解決拒否 | 差分なし（参照は読み取りのみ） | なし（正常参照）／拒否ログ（unknown_key） | 未定義 key への暗黙値（0・None 等）の返却 | 0 回 | S0 |
| TCC-34-1 | normal | AC-34-1 | business_profiles 2 行、B スコープの brand_plans = 0 件・A スコープ = 1 件 | business_profiles +1 行、他テーブル差分なし | business_profiles の複数行共存（SELECT で確認） | A の行・A 所属データの変更・コードやワークフロー定義の修正の必要 | 0 回 | S1 |
| TCC-34-2 | reject | AC-34-2 | B の brand_plans 行が不変・A へのデータ流出 0 件 | 差分なし、構造化ログ +1 行（越境拒否） | 越境アクセスの拒否ログ（要求スコープ・対象行・理由） | 他プロファイル行の返却・変更（越境参照・越境書込み） | 0 回 | S1 |
| TCC-34-3 | boundary | AC-34-3 | business_profiles 1 行のまま（archived・不変） | 差分なし | 書込み拒否・重複拒否のログ | archived プロファイルへの新規業務行の追加・既存行の上書き登録 | 0 回 | S1 |
| TCC-41-1 | normal | AC-41-1 | 最新 config 行の宣言どおりの経路が返る | config +1 行（経路変更 INSERT）。operation_log 差分なし | なし（正常解決は証跡不要） | コード側分岐による経路決定・operation_log への拒否行追加・外部 HTTP 呼出（0 回） | 0 回 | S0 |
| TCC-41-2 | reject | AC-41-2 | 経路は 1 件も返却されない | operation_log +2 行（未登録拒否・有償経路拒否） | operation_log 拒否行（service・要求経路・理由） | 有償 API への接続試行（外部 HTTP 呼出 0 回）・spend_ledger への行追加 | 0 回 | S0 |
| TCC-41-3 | boundary | AC-41-3 | 両要求とも経路返却 0 件 | operation_log +2 行（破損拒否・経路なし） | operation_log 拒否行（理由 = registry 行破損／fallback なし） | 破損行からの部分的な経路返却（fail-open）・外部 HTTP 呼出（0 回） | 0 回 | S0 |
| TCC-42-1 | normal | AC-42-1 | external_operations 3 行すべて confirmed、playbook は active のまま | external_operations +3 行、operation_log +3 行、playbooks.last_success_at UPDATE | operation_log 行（external_operation_id つき）＋構造化ログの seed=42 と間隔 3 値 | 固定間隔での連続送信（3 間隔が全一致）・範囲外（1 秒未満/5 秒超）の間隔・idempotency key の重複 | 0 回 | S1 |
| TCC-42-2 | reject | AC-42-2 | external_operations に新規 sent/confirmed 行なし | operation_log +2 行（X 拒否・上限拒否）。external_operations 差分なし | operation_log 拒否行（media・理由 = prohibited／daily_cap） | 外部サイトへのブラウザ書込み送信（0 回）・playbooks.last_success_at の更新 | 0 回 | S1 |
| TCC-42-3 | boundary | AC-42-3 | k1 = confirmed、k2 = unknown で対象タスク escalated | external_operations 2 行 UPDATE（confirmed/unknown）、operation_log +2 行（照合結果）、state_transitions +1 行（escalate） | operation_log 行（照合結果・external_operation_id 補完） | 同一 idempotency key の再送（mock 受信カウンタ増加 0）・unknown の confirmed 化 | 0 回 | S1 |
| TCC-43-1 | normal | AC-43-1 | playbook = active（新地図） | playbooks 1 行 UPDATE、operation_log +2 行（検知・再生成成功） | operation_log 行（不一致セレクタ・再生成結果）＋再解析時 screenshot evidence | 再解析中の外部サイトへの書込み（mock 書込み受信 0 回）・2 回目の再生成試行 | 0 回 | S2 |
| TCC-43-2 | reject | AC-43-2 | playbook = broken、task = escalated | playbooks.status UPDATE（broken）、state_transitions +1 行（escalate）、operation_log +2 行（検知・再生成失敗） | operation_log 行（再生成失敗理由）＋escalate 遷移行 | 2 回目以降の自動再生成試行・broken 地図での書込み操作続行・地図の推測書換え | 0 回 | S2 |
| TCC-43-3 | boundary | AC-43-3 | note 行 = active、kdp 行 = retired のまま対象タスク escalated | playbooks 1 行 UPDATE（active）、state_transitions +1 行（retired 側 escalate）、operation_log +2 行以上 | operation_log 行（再開後の再生成試行・retired 拒否） | 中間状態の地図（部分更新）での操作再開・retired 行の自動復活・外部書込み | 0 回 | S2 |
| TCC-44-1 | normal | AC-44-1 | 下書き行・公開行とも confirmed、WP 上で記事 published | external_operations +2 行、operation_log +2 行、evidence +1 行（published_url）、assets +1 行（canonical_url・wp_post_id） | published_url evidence（url・wp_post_id・external_operation_id・asset_id）＋operation_log 2 行 | 下書きと公開の idempotency key 共有・Docker 以外の endpoint への送信・credential の平文ログ出力 | 0 回 | S1 |
| TCC-44-2 | reject | AC-44-2 | external_operations に prepared 行すら作られない（検証は送信前） | operation_log +2 行（ペアなし拒否・本番書込み拒否）。external_operations 差分なし | operation_log 拒否行（理由 = pair 未成立／非 Docker endpoint） | 外部 HTTP 呼出（受信カウンタ 0 のまま）・本番 WP への一切の書込み | 0 回 | S1 |
| TCC-44-3 | boundary | AC-44-3 | k-pub 行 = confirmed、WP 上の公開記事は 1 件のまま | external_operations 1 行 UPDATE（confirmed・response 補完）、evidence +1 行（published_url 補完）、operation_log +1 行 | operation_log 照合行＋published_url evidence（external_operation_id 整合） | 公開 API の再送（mock 受信回数増加 0）・external_operations の重複行・二重公開 | 0 回 | S1 |
| TCC-45-1 | normal | AC-45-1 | 読取り draft 保存済み、書戻し操作 confirmed | external_operations +1 行（confirmed）、operation_log +1 行、draft 保存 +1 行 | operation_log 行（service=notion・external_operation_id・request_fingerprint） | 2,000 字超の単一ブロック送信・3 req/秒超過・ループ判定への Notion 値の混入 | 0 回 | S1 |
| TCC-45-2 | reject | AC-45-2 | 同期 task = failed、loop_run は継続進行 | operation_log +1 行（NotionUnavailable）、state_transitions に同期 task の failed 遷移＋他 task の正常遷移 | operation_log 行（service=notion・理由 = unavailable） | ループ本体の停止・待機（Notion 障害の波及）・障害中の書戻し再送連打 | 0 回 | S1 |
| TCC-45-3 | boundary | AC-45-3 | 境界更新 1 件が draft に反映、k-nt = confirmed | draft 1 行 upsert（重複行なし）、external_operations 1 行 UPDATE、operation_log +1 行 | operation_log 照合行（external_operation_id 補完） | 境界更新の取りこぼし・draft の重複行・書戻しの再送（mock 受信増加 0） | 0 回 | S1 |
| TCC-46-1 | normal | AC-46-1 | approvals = approved・evidence 相互整合、task = 進行再開 | approvals +1 行（pending→approved UPDATE）、evidence +1 行（kind=approval）、state_transitions +2 行（waiting→in_progress 系） | approval evidence（decision=approved・binding 3 項目・approvals.evidence_id 整合） | 応答受領前の公開実行・approvals 行の書換えによる decision 変更 | 0 回 | S0 |
| TCC-46-2 | reject | AC-46-2 | 公開 0 件、rejected 側 task = failed（retry_count 増加なし） | operation_log +1 行（binding 不一致）、approvals 1 行 UPDATE（rejected）、state_transitions +1 行（failed） | operation_log 拒否行（不一致項目の明示）＋approvals rejected 行 | 不一致のままの公開（外部書込み 0 回）・rejected タスクの自動リトライ・escalated への迂回 | 0 回 | S0 |
| TCC-46-3 | boundary | AC-46-3 | expired 側 task = escalated、pending 側 = waiting 継続（要求は 1 件のまま） | approvals は再要求分のみ増加（上限到達で停止）、state_transitions +1 行（escalate）。pending 側 approvals 差分なし | approvals の expired 履歴＋escalate 遷移行（事由 = approval_retry_limit 到達） | 上限超過後の再要求継続（無限待機）・同一 binding の重複 approvals 行・expired の failed 化（rejected と混同） | 0 回 | S0 |
| TCC-47-1 | normal | AC-47-1 | 接続成功・平文検出 0 件 | external_operations/operation_log は操作分のみ（credential 列・平文なし） | operation_log 行（external_operation_id — 秘匿値を含まない） | SQLite・repo・ログ・evidence への平文 credential 書込み（検索ヒット 1 件でも fail） | 0 回 | S0 |
| TCC-47-2 | reject | AC-47-2 | 接続 0 件、ログには伏字（token=***）のみ、書出し元 task = escalated 誘導 | operation_log +2 行（SecretUnavailable・CredentialLeakDetected — いずれも平文なし） | operation_log 検知行（マスク済み — 秘匿値そのものを含まない） | 平文のままのログ永続化・秘匿値なしでの外部接続試行（外部 HTTP 呼出 0 回） | 0 回 | S0 |
| TCC-47-3 | boundary | AC-47-3 | 再投入前 = escalated・接続 0 件、再投入後 = 同一タスクが接続成功 | operation_log +2 行（期限切れ・組合せ拒否）、state_transitions に escalate と再開の遷移 | operation_log 行（理由 = session expired／credential-endpoint mismatch — 平文なし） | 期限切れセッションでの外部送信・テスト credential の本番 endpoint 使用（fail-open）・再投入値の SQLite 保存 | 0 回 | S0 |
| TCC-51-1 | normal | AC-51-1 | assets 1 行（content_hash = 出力 hash、wp_media_id あり） | assets +1 行、evidence +1 行（file_hash）、operation_log +1 行（WP アップ操作）— 2 回目は差分なし | evidence 行（kind=file_hash、value=出力 SHA-256、payload に file_path・algorithm=SHA-256） | 2 回目実行での assets/evidence の行増加・出力 hash の変動・本番 WP への書込み | 0 回 | S0 |
| TCC-51-2 | reject | AC-51-2 | assets 空のまま、WP モックへの書込み呼出 0 回 | operation_log +2 行（未 commit 拒否・接続先拒否）のみ | operation_log 拒否行（理由 = uncommitted source／wp target denied） | assets/evidence への行追加・WP（モック含む）への書込み呼出 | 0 回 | S0 |
| TCC-51-3 | boundary | AC-51-3 | assets 1 行（既存 wp_media_id を参照）、evidence 1 行 | assets +1 行、evidence +1 行（file_hash）— WP への新規アップロード 0 回 | evidence 行（kind=file_hash、value=出力 SHA-256） | 同一実体の二重アップロード・assets の重複行 | 0 回 | S0 |
| TCC-52-1 | normal | AC-52-1 | キャッシュ = v3（hash T3）、出力に #123456 が展開 | operation_log +1 行（取得成功）。業務テーブル差分なし | レンダリング証跡 payload の token_version='v3'・token_hash=T3・stale=false | トークン外の恣意的スタイル値の混入・キャッシュの破壊的更新（temp→rename 以外） | 0 回 | S1 |
| TCC-52-2 | reject | AC-52-2 | レンダリング出力 0 件 | operation_log +1 行（取得失敗・キャッシュなし拒否）のみ | operation_log 拒否行（理由 = token unavailable, no cache） | トークン未適用出力の生成・assets/evidence への登録 | 0 回 | S1 |
| TCC-52-3 | boundary | AC-52-3 | レンダリング成功（v2 トークン適用）、キャッシュは v2 のまま | operation_log +1 行（フォールバック記録） | 証跡 payload の token_version='v2'・stale=true | 破損キャッシュの使用（hash 不一致時の続行）・再試行回数の超過呼出 | 0 回 | S1 |
| TCC-53-1 | normal | AC-53-1 | assets +1 行（asset_type=audio、parent_asset_id=1） | assets +1 行、evidence +1 行（file_hash＋実行記録 payload）— 2 回目は差分なし | evidence payload に入力参照（台本 commit・素材 asset_id）・ツール版数・出力 hash | localhost 以外への TTS 送信・2 回目実行での行増加・SQLite への mp3 実体格納 | 0 回 | S3+ |
| TCC-53-2 | reject | AC-53-2 | assets 差分なし、WP への登録 0 件 | operation_log +2 行（参照拒否・実行失敗）のみ | operation_log 拒否行（理由 = missing asset ref／pipeline failed at encode） | 部分出力（中間 mp4）の assets 登録・WP アップロード | 0 回 | S3+ |
| TCC-53-3 | boundary | AC-53-3 | assets 1 行・evidence 1 行（再実行分のみ） | assets +1 行、evidence +1 行 — 断片由来の行は 0 | evidence 行（kind=file_hash、value=再実行出力の SHA-256） | 前回断片の成果物採用・二重登録 | 0 回 | S3+ |
| TCC-54-1 | normal | AC-54-1 | review_pass 証跡の commit_hash 列 = H1、復元ソースの内容 hash = 証跡化時と一致 | evidence +2 行（commit_hash・review_pass） | evidence（kind=commit_hash、value=H1、payload に repository・paths）／evidence（kind=review_pass、payload に result=PASS・commit_hash=H1・reviewer） | 既存証跡行の UPDATE/DELETE（append-only トリガ違反） | 0 回 | S0 |
| TCC-54-2 | reject | AC-54-2 | review_pass 証跡 0 件のまま | operation_log +1 行（hash 不一致拒否）のみ | operation_log 拒否行（理由 = commit hash mismatch H1≠H2） | H2 での review_pass 記録・既存 commit_hash 証跡の書換え | 0 回 | S0 |
| TCC-54-3 | boundary | AC-54-3 | commit_hash 証跡 = 2 行（40 桁 1・64 桁 1） | evidence +2 行（重複分・不正桁は増えない） | operation_log 行（39 桁の拒否） | 同一 (task, kind, value) の重複行・不正桁数 hash の記録 | 0 回 | S0 |
| TCC-55-1 | normal | AC-55-1 | assets 2 行（A1 と派生行）、系譜クエリ結果 = [派生, A1] | assets +1 行（本文実体列なし・参照のみ） | なし（登録行自体が系譜の正本。公開時の published_url は別 FR） | SQLite への画像バイナリ・本文テキストの格納 | 0 回 | S0 |
| TCC-55-2 | reject | AC-55-2 | assets 差分なし | operation_log +2 行（実体混入拒否・参照不正拒否）のみ | operation_log 拒否行（理由 = content body in metadata／parent not found） | 本文実体を含む行の INSERT・出自なし派生行の作成 | 0 回 | S0 |
| TCC-55-3 | boundary | AC-55-3 | assets 1 行のまま（A1）、循環系譜 0 件 | assets 差分なし、operation_log +1 行（循環拒否） | operation_log 拒否行（理由 = circular lineage） | canonical_url 重複行の作成・循環系譜の成立 | 0 回 | S0 |
| TCC-61-1 | normal | AC-61-1 | kpi_nodes に 5 階層のノードが存在し、全 measurements がノードへ FK 接続 | kpi_nodes +5 行、operation_log 差分なし | なし（正常登録は証跡不要 — 拒否時のみ operation_log） | 戦略正本（brand_plans 等）への書込み・有料指標型の混入 | 0 回 | S0 |
| TCC-61-2 | reject | AC-61-2 | kpi_nodes は seed の行のみ | operation_log +3 行（有料拒否・重複拒否・越境拒否）のみ | operation_log 拒否行（指標型・node_key・理由） | cac/roas/ad_spend 型ノードの成立（アプリ層を迂回した直接 INSERT も DDL CHECK で拒否されること） | 0 回 | S0 |
| TCC-61-3 | boundary | AC-61-3 | N1 は status='archived' で存続、measurements の FK は不変 | kpi_nodes 1 行 UPDATE（status）のみ、行数不変 | なし（構造保護は DDL の領分） | 参照中ノードの物理削除・measurements の孤児化 | 0 回 | S0 |
| TCC-62-1 | normal | AC-62-1 | measurements 10 行（全行 evidence_id が S1 証跡へ FK 接続） | 1 回目: evidence +1 行・measurements +10 行。2 回目: 差分なし | evidence（kind=measurement、value=S1、payload に source・file_hash・period・row_count=10） | 2 回目実行での行重複・証跡なし行の投入・有料指標ノードへの投入 | 0 回 | S0 |
| TCC-62-2 | reject | AC-62-2 | 部分破損: measurements 7 行＋隔離 3 行。全破損: measurements 差分なし | 部分: evidence +1・measurements +7・operation_log +1（隔離記録）。全破損: operation_log +1 のみ | operation_log 行（隔離件数・理由）／取得証跡（部分破損側は投入前に記録済み） | 破損行の measurements 混入・全破損ファイルからの部分コミット | 0 回 | S0 |
| TCC-62-3 | boundary | AC-62-3 | measurements 10 行（再実行分のみ）、空取込は行 0・証跡 1 | 再実行: measurements +10。空取込: evidence +1（value=S2、row_count=0）のみ | evidence（kind=measurement、value=S2、payload.row_count=0） | 5 行だけの部分コミット残留・再実行での 15 行化 | 0 回 | S0 |
| TCC-63-1 | normal | AC-63-1 | 自己完結 HTML 1 ファイル（CSS/JS インライン） | evidence +1 行（dashboard）— 2 回目は差分なし。業務テーブル不変 | evidence（kind=dashboard、value=出力 hash、payload に file_path・file_hash・period_end） | 外部 CDN・外部 URL 参照の混入・業務テーブルへの書込み | 0 回 | S1 |
| TCC-63-2 | reject | AC-63-2 | 出力ファイル 0 件、dashboard 証跡 0 件 | operation_log +1 行（検出・破棄）のみ | operation_log 拒否行（理由 = external reference detected／secret pattern） | 汚染 HTML の出力先残留・汚染成果物の証跡化 | 0 回 | S1 |
| TCC-63-3 | boundary | AC-63-3 | 自己完結 HTML 1 ファイル（空データ表示）、断片 0 件 | evidence +1 行（dashboard）— クラッシュ試行分の証跡は 0 | evidence（kind=dashboard — 成功分のみ） | temp 断片の出力先残留・生成失敗分の証跡化 | 0 回 | S1 |
| TCC-71-1 | normal | AC-71-1 | 25 テーブル＋保護トリガ 6 件（config/evidence/state_transitions × update/delete）存在、verify() = pass | 全 25 テーブル CREATE、schema_version +N 行（migration ごと） | schema_version 行（version・migration 名・checksum・適用者・時刻） | DDL 正本にないテーブル・トリガの生成、FK OFF での使用開始 | 0 回 | S0 |
| TCC-71-2 | reject | AC-71-2 | 使用開始拒否（kernel 起動せず） | 差分なし（拒否後の業務書込み 0 件） | verify() の検証結果ログ（欠落テーブル名 = spend_ledger） | 不完全スキーマへの業務行 INSERT・欠落の黙認（fail-open） | 0 回 | S0 |
| TCC-71-3 | boundary | AC-71-3 | schema_version 行数不変・evidence 値不変 | 差分なし | なし（no-op と拒否のみ） | migration の二重適用・append-only 行の改変 | 0 回 | S0 |
| TCC-72-1 | normal | AC-72-1 | version=2、既存行の行数・hash 一致（破壊なし） | schema_version +1 行、新テーブル CREATE（既存行の変更なし） | schema_version 行（version=2・migration 名・checksum_sha256・applied_by・applied_at） | 既存の列・値・意味の変更（破壊的変更）・rename | 0 回 | S0 |
| TCC-72-2 | reject | AC-72-2 | 昇格停止・DB 不変 | 差分なし | 構造化ログ（checksum 不一致 — 期待値と実測値） | checksum 不一致のままの適用続行・schema_version の書換え | 0 回 | S0 |
| TCC-72-3 | boundary | AC-72-3 | version=1 に復元済み・integrity_check ok | 最終的に差分なし（適用→復元で相殺） | verify() の失敗結果ログ＋復元実施の記録 | verify() fail のままの運転継続・失敗した同一 version の書換え修正 | 0 回 | S0 |
| TCC-73-1 | normal | AC-73-1 | 台帳 1 行・当月累計 300 円 | spend_ledger +1 行 | spend_ledger 行（external_operation_id で operation_log 証跡と紐付く） | 既存台帳行の変更・二重計上 | 0 回 | S1 |
| TCC-73-2 | reject | AC-73-2 | spend_ledger 1 行のまま（不完全行・重複行なし） | 差分なし | 構造化ログの拒否行（欠落フィールド名・重複キー） | 用途不明の支出行の混入・同一操作の二重計上 | 0 回 | S1 |
| TCC-73-3 | boundary | AC-73-3 | 台帳 +2 行（0 円行・復旧行が各 1 行） | spend_ledger +2 行、external_operations 1 行 UPDATE（sent→confirmed） | spend_ledger 行＋照合復旧の operation_log 証跡 | 0 円利用の記録省略・復旧再送での二重計上 | 0 回 | S1 |
| TCC-SR-01-1 | normal | AC-SR-01-1 | upper に TLP 0 件、lower に TLP 1 件、意味モデルは upper 由来のみ | tactical_learning_packets +1 行（lower 分のみ） | TLP 行（lower run 起点） | upper run への TLP 追加・lower からの意味モデル追加 | 0 回 | S1 |
| TCC-SR-01-2 | reject | AC-SR-01-2 | 両 run の状態・学習正本とも提出前のまま | operation_log +2 行（越境拒否 ×2）のみ | operation_log 拒否行（loop_kind・提出型・理由） | 越境成果物の永続化・単一ループへの統合的書込み | 0 回 | S1 |
| TCC-SR-02-1 | normal | AC-SR-02-1 | observation 1 件受理（fact のみ） | observation レコード +1（S1 ストア） | schema 検証 PASS の記録 | 解釈フィールドの自動付加・operation_log への拒否行 | 0 回 | S1 |
| TCC-SR-02-2 | reject | AC-SR-02-2 | observation 未受理 | operation_log +1 行（拒否）のみ | operation_log 拒否行（違反フィールド・理由） | 混在 payload の部分受理・fact の自動書換え | 0 回 | S1 |
| TCC-SR-02-3 | boundary | AC-SR-02-3 | 観測 0 件受理、TLP は正規経路で受理 | operation_log +1 行（判定不能拒否）、tactical_learning_packets +1 行 | operation_log 拒否行（理由 = schema 判定不能） | 判定不能時の受理（fail-open） | 0 回 | S1 |
| TCC-SR-03-1 | normal | AC-SR-03-1 | 3 モデル各 1 版受理 | モデルレコード +3（S1 ストア） | schema 検証 PASS と観測 trace の記録 | 自由 JSON としての受理・trace なし受理 | 0 回 | S1 |
| TCC-SR-03-2 | reject | AC-SR-03-2 | モデル 0 件受理 | operation_log +2 行（拒否）のみ | operation_log 拒否行（欠落フィールド一覧） | 部分受理・自由 JSON の正本混入 | 0 回 | S1 |
| TCC-SR-03-3 | boundary | AC-SR-03-3 | 初回 0 件受理→再投入で 1 版受理 | operation_log +2 行（拒否）、その後モデルレコード +1 | operation_log 拒否行（additionalProperties／根拠欠落） | 未知フィールドの黙認（fail-open） | 0 回 | S1 |
| TCC-SR-04-1 | normal | AC-SR-04-1 | segment 1 件受理 | segment レコード +1（S1 ストア） | schema 検証 PASS の記録 | operation_log への拒否行 | 0 回 | S1 |
| TCC-SR-04-2 | reject | AC-SR-04-2 | segment 0 件受理 | operation_log +1 行（拒否）のみ | operation_log 拒否行（欠落状況フィールド一覧） | ペルソナ型 segment の正本混入 | 0 回 | S1 |
| TCC-SR-04-3 | boundary | AC-SR-04-3 | 前者 0 件・後者 1 件受理 | operation_log +1 行（拒否）、segment レコード +1 | operation_log 拒否行（理由 = 状況フィールド実質未記入） | 空フィールドの記入扱い（fail-open） | 0 回 | S1 |
| TCC-SR-05-1 | normal | AC-SR-05-1 | 2 モデル各 1 版受理 | 戦略モデルレコード +2（S1 ストア） | schema 検証 PASS の記録 | 棄却案・反証条件の欠落したままの受理 | 0 回 | S1 |
| TCC-SR-05-2 | reject | AC-SR-05-2 | 0 件受理 | operation_log +2 行（拒否）のみ | operation_log 拒否行（欠落要素一覧） | 反証不能な仮説の正本混入 | 0 回 | S1 |
| TCC-SR-05-3 | boundary | AC-SR-05-3 | 前者 1 版受理・後者 0 件 | 戦略モデルレコード +1、operation_log +1 行（拒否） | operation_log 拒否行（理由 = 棄却理由空） | 空文字理由の記入扱い | 0 回 | S1 |
| TCC-SR-01 | normal | AC-SR-01 | digest 一致（決定性） | 差分なし（算出は pure） | なし（拒否・算出は証跡対象外） | DB への書込み・brief 行の変更 | 0 回 | S0 |
| TCC-SR-06-1 | reject | AC-SR-06-1 | strategic_briefs 空のまま | operation_log +2 行（拒否）のみ | operation_log 拒否行（欠落・無効理由） | 無効 brief の INSERT・digest の発番 | 0 回 | S0 |
| TCC-SR-06-2 | boundary | AC-SR-06-2 | v1 = superseded・v2 = active、既存 run = completed（v1 digest 保持）、新規 run = v2 参照 | strategic_briefs +1 行（v2）、v1 の status UPDATE のみ | v2 行（supersedes_id = v1）・既存 run の TLP（v1 digest 三者一致） | v1 内容列の変更・既存 run の digest 差替え・新規 run の v1 参照 | 0 回 | S0 |
| TCC-SR-02 | reject | AC-SR-02 | run 未作成 | 差分なし | 拒否の構造化ログ | loop_runs への INSERT | 0 回 | S0 |
| TCC-SR-07-1 | normal | AC-SR-07-1 | run = running（brief id・digest 保持） | loop_runs UPDATE 1 行、state_transitions +1 行（passed） | state_transitions 行（guard_result = passed） | digest の書換え・brief 行の変更 | 0 回 | S0 |
| TCC-SR-07-2 | boundary | AC-SR-07-2 | 2 run 開始成立・1 run 完走（旧 digest 保持） | loop_runs UPDATE ×3、state_transitions +3 行（passed） | state_transitions の passed 行と完走 run の TLP（旧 digest 三者一致） | 境界時刻の拒否側誤判定・実行中 run の digest 差替え・強制中断 | 0 回 | S0 |
| TCC-SR-03 | normal | AC-SR-03 | run 終端＋TLP 1 件 | loop_runs UPDATE 1 行＋tactical_learning_packets INSERT 1 行（同一 tx） | state_transitions 行＋TLP 行 | packet なし終端・二重 packet | 0 回 | S0 |
| TCC-SR-06 | reject | AC-SR-06 | TLP 未挿入 | 差分なし | なし（拒否・算出は証跡対象外） | 不正 packet の INSERT 成功 | 0 回 | S0 |
| TCC-SR-08-1 | reject | AC-SR-08-1 | run = running のまま（遷移未成立）、TLP 0 件 | 差分なし（全 rollback） | なし（transaction 不成立のため証跡も残らない） | 因果解釈つき failure packet の永続化・遷移だけの先行成立 | 0 回 | S0 |
| TCC-SR-08-2 | boundary | AC-SR-08-2 | 1 回目クラッシュ後 = running・TLP 0 件、再実行後 = completed・TLP 1 件 | 最終: loop_runs UPDATE 1 行、tactical_learning_packets +1 行、state_transitions +1 行 | TLP 行（digest 三者一致）と終端の state_transitions 行 | 遷移のみ成立した孤児終端 run・TLP 二重生成 | 0 回 | S0 |
| TCC-SR-04 | reject | AC-SR-04 | 正本無変更 | 差分なし | なし（拒否はトリガ層） | 上流正本の行変更 | 0 回 | S0 |
| TCC-SR-09-1 | normal | AC-SR-09-1 | TLP 1 件・brief 完全不変 | tactical_learning_packets +1 行のみ（brief 差分なし） | TLP 行（evidence_ids で run の証跡へ接続） | strategic_briefs のいかなる列の変更 | 0 回 | S0 |
| TCC-SR-09-2 | boundary | AC-SR-09-2 | TLP 3 件・brief 完全不変（status も active のまま） | tactical_learning_packets +3 行のみ | 3 件の TLP 行（recommended_next_action = request_strategy_review） | 推奨の蓄積による brief の自動 supersede・status 自動遷移 | 0 回 | S0 |
| TCC-SR-10-1 | normal | AC-SR-10-1 | v2 = active・v1 = superseded・revision = accepted | 新版 +1 行、旧版 status UPDATE、revision 記録 +1 | strategy_revision 行（根拠 2 件・反証空配列明示・信頼度・対象版） | 旧版内容列の変更・transaction 分割による中間状態 | 0 回 | S1 |
| TCC-SR-10-2 | reject | AC-SR-10-2 | v1 = active のまま・revision accepted 0 件 | operation_log +2 行（拒否）のみ | operation_log 拒否行（根拠不足／反証未明示） | 単一計測値による自動 accept・新版の先行生成 | 0 回 | S1 |
| TCC-SR-10-3 | boundary | AC-SR-10-3 | 重複 = 拒否、2 件 = v2 生成、maintain = 版不変・記録 1 件 | 新版 +1（2 件ケースのみ）、revision 記録 +2（accept・maintain）、operation_log +1（拒否） | maintain の revision 記録（版遷移なし） | 重複 ID の 2 件扱い・maintain での版生成 | 0 回 | S1 |
| TCC-SR-05 | reject | AC-SR-05 | 全行が実行前と同一 | 差分なし | なし（拒否・算出は証跡対象外） | 1 本でも成功する DML | 0 回 | S0 |
| TCC-SR-11-1 | normal | AC-SR-11-1 | v1 = superseded（内容不変）・v2 = active | strategic_briefs +1 行、v1 の status UPDATE のみ | 版連鎖そのもの（v2.supersedes_id = v1.id） | v1 内容列の変更・v1 の削除 | 0 回 | S0 |
| TCC-SR-11-2 | boundary | AC-SR-11-2 | status・valid_until のみ更新済み、内容列は初期値のまま | 許可 2 列の UPDATE のみ（内容差分なし） | IntegrityError の pytest 捕捉記録（トリガ主体の拒否 — FK 等の別要因でない） | 内容列の部分更新・拒否時の行破損 | 0 回 | S0 |
| TCC-SR-12-1 | normal | AC-SR-12-1 | 計測・TLP 受理、意味正本不変 | measurements +N 行、tactical_learning_packets +1 行（brief 差分なし） | measurements 行（evidence_id 接続）と TLP の metrics 参照 | 計測投入による意味モデル・brief の変更 | 0 回 | S1 |
| TCC-SR-12-2 | reject | AC-SR-12-2 | 意味モデル不変（v1 = active） | operation_log +1 行（拒否）のみ | operation_log 拒否行（理由 = 単一計測値根拠） | KPI 変動による戦略正本の自動更新 | 0 回 | S1 |
| TCC-SR-12-3 | boundary | AC-SR-12-3 | TLP 1 件（異常記録つき）・意味正本不変 | tactical_learning_packets +1 行のみ | TLP 行（anomalies・request_strategy_review） | 急変を契機とした brief の自動 supersede・意味モデル自動更新 | 0 回 | S1 |
| TCC-SR-13-1 | normal | AC-SR-13-1 | 企画承認済み・plan_record 証跡 1 件 | evidence +1 行（plan_record） | evidence 行（payload_json に 5 宣言） | operation_log への拒否行 | 0 回 | S1 |
| TCC-SR-13-2 | reject | AC-SR-13-2 | 企画未承認・plan_record 0 件 | operation_log +1 行（拒否）のみ | operation_log 拒否行（欠落キー = recognition_change） | 宣言なし企画の主要企画としての承認 | 0 回 | S1 |
| TCC-SR-13-3 | boundary | AC-SR-13-3 | 初回 2 件拒否→補完後 1 件承認 | operation_log +2 行（拒否）、その後 evidence +1 行 | operation_log 拒否行（空値／参照不整合） | 空値の宣言扱い（fail-open） | 0 回 | S1 |
| TCC-SR-14-1 | normal | AC-SR-14-1 | brief 1 行発行（media_role = problem-framing） | strategic_briefs +1 行 | brief 行そのもの（役割語彙保存） | operation_log への拒否行 | 0 回 | S1 |
| TCC-SR-14-2 | reject | AC-SR-14-2 | brief 0 件発行 | operation_log +2 行（拒否）のみ | operation_log 拒否行（宣言値・台帳版） | 媒体名の media_role としての保存・揺れの自動正規化 | 0 回 | S1 |
| TCC-SR-14-3 | boundary | AC-SR-14-3 | 欠損時 0 件・復旧後 1 件発行 | operation_log +1 行（拒否）、復旧後 strategic_briefs +1 行 | operation_log 拒否行（理由 = 台帳ロード不能） | 台帳欠損時の全許可（fail-open） | 0 回 | S1 |
| TCC-SR-15-1 | normal | AC-SR-15-1 | STC-I-01〜06 全 green・全ゲート PASS | 差分なし（検証のみ — テスト DB は使い捨て） | CI ログ（pytest green・ゲート PASS） | S0 スコープ外機能（上流生成系）の実装混入 | 0 回 | S0 |
| TCC-SR-15-2 | reject | AC-SR-15-2 | CI 赤・コミット差戻し | 差分なし（検証のみ） | CI ログ（baseline 違反・ゲート名つき） | 分母縮小・スコープ拡大の黙認（fail-open） | 0 回 | S0 |
| TCC-SR-16-1 | normal | AC-SR-16-1 | 一周判定 = True・計数 +1 | ループ計数記録 +1（upper run メタデータ） | accepted revision 行と新版行（supersedes_id 連鎖 — 一周の根拠） | 同一回転の重複計上 | 0 回 | S1 |
| TCC-SR-16-2 | reject | AC-SR-16-2 | 一周判定 = False・計数不変 | ループ計数の差分なし | なし（計上されないことが期待 — revision 記録の不在を確認） | 微修正回転の一周計上（管理ループへの縮退） | 0 回 | S1 |
| TCC-SR-16-3 | boundary | AC-SR-16-3 | False・True（計数 +1）・False | ループ計数 +1（複数更新ケースのみ） | maintain の revision 記録（「見て維持」— 計上されない根拠） | 複数更新の多重計上・判定不能時の一周扱い（fail-open） | 0 回 | S1 |
| TCC-KILL-1 | kill | AC-11-3 | 強制終了時点の遷移が transaction ごと消え、loop_runs は直前の確定状態 | 未コミット遷移の行が存在しない（state_transitions に中間行なし） | なし（中断は証跡を残さない — 再開後の遷移が証跡を残す） | 中間状態の残留・二重遷移 | 0 回 | S0 |
| TCC-KILL-2 | kill | AC-SR-03 | 終端遷移と TLP INSERT が同一 transaction — 中断時は両方とも未適用 | loop_runs 非終端のまま＋TLP 0 件（部分適用なし） | なし | packet なし終端 run の出現（孤児） | 0 回 | S0 |
| TCC-CONFLICT-1 | conflict | AC-11-3 | 同一 run への同時イベントは 1 件のみ成立し、他方は現状態不一致で拒否 | state_transitions は 1 行のみ増加 | 拒否側の構造化ログ | 二重遷移・二重証跡 | 0 回 | S0 |
| TCC-CONFLICT-2 | conflict | AC-SR-06 | 同一 loop_run への 2 件目 TLP INSERT が UNIQUE(loop_run_id) で拒否 | tactical_learning_packets は 1 行のまま | なし | 二重 packet | 0 回 | S0 |
| TCC-RESUME-1 | resume | AC-42-3 | プロセス再起動後、in-flight の external_operations（sent 未確定）が照合され、確定 or 補償に収束 | external_operations の status が pending のまま残らない | operation_log の照合結果行 | 同一操作の二重送信（冪等キー衝突） | 照合 1 回（送信の再実行 0 回） | S1 |
| TCC-RESUME-2 | resume | AC-72-3 | migration が途中失敗しても schema_version は前版のまま（1 版 = 1 transaction） | 部分適用されたテーブル・列が存在しない | migration 失敗の構造化ログ | 半適用スキーマでの起動継続 | 0 回 | S0 |
| TCC-11-4 | reject | AC-11-4 | loop_run は running のまま、brief_id=B1・digest=D1 不変 | 差分なし | 構造化ログの拒否行（run 保持 brief 参照の変更拒否） | loop_runs 行の brief_id/digest 変更・状態遷移の発生 | 0 回 | S0 |
| TCC-12-4 | reject | AC-12-4 | tasks 行なし（発行不成立） | 差分なし | 構造化ログの拒否行（verifier 未割当） | verifier_agent_id NULL の tasks 行の混入 | 0 回 | S0 |
| TCC-13-4 | reject | AC-13-4 | task は verifying のまま（done へ遷移しない） | state_transitions に guard_result = rejected 1 行 | operation_log の拒否行（自己審査 PASS 拒否） | done への遷移・review_pass 証跡の生成 | 0 回 | S0 |
| TCC-27-4 | reject | AC-27-4 | tasks 行なし | 差分なし | なし（DB 層拒否） | verifier NULL 行の混入・CHECK 制約の三値すり抜け | 0 回 | S0 |
| TCC-33-4 | reject | AC-33-4 | config 1 行のまま不変 | 差分なし | なし（DB 層拒否） | 同一 (key, changed_at) の重複行の混入 | 0 回 | S0 |
| TCC-41-4 | reject | AC-41-4 | registry 不変（x の browser 書込み行なし） | operation_log に拒否 1 行 | operation_log の拒否行（BR-M-X-4 理由つき） | x の browser 書込み経路行の混入・後続経路解決での採用 | 0 回 | S0 |
| TCC-46-4 | reject | AC-46-4 | approvals 1 行のまま decision='approved' 不変 | 差分なし | なし（DB 層拒否） | approvals 行の decision 変更・行削除 | 0 回 | S0 |
| TCC-61-4 | reject | AC-61-4 | strategic_briefs 全行不変 | 差分なし | なし（DB 層拒否） | strategic_briefs の変更・KPI 起点の自動 revision 行の生成 | 0 回 | S0 |
| TCC-71-4 | reject | AC-71-4 | loop_runs・tasks とも行数不変 | 差分なし | なし（DB 層拒否） | 参照行の連鎖削除・孤児行の発生 | 0 回 | S0 |
| TCC-SR-08-3 | reject | AC-SR-08-3 | TLP 1 行のまま全列不変 | 差分なし | なし（DB 層拒否） | TLP 行の変更・削除 | 0 回 | S0 |
| TCC-SR-06-3 | boundary | AC-SR-06-3 | 2 digest が相異なり、不一致 digest の run が未作成 | loop_runs 差分なし | 拒否の構造化ログ（digest 不一致） | 異内容への同一 digest 付与・不一致 digest での run 作成 | 0 回 | S0 |
| TCC-13-5 | reject | AC-13-5 | task は verifying のまま | state_transitions 差分なし・tasks 差分なし | 拒否の構造化ログ（理由欠落） | 理由なし差戻しの成立・retry_count の増加 | 0 回 | S0 |
| TCC-16-4 | reject | AC-16-4 | task は in_progress のまま（escalated にならない） | tasks 差分なし | 拒否の構造化ログ（rejected は escalate 対象外） | rejected からの escalated 遷移の成立 | 0 回 | S0 |
| TCC-21-4 | reject | AC-21-4 | 公開未実行 | assets・evidence 差分なし | 拒否の構造化ログ（bypass 不能） | config によるゲート無効化・外部 HTTP 呼出（0 回であること） | 0 回 | S0 |
| TCC-23-4 | reject | AC-23-4 | kpi_nodes に有料指標なし | kpi_nodes 差分なし | 拒否の構造化ログ（解除不能） | config によるゼロ広告費ゲートの無効化 | 0 回 | S0 |
| TCC-28-4 | boundary | AC-28-4 | task は verifying・retry_count=1 のまま | tasks・evidence 差分なし（3 回試行後も同一） | 拒否の構造化ログ 3 件 | retry_count の増加・状態変化・証跡の自動補完 | 0 回 | S0 |
| TCC-33-5 | reject | AC-33-5 | config は既存 1 行のまま | config 差分なし | 拒否の構造化ログ（reason 必須） | reason なし変更行の INSERT | 0 回 | S0 |
| TCC-41-5 | boundary | AC-41-5 | タスク done・層違反 0 | tasks +1 行・registry/workflows/playbooks のみ増加 | タスクの operation_log | kernel・gates への媒体固有コードの混入 | 0 回 | S0 |
| TCC-47-4 | reject | AC-47-4 | 秘密が evidence 本文に存在しない | evidence は 0 行または マスク済み 1 行 | マスク済み証跡（秘密は伏字） | 生の認証情報の evidence・ログへの出力 | 0 回 | S0 |
| TCC-51-4 | reject | AC-51-4 | publish 未実行 | assets・external_operations 差分なし | 拒否の構造化ログ（本番 WP 遮断） | 本番 WP への HTTP 呼出（0 回であること） | 0 回 | S0 |
| TCC-54-4 | boundary | AC-54-4 | 公開未実行 | assets 差分なし | 拒否の構造化ログ（hash 不一致） | 旧 PASS の新版への流用 | 0 回 | S0 |
| TCC-61-5 | reject | AC-61-5 | kpi_nodes に層外ノードなし | kpi_nodes 差分なし | 拒否の構造化ログ（層外） | 層外ノードの INSERT | 0 回 | S0 |
| TCC-62-4 | boundary | AC-62-4 | measurements は 1 回目と同数 | measurements 差分なし（2 回目） | 取込スキップの構造化ログ | 同一 hash の二重投入 | 0 回 | S0 |
| TCC-62-5 | reject | AC-62-5 | measurements 差分なし | measurements 差分なし | 拒否の構造化ログ（証跡必須） | 証跡なし実測の保存 | 0 回 | S0 |
| TCC-72-4 | boundary | AC-72-4 | schema_version は N+1（N の書換えは不成立） | schema_version 行は追記のみ（N の UPDATE なし） | migration 実行ログ | 既存 version 行の UPDATE・後方参照の migration | 0 回 | S0 |
| TCC-SR-06-4 | reject | AC-SR-06-4 | strategic_briefs は 1 件のまま | strategic_briefs 差分なし | 拒否の構造化ログ（supersedes 必須） | supersedes なし改訂の INSERT・旧版の内容変更 | 0 回 | S0 |
| TCC-SR-09-3 | reject | AC-SR-09-3 | 意味モデル正本は無変更 | strategic_briefs 差分なし | なし（拒否はトリガ層） | KPI 変動を契機とする戦略正本の更新 | 0 回 | S0 |
| TCC-SR-11-3 | boundary | AC-SR-11-3 | 3 版すべて存在し連鎖が完全 | 差分なし | なし（拒否はトリガ層） | 中間版の削除・連鎖の切断 | 0 回 | S0 |
| TCC-SR-11-4 | reject | AC-SR-11-4 | 3 版のまま | 差分なし | なし（拒否はトリガ層） | 履歴件数の減少 | 0 回 | S0 |
| TCC-SR-15-3 | boundary | AC-SR-15-3 | S0 部分は同一・追加分のみ増加 | S0 テーブル定義の差分なし | migration 実行ログ | S0 テーブル・トリガの変更や削除 | 0 回 | S0 |
| TCC-SR-15-4 | reject | AC-SR-15-4 | ゲート NG（縮小検出） | 差分なし（検査のみ） | ゲート実行ログ | 縮小・降格の PASS 通過 | 0 回 | S0 |

検証手段（method）の全文は JSON 正本を参照。
