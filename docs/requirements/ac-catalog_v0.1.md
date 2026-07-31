<!-- GENERATED FILE — 編集禁止。正本は docs/requirements/json/ac/ac-contracts.json。再生成 = python3 scripts/render_views.py -->

# 受入条件 検証契約カタログ（AC contracts）v0.1

> status: **draft（再降下中）**（2026-08-01 全層再降下 §4 — JSON 内容正本の生成ビュー）
> 各 AC に GWT＋fixture・観測点・期待状態・DB 差分・証跡・禁止副作用・エラー型・対象更新を必須化
> （G-AC-COVERAGE／G-AC-POLARITY）。既存 AC-01〜19（json/ac.json）は履歴として保持。

## FR-11

### AC-11-1（正常）

- **Given**: pending の下位 loop_run（親 upper run が running・sprint の KPI target あり・active な strategic_brief の id/digest を保持） ／ **When**: start イベントを適用する ／ **Then**: ガード成立で running へ遷移し、state_transitions に guard_result = passed の遷移 1 行が追記される
- **fixture**: seed: strategic_briefs 1 行（status='active', digest=D）、sprints 1 行（kpi_target_json={"pv_weekly":500}）、親 loop_runs（loop_kind='upper', state='running'）、対象 loop_runs（loop_kind='lower', state='pending', strategic_brief_digest=D）
- **観測点**: 遷移 API 戻り値／loop_runs.state SELECT／state_transitions SELECT ／ **期待状態**: loop_runs.state = 'running'（started_at 記録）
- **期待 DB 差分**: loop_runs 1 行 UPDATE（pending→running）、state_transitions +1 行（entity_type='loop_run', event='start', guard_result='passed'） ／ **期待証跡**: state_transitions 行（遷移証跡 — 同一 transaction でコミット）
- **禁止副作用**: 他 loop_run の状態変更・operation_log への追加（状態遷移の記録に operation_log は使わない — §3） ／ **エラー型**: なし
- **対象更新**: S0.1（CMP-01 kernel/state.py）／loop_runs start 遷移 ／ **TC**: （割当待ち）

### AC-11-2（拒否）

- **Given**: running 状態の loop_run と、遷移表に無い (状態, イベント) の組（running への start 再送） ／ **When**: 遷移表に合致しないイベントを適用する ／ **Then**: TransitionRejected が raise され、状態・retry_count は変化せず、拒否が guard_result = rejected で記録される
- **fixture**: seed: loop_runs 1 行（state='running', retry_count=0）、適用イベント='start'
- **観測点**: raise される例外型／loop_runs SELECT／state_transitions SELECT ／ **期待状態**: loop_runs.state = 'running' のまま（retry_count=0 不変）
- **期待 DB 差分**: state_transitions +1 行（from_state='running', event='start', guard_result='rejected'）のみ。loop_runs 差分なし ／ **期待証跡**: state_transitions 拒否行（rejected — 拒否も証跡化 §3）
- **禁止副作用**: loop_runs の状態・retry_count の変更、遷移の部分適用 ／ **エラー型**: TransitionRejected
- **対象更新**: S0.1（CMP-01）／未定義遷移の fail-close ／ **TC**: （割当待ち）

### AC-11-3（境界・復旧）

- **Given**: completed（終端）の loop_run A と、遷移 transaction のコミット直前に強制終了した running の loop_run B ／ **When**: A へ cancel イベントを適用し、B は再起動後に状態を読み直して続行する ／ **Then**: 終端 A からの遷移は拒否され、B は中間状態が残らず遷移前の running から §3.3 の規則どおり再開できる
- **fixture**: seed: loop_runs A（state='completed'）、loop_runs B（state='running'）— B への wait 遷移をコミット前 kill で中断
- **観測点**: raise される例外型／再起動後の loop_runs.state・state_transitions 行数 ／ **期待状態**: A='completed' 不変、B='running'（未コミット遷移は transaction ごと消滅）
- **期待 DB 差分**: A: state_transitions +1 行（guard_result='rejected'）。B: 差分なし（部分行が存在しない） ／ **期待証跡**: A の拒否行。B は証跡なし（原子性 — 状態と遷移ログの片方だけ残らない）
- **禁止副作用**: 終端からの状態変更・state_transitions の部分行（ログだけ残る／状態だけ変わる） ／ **エラー型**: TransitionRejected
- **対象更新**: S0.1（CMP-01）／終端保護と §3.3 再開規則 ／ **TC**: （割当待ち）

## FR-12

### AC-12-1（正常）

- **Given**: running の loop_run がステップ 'plan' に到達し、active な WF-WP-1 定義と principal の異なる strategist/critic agent が存在する ／ **When**: タスク発行を実行する ／ **Then**: tasks 行が生成され、ワークフロー ID・担当（author/verifier）・期待成果物型がすべて非 NULL で、author と verifier は別 agent である
- **fixture**: seed: workflows 1 行（workflow_key='WF-WP-1', task_type='T-PLAN', status='active'）、agents 2 行（strategist/critic — principal 相違・active）、loop_runs 1 行（state='running'）
- **観測点**: 発行 API 戻り値／tasks SELECT（workflow_id・author_agent_id・verifier_agent_id・expected_output_kind） ／ **期待状態**: tasks.state = 'pending'（未 claim・idempotency_key 付与済み）
- **期待 DB 差分**: tasks +1 行（4 列すべて非 NULL、UNIQUE(loop_run_id, step_key, attempt) 充足） ／ **期待証跡**: tasks 行そのもの（発行記録の正本）
- **禁止副作用**: author_agent_id == verifier_agent_id の行・同一 (loop_run_id, step_key, attempt) の重複行の生成 ／ **エラー型**: なし
- **対象更新**: S0.1（CMP-02 kernel/orchestrator.py・assigner.py）／タスク発行 ／ **TC**: （割当待ち）

### AC-12-2（拒否）

- **Given**: pair_plan_quality（status = passed）が未成立の action plan に対する T-PUB 発行要求 ／ **When**: T-PUB タスクの発行を実行する ／ **Then**: TaskIssuanceRejected で発行段階で拒否され、tasks に行が作られない（T-R2 — 審査 PASS ペアなしに T-PUB は生成されない）
- **fixture**: seed: action_plans 1 行、pair_plan_quality 0 行、workflows に WF-WP-2（status='active'）、loop_runs 1 行（state='running'）
- **観測点**: raise される例外型／tasks SELECT 件数 ／ **期待状態**: T-PUB の tasks 行が存在しない
- **期待 DB 差分**: 差分なし（tasks 0 行増） ／ **期待証跡**: なし（発行前拒否 — 外部操作ではないため operation_log 対象外）
- **禁止副作用**: tasks への T-PUB 行 INSERT・WP コネクタの呼出し ／ **エラー型**: TaskIssuanceRejected
- **対象更新**: S0.1（CMP-02）＋S0.2 の公開系回帰／T-R2 ガード ／ **TC**: （割当待ち）

### AC-12-3（境界・復旧）

- **Given**: 発行 INSERT のコミット直後にクラッシュし、再起動後のステップ再評価で同一 idempotency_key・同一 (loop_run_id, step_key, attempt) の発行が再実行される ／ **When**: 同じタスク発行を再実行する ／ **Then**: 既存 tasks 行が検出・採用され、重複行は作られない（UNIQUE 衝突を例外露出せず冪等に収束させる）
- **fixture**: seed: tasks 1 行（loop_run_id=1, step_key='plan', attempt=1, idempotency_key='K1'）を先行 INSERT 済み、同一パラメータで再発行
- **観測点**: 発行 API 戻り値（既存行の id）／tasks SELECT count ／ **期待状態**: tasks 1 行のまま（state='pending' 不変）
- **期待 DB 差分**: 差分なし ／ **期待証跡**: なし（無副作用の冪等再実行）
- **禁止副作用**: tasks への 2 行目 INSERT・attempt の暗黙増加・UNIQUE 制約例外の呼出し側への素通し ／ **エラー型**: なし
- **対象更新**: S0.1（CMP-02）／発行の冪等性・クラッシュ再開 ／ **TC**: （割当待ち）

## FR-13

### AC-13-1（正常）

- **Given**: verifying の task（output_json 保存済み・workflow 必須証跡完備）と、author と別 principal の verifier による PASS 判定 ／ **When**: verify_pass イベントを適用する ／ **Then**: done へ遷移し、review_pass 証跡と遷移ログが残り、retry_count は変化しない
- **fixture**: seed: agents 2 行（principal 相違）、tasks 1 行（state='verifying', retry_count=0, output_json 保存済み）、evidence に workflow の必須 kind（review_pass 含む）を投入済み
- **観測点**: tasks.state SELECT／state_transitions SELECT／evidence SELECT ／ **期待状態**: tasks.state = 'done'（completed_at 記録・retry_count=0 のまま）
- **期待 DB 差分**: tasks 1 行 UPDATE（verifying→done）、state_transitions +1 行（event='verify_pass', guard_result='passed'） ／ **期待証跡**: evidence: review_pass（result=PASS・reviewer は author と別 agent）
- **禁止副作用**: retry_count の変化・author 自身の principal による PASS 判定 ／ **エラー型**: なし
- **対象更新**: S0.1（CMP-02 マイクロループ＋CMP-01 状態機械）／verify_pass ／ **TC**: （割当待ち）

### AC-13-2（拒否）

- **Given**: verifying の task に、差戻し理由（failure_detail）と verifier 証跡の両方を欠いた FAIL 判定 ／ **When**: verify_fail イベントを適用する ／ **Then**: ガード不成立で TransitionRejected が raise され、state・retry_count は不変のまま拒否が記録される
- **fixture**: seed: tasks 1 行（state='verifying', retry_count=1）、FAIL 入力 = 差戻し理由 None・verifier 証跡なし
- **観測点**: raise される例外型／tasks SELECT／state_transitions SELECT ／ **期待状態**: tasks.state = 'verifying' のまま（retry_count=1 不変）
- **期待 DB 差分**: state_transitions +1 行（event='verify_fail', guard_result='rejected'）のみ。tasks 差分なし ／ **期待証跡**: state_transitions 拒否行（差戻し理由欠如による rejected）
- **禁止副作用**: in_progress への差戻し・retry_count の増加 ／ **エラー型**: TransitionRejected
- **対象更新**: S0.1（CMP-02＋CMP-01）／verify_fail ガード ／ **TC**: （割当待ち）

### AC-13-3（境界・復旧）

- **Given**: config.retry_limit=3、retry_count=2（= 上限 - 1）の verifying task と、差戻し理由・verifier 証跡つきの FAIL 判定 ／ **When**: FAIL の遷移イベントを適用する（retry_count + 1 >= retry_limit の境界） ／ **Then**: in_progress へは戻らず verify_fail_exhausted で escalated（終端）となり、retry_count はちょうど 3 になる
- **fixture**: seed: config 1 行（key='retry_limit', value_json='3', value_type='integer'）、tasks 1 行（state='verifying', retry_count=2）、差戻し理由・verifier 証跡を投入済み
- **観測点**: tasks.state・retry_count SELECT／state_transitions SELECT ／ **期待状態**: tasks.state = 'escalated'（終端）、retry_count=3
- **期待 DB 差分**: tasks 1 行 UPDATE（verifying→escalated, retry_count 2→3）、state_transitions +1 行（event='verify_fail_exhausted', guard_result='passed'） ／ **期待証跡**: state_transitions 行＋tasks.failure_detail（最終差戻し理由）
- **禁止副作用**: in_progress への 4 回目の差戻し・retry_count の 2 加算・failed への誤分類 ／ **エラー型**: なし
- **対象更新**: S0.1（CMP-02）／retry_limit 境界（AC-13 の正本条件） ／ **TC**: （割当待ち）

## FR-14

### AC-14-1（正常）

- **Given**: 空でない KPI 目標を持つ planned の WP sprint と、blocked のまま遅延している他媒体（X）の sprint が並存する ／ **When**: WP sprint の開始判定を実行する ／ **Then**: WP sprint は active になり、X sprint の状態に影響されず・影響も与えない（媒体独立）
- **fixture**: seed: action_plans 1 行（status='active'）、sprints 2 行（WP: status='planned', kpi_target_json={"pv_weekly":500} ／ X: status='blocked'）、config 1 行（key='loop.wp.cycle', value_json='"P7D"'）
- **観測点**: sprints.status SELECT（WP・X 両行） ／ **期待状態**: WP sprint = 'active'、X sprint = 'blocked' のまま
- **期待 DB 差分**: sprints 1 行 UPDATE（WP のみ planned→active） ／ **期待証跡**: sprints 行の status 変化（列更新が正本 — 遷移ログ対象外）
- **禁止副作用**: X sprint 行の変更・他媒体待ち合わせによる開始保留（同期強制） ／ **エラー型**: なし
- **対象更新**: S1（FN-106 スプリント制御）／開始条件と媒体独立性 ／ **TC**: （割当待ち）

### AC-14-2（拒否）

- **Given**: kpi_target_json が空 JSON（{}）で対応 kpi_node の target_json も NULL の planned sprint と、それを参照する pending の下位 loop_run ／ **When**: sprint 開始判定と下位 loop_run の start を実行する ／ **Then**: sprint は SprintStartRejected で planned のまま、下位 loop_run の start も §3.1 ガード（sprint の KPI target 存在）で拒否される
- **fixture**: seed: sprints 1 行（status='planned', kpi_target_json='{}'）、kpi_nodes 1 行（target_json=NULL）、下位 loop_runs 1 行（state='pending', 当該 sprint 参照・active brief 保持）
- **観測点**: raise される例外型／sprints.status SELECT／loop_runs.state SELECT／state_transitions SELECT ／ **期待状態**: sprint = 'planned'、loop_run = 'pending'（いずれも不変）
- **期待 DB 差分**: sprints 差分なし。state_transitions +1 行（loop_run start の guard_result='rejected'） ／ **期待証跡**: state_transitions 拒否行（KPI target 欠如）
- **禁止副作用**: sprint の active 化・下位 loop_run の running 化・タスク発行 ／ **エラー型**: SprintStartRejected（下位 run 側は TransitionRejected）
- **対象更新**: S1（FN-106）＋S0.1 start ガードの回帰／LP-R2 ／ **TC**: （割当待ち）

### AC-14-3（境界・復旧）

- **Given**: ends_at に到達した active の sprint A と、開始 UPDATE のコミット前に強制終了して中断した planned の sprint B（KPI 目標あり） ／ **When**: A の期限到達処理を実行し、再起動後に B の開始判定を再実行する ／ **Then**: A は reviewing へ移行して新規タスク発行が止まり、B は中間状態なく planned から同じ判定の再実行で active になる
- **fixture**: seed: sprints A（status='active', ends_at=過去時刻）、sprints B（status='planned', kpi_target_json={"pv_weekly":300}）— B の開始 UPDATE をコミット前 kill で中断
- **観測点**: sprints.status SELECT（再起動前後）／A 配下での新規 tasks 発行の可否 ／ **期待状態**: A = 'reviewing'、B = 再実行後 'active'（planned/active 以外の中間値なし）
- **期待 DB 差分**: A: 1 行 UPDATE（active→reviewing）。B: kill 分は差分なし → 再実行で 1 行 UPDATE（planned→active） ／ **期待証跡**: sprints 行の status 遷移（正本）
- **禁止副作用**: reviewing 移行後の A への新規タスク発行・B の状態不定 ／ **エラー型**: なし
- **対象更新**: S1（FN-106）／期限境界と再開（無状態判定の再実行） ／ **TC**: （割当待ち）

## FR-15

### AC-15-1（正常）

- **Given**: reviewing の sprint に pair_kpi_measure（status = passed）が成立している（KPI 目標と計測スナップショットの両参照あり） ／ **When**: 還流処理を実行する ／ **Then**: learnings が 1 行生成され（source_pair_id で成立ペアへ FK 接続・status = draft）、上位ループ次回転の入力として参照できる
- **fixture**: seed: sprints 1 行（status='reviewing'）、kpi_nodes→measurements→evidence の連鎖 1 組、pair_kpi_measure 1 行（status='passed'）、上位 loop_runs 1 行（loop_kind='upper'）
- **観測点**: learnings SELECT（sprint_id・source_pair_id・status）／上位ループ入力キューの参照 API ／ **期待状態**: learnings.status = 'draft'（採否は上位ループ側の判断待ち）
- **期待 DB 差分**: learnings +1 行（sprint_id・source_pair_id の FK 接続・learning_json 有効） ／ **期待証跡**: learnings 行（source_pair_id つき — 還流の正本）
- **禁止副作用**: strategic_briefs への書込み（下流からの上流正本直接変更 — SR-07 違反） ／ **エラー型**: なし
- **対象更新**: S1（FN-107 還流処理）／レビュー成立→learnings 生成 ／ **TC**: （割当待ち）

### AC-15-2（拒否）

- **Given**: 計測は存在するが pair_kpi_measure が 0 行（ペア未成立）の reviewing sprint ／ **When**: 還流処理を実行する ／ **Then**: PairNotEstablished で拒否され、learnings は生成されず上位キューにも積まれない（REQ-009 — ペア成立まで還流は発生しない）
- **fixture**: seed: sprints 1 行（status='reviewing'）、measurements 1 行（evidence 接続あり）、pair_kpi_measure 0 行
- **観測点**: raise される例外型／learnings SELECT count ／ **期待状態**: learnings 0 行のまま
- **期待 DB 差分**: 差分なし ／ **期待証跡**: なし（生成前拒否）
- **禁止副作用**: learnings INSERT・上位キューへの登録・strategic_briefs への書込み ／ **エラー型**: PairNotEstablished
- **対象更新**: S1（FN-107)／片肺禁止ガード ／ **TC**: （割当待ち）

### AC-15-3（境界・復旧）

- **Given**: 同一 pair から learnings 生成済みで、生成 transaction のコミット直後にクラッシュし再起動した状態（キュー投入の完了は不明） ／ **When**: 同じレビュー成立イベントで還流処理を再実行する ／ **Then**: 同一 source_pair_id の既存 learnings が検出されて重複生成されず、上位キューは learnings 行を正本に再構成される
- **fixture**: seed: pair_kpi_measure 1 行（status='passed'）、learnings 1 行（source_pair_id=当該 pair, status='draft'）を先行投入して再実行
- **観測点**: learnings SELECT count（source_pair_id で絞込み）／再実行 API 戻り値（既存行 id） ／ **期待状態**: learnings 1 行のまま（status='draft' 不変）
- **期待 DB 差分**: 差分なし ／ **期待証跡**: 既存 learnings 行（重複なし）
- **禁止副作用**: 同一 source_pair_id の 2 行目 INSERT・summary/learning_json の上書き ／ **エラー型**: なし
- **対象更新**: S1（FN-107）／還流の冪等性・クラッシュ再開 ／ **TC**: （割当待ち）

## FR-16

### AC-16-1（正常）

- **Given**: 自己修復に失敗した攻略地図破損（playbooks.status='broken'）を検知した in_progress の task と、running の親 loop_run ／ **When**: エスカレーション制御が task へ escalate、親 loop_run へ fatal_failure を発火する ／ **Then**: task と loop_run がともに escalated（安全停止）となり、failure_code が記録され、FR-46 経路へ通知が 1 件送出される
- **fixture**: seed: playbooks 1 行（status='broken', consecutive_failures=2）、tasks 1 行（state='in_progress'）、loop_runs 1 行（state='running'）、通知 transport = mock
- **観測点**: tasks.state・failure_code SELECT／loop_runs.state SELECT／state_transitions SELECT／mock 通知の呼出回数 ／ **期待状態**: tasks = 'escalated'、loop_runs = 'escalated'（終端・人の対処待ち）
- **期待 DB 差分**: tasks 1 行 UPDATE（state='escalated', failure_code='playbook_broken'）、loop_runs 1 行 UPDATE、state_transitions +2 行（escalate／fatal_failure、guard_result='passed'） ／ **期待証跡**: state_transitions 2 行＋tasks.failure_code（事由コード）
- **禁止副作用**: 通知 transport 失敗による遷移の巻き戻し・failed への誤分類・破損 playbook での外部操作継続 ／ **エラー型**: なし
- **対象更新**: S0.1（CMP-01 状態機械）＋S0.2（CMP-11 通知）／escalate・fatal_failure ／ **TC**: （割当待ち）

### AC-16-2（拒否）

- **Given**: done（終端）の task A への escalate 要求と、承認 decision='rejected' を escalate へ振り分けようとする誤分類入力を持つ in_progress の task B ／ **When**: A へ escalate を適用し、B の承認 rejected を分類・遷移させる ／ **Then**: A は TransitionRejected で不変。B は escalate されず non_retryable_failure で failed へ倒される（rejected → non_retryable_failure → failed が正準）
- **fixture**: seed: tasks A（state='done'）、tasks B（state='in_progress'）＋approvals 1 行（decision='rejected', binding 3 項目つき）
- **観測点**: raise される例外型／tasks.state SELECT（A・B）／state_transitions.guard_result SELECT ／ **期待状態**: A = 'done' 不変、B = 'failed'（escalated ではない）
- **期待 DB 差分**: A: state_transitions +1 行（guard_result='rejected'）。B: tasks 1 行 UPDATE（→failed, failure_code='approval_rejected'）＋state_transitions +1 行（event='non_retryable_failure', passed） ／ **期待証跡**: A の拒否行＋B の failure_code・state_transitions 行
- **禁止副作用**: A の状態変更・B の escalated への遷移（rejected の escalate 誤分類）・公開の実行 ／ **エラー型**: TransitionRejected（A 側。B 側は例外なしの failed 遷移）
- **対象更新**: S0.1（CMP-01）＋S0.2 承認分類の回帰／終端保護と正準分類 ／ **TC**: （割当待ち）

### AC-16-3（境界・復旧）

- **Given**: config.approval_retry_limit=2 のもとで、束縛承認が expired を 1 回返した waiting 中の公開系 task（T-PUB 相当） ／ **When**: 承認を再要求し、2 回目も expired となる（上限到達） ／ **Then**: 1 回目の expired では escalate せず承認再要求で待機継続し、approval_retry_limit 到達（2 回目）で escalated へ遷移する
- **fixture**: seed: config 1 行（key='approval_retry_limit', value_json='2', value_type='integer'）、tasks 1 行（T-PUB 相当・親 loop_run waiting）、承認 mock が decision='expired' を 2 連続返却
- **観測点**: 1 回目 expired 後の task/loop 状態／2 回目後の tasks.state SELECT／approvals SELECT 件数 ／ **期待状態**: 1 回目後 = 待機継続（escalated でない・承認再要求済み）、2 回目後 = tasks = 'escalated'
- **期待 DB 差分**: approvals +2 行（decision='expired'）、tasks 1 行 UPDATE（→escalated）、state_transitions +1 行（event='escalate', guard_result='passed'） ／ **期待証跡**: approvals の expired 2 行＋state_transitions 行（再要求系列の証跡）
- **禁止副作用**: 1 回目 expired での即時 escalate・expired の failed への誤分類（rejected と混同）・承認なしの公開実行 ／ **エラー型**: なし
- **対象更新**: S0.2（CMP-11 承認通知＋CMP-01）／approval_retry_limit 境界 ／ **TC**: （割当待ち）

## FR-21

### AC-21-1（正常）

- **Given**: action plan 1 件、commit hash が一致する review_pass 証跡、pair_plan_quality に status = passed の成立ペア ／ **When**: 公開系コネクタが成立ペア ID つきで公開前検証を実行する ／ **Then**: 検証は通過し、WP 下書き作成（外部操作の prepared 化）へ進める
- **fixture**: seed: action_plans 1 行、T-REVIEW done ＋ evidence(review_pass, commit_hash=制作 hash)、pair_plan_quality(plan_id, review_evidence_id, status='passed')
- **観測点**: 公開前検証 API の戻り値／external_operations SELECT／operation_log 件数 ／ **期待状態**: T-PUB が公開ステップへ進行可能（pair 検証 PASS）
- **期待 DB 差分**: pair_plan_quality 差分なし（既存行を根拠に通過）、operation_log 拒否行なし ／ **期待証跡**: なし（正常通過は既存 pair 行が根拠）
- **禁止副作用**: pair 行の変更・operation_log への拒否行追加 ／ **エラー型**: なし
- **対象更新**: S0.2（ゲート層）／pair_plan.check_established・公開前検証 ／ **TC**: （割当待ち）

### AC-21-2（拒否）

- **Given**: review_pass 証跡も pair_plan_quality 行も存在しない action plan ／ **When**: 公開系コネクタがペア ID なしで公開呼び出しを実行する ／ **Then**: PairNotEstablished で拒否され、WP API は一度も呼ばれず、T-PUB は non_retryable_failure で failed になる
- **fixture**: seed: action_plans 1 行のみ（tasks/evidence/pair なし）、T-PUB task を verifying 前の公開検証に投入
- **観測点**: raise される例外型／external_operations SELECT（0 行）／state_transitions・operation_log SELECT ／ **期待状態**: T-PUB = failed（failure_code = pair 不成立）
- **期待 DB 差分**: state_transitions +1 行（failed 遷移）、operation_log +1 行（拒否）、external_operations 差分なし ／ **期待証跡**: operation_log 拒否行（plan_id・理由 = pair 不成立）
- **禁止副作用**: WP API 呼出し（external_operations への行追加）・pair_plan_quality への行追加 ／ **エラー型**: PairNotEstablished
- **対象更新**: S0.2（ゲート層）／公開ゲート FN-202 ／ **TC**: （割当待ち）

### AC-21-3（境界・復旧）

- **Given**: 成立済み pair（passed）を持つ plan の記事を再 commit（内容変更）して pair が revoked 化された状態 ／ **When**: 旧ペア ID を根拠に公開前検証を実行し、その後、再審査 PASS で新 pair を成立させて再実行する ／ **Then**: revoked ペアでの公開は PairNotEstablished で拒否され、再審査後の新 pair でのみ通過する（復旧経路 = 再審査のみ）
- **fixture**: seed: pair_plan_quality(status='revoked') 1 行 → 再審査 T-REVIEW done ＋新 review_pass ＋新 pair(passed) を追加投入
- **観測点**: 1 回目の例外型／2 回目の検証戻り値／pair_plan_quality SELECT ／ **期待状態**: 1 回目拒否・2 回目通過。revoked 行は revoked のまま保持（履歴保持）
- **期待 DB 差分**: pair_plan_quality +1 行（新 passed）、operation_log +1 行（1 回目拒否） ／ **期待証跡**: operation_log 拒否行（理由 = pair revoked）＋新 review_pass 証跡
- **禁止副作用**: revoked 行の passed への書き戻し・revoked ペアでの外部書込み ／ **エラー型**: PairNotEstablished（1 回目）／なし（2 回目）
- **対象更新**: S0.2（ゲート層）／pair 失効と再成立 ／ **TC**: （割当待ち）

## FR-22

### AC-22-1（正常）

- **Given**: KPI 目標が設定された sprint（reviewing）と、取得証跡つき measurement（sprint 期間と整合） ／ **When**: スプリントレビュー成立判定を実行する ／ **Then**: pair_kpi_measure に passed 行が作られ、レビュー成立イベントが発火して sprint が completed になり、learnings 生成の起点となる
- **fixture**: seed: sprints(status='reviewing', kpi_target_json に PV 目標)、kpi_nodes 1 行、measurements 1 行（evidence_id FK あり・期間整合）
- **観測点**: pair_kpi_measure SELECT／sprints.status／learnings 生成キューの呼出し記録 ／ **期待状態**: sprint = completed、pair = passed
- **期待 DB 差分**: pair_kpi_measure +1 行（passed）、sprints 1 行 UPDATE（completed） ／ **期待証跡**: pair_kpi_measure 行（成立根拠 = measurement＋evidence FK）
- **禁止副作用**: measurement のない状態でのレビュー成立・上位還流 ／ **エラー型**: なし
- **対象更新**: S1（ゲート層）／pair_kpi.check_established・レビュー成立イベント ／ **TC**: （割当待ち）

### AC-22-2（拒否）

- **Given**: KPI 目標は設定済みだが計測スナップショット（measurements 行）が 1 件も存在しない sprint ／ **When**: スプリントレビュー成立判定を実行する ／ **Then**: ReviewNotEstablished で不成立となり、レビュー成立イベント・learnings 生成・上位還流のいずれも発生しない
- **fixture**: seed: sprints(status='reviewing', kpi_target_json あり)、kpi_nodes 1 行、measurements 空
- **観測点**: raise される例外型（又は不成立戻り値）／sprints.status／pair_kpi_measure・learnings SELECT ／ **期待状態**: sprint = reviewing のまま（遷移なし）
- **期待 DB 差分**: 差分なし（pair_kpi_measure・learnings とも 0 行のまま） ／ **期待証跡**: なし（不成立は状態不変で表現。state_transitions への rejected 記録は sprint 遷移要求時のみ）
- **禁止副作用**: レビュー成立イベント発火・learnings への行追加・上位ループへの還流 ／ **エラー型**: ReviewNotEstablished
- **対象更新**: S1（ゲート層）／pair_kpi 片肺検出 ／ **TC**: （割当待ち）

### AC-22-3（境界・復旧）

- **Given**: kpi_target_json が空 JSON（目標ノード 0 件）の sprint と、後から取り込まれる measurement ／ **When**: 空目標のままレビュー判定 → KPI 目標を設定し measurement 取り込み完了後に再判定する ／ **Then**: 空目標時は判定不能として不成立（fail-close）、目標設定と計測の両参照が揃った再判定でのみ成立する（不成立は恒久拒否ではなく待機）
- **fixture**: seed: sprints(kpi_target_json='{}') → 再判定前に kpi_target_json 設定済み新 sprint 状態＋measurements 1 行（evidence FK あり）を投入
- **観測点**: 1 回目の不成立判定／2 回目の pair_kpi_measure SELECT と sprints.status ／ **期待状態**: 1 回目 = reviewing のまま、2 回目 = completed
- **期待 DB 差分**: 2 回目のみ pair_kpi_measure +1 行・sprints UPDATE ／ **期待証跡**: 2 回目の pair_kpi_measure 行（passed）
- **禁止副作用**: 空目標での成立（fail-open）・1 回目でのレビュー成立イベント発火 ／ **エラー型**: ReviewNotEstablished（1 回目）／なし（2 回目）
- **対象更新**: S1（ゲート層）／目標空の判定不能処理と後着計測での再判定 ／ **TC**: （割当待ち）

## FR-23

### AC-23-1（正常）

- **Given**: 有料指標を含まない KPI ノード定義（例: 週間表示回数）と、許可リストに含まれる URL ／ **When**: KPI 登録とブラウザ遷移判定を実行する ／ **Then**: 登録は成功し、遷移は許可され、拒否ログは増えない
- **fixture**: seed: config.url_allowlist=['blog.example.test']、kpi_nodes 空
- **観測点**: 登録 API 戻り値／kpi_nodes SELECT／operation_log 件数 ／ **期待状態**: kpi_nodes に 1 行（非有料型）
- **期待 DB 差分**: kpi_nodes +1 行、operation_log 差分なし ／ **期待証跡**: なし（正常通過は証跡不要）
- **禁止副作用**: operation_log への拒否行の追加 ／ **エラー型**: なし
- **対象更新**: S0.2（ゲート層）／zero_ad.check_metric・check_url ／ **TC**: （割当待ち）

### AC-23-2（拒否）

- **Given**: 有料指標型（ROAS）の KPI ノード定義と、許可リスト外の広告マネージャ URL ／ **When**: KPI 登録とブラウザ遷移判定を実行する ／ **Then**: 登録は PaidMetricRejected、遷移は UrlDenied で拒否され、それぞれ operation_log に理由が残る
- **fixture**: seed: config.url_allowlist=['blog.example.test']、登録要求 = {type:'ROAS'}、URL='`https://ads.example.com`'
- **観測点**: raise される例外型／operation_log SELECT ／ **期待状態**: kpi_nodes 空のまま
- **期待 DB 差分**: operation_log +2 行（指標拒否・URL 拒否） ／ **期待証跡**: operation_log 拒否行（指標名・URL・理由）
- **禁止副作用**: kpi_nodes への行追加・外部への実遷移 ／ **エラー型**: PaidMetricRejected／UrlDenied
- **対象更新**: S0.2（ゲート層） ／ **TC**: （割当待ち）

### AC-23-3（境界・復旧）

- **Given**: config.url_allowlist が空（未設定）の状態 ／ **When**: 任意の URL への遷移判定を実行する ／ **Then**: deny-by-default によりすべて拒否される（判定不能は通さない側へ倒れる）
- **fixture**: seed: config から url_allowlist 行を削除
- **観測点**: raise される例外型／operation_log SELECT ／ **期待状態**: 遷移 0 件許可
- **期待 DB 差分**: operation_log +1 行（拒否） ／ **期待証跡**: operation_log 拒否行（理由 = allowlist 未設定）
- **禁止副作用**: URL 許可（fail-open） ／ **エラー型**: UrlDenied
- **対象更新**: S0.2（ゲート層） ／ **TC**: （割当待ち）

## FR-24

### AC-24-1（正常）

- **Given**: ASP ドメインへのアフィリエイトリンクと規定の PR 表記ブロックを両方含む commit 固定済み記事 ／ **When**: 公開前の PR 表記検証を実行する ／ **Then**: 表記検証に合格して公開ゲートを通過し、拒否ログは増えない
- **fixture**: seed: config.affiliate_domainlist=['asp.example.test']、記事 HTML に <a href='`https://asp.example.test/...`'> と PR 表記ブロック（必須文言）を含む fixture ファイル
- **観測点**: 検証 API の戻り値／operation_log 件数 ／ **期待状態**: T-PUB が公開ステップへ進行可能（表記検証 PASS）
- **期待 DB 差分**: operation_log 差分なし ／ **期待証跡**: なし（正常通過。審査側 review_pass の checked_items に表記検証結果）
- **禁止副作用**: operation_log への拒否行追加・表記なしでの通過 ／ **エラー型**: なし
- **対象更新**: S1（ゲート層）／pr_label.check ／ **TC**: （割当待ち）

### AC-24-2（拒否）

- **Given**: ASP ドメインへのアフィリエイトリンクを含み PR 表記ブロックがない記事 ／ **When**: 公開前の PR 表記検証を実行する ／ **Then**: PrLabelMissing で公開ゲートを通過せず、operation_log に検出リンクと欠落規則が記録され、外部書込みは発生しない
- **fixture**: seed: config.affiliate_domainlist=['asp.example.test']、記事 HTML にリンクのみ・表記ブロックなし
- **観測点**: raise される例外型／operation_log SELECT／external_operations SELECT（0 行） ／ **期待状態**: T-PUB = failed（non_retryable_failure）
- **期待 DB 差分**: operation_log +1 行（拒否）、external_operations 差分なし ／ **期待証跡**: operation_log 拒否行（commit hash・検出リンク・欠落規則）
- **禁止副作用**: WP API 呼出し・表記なし成果物の公開ゲート通過 ／ **エラー型**: PrLabelMissing
- **対象更新**: S1（ゲート層）／pr_label.check ／ **TC**: （割当待ち）

### AC-24-3（境界・復旧）

- **Given**: config.affiliate_domainlist が未設定（config 行なし）の状態と、短縮 URL 経由で ASP へリダイレクトするリンクを含む記事 ／ **When**: 公開前の PR 表記検証を実行し、その後リストを設定して再実行する ／ **Then**: リスト未設定時は判定不能として公開を拒否（fail-close）し、リスト設定後は展開後の最終 URL で ASP 該当と判定して表記検証が適用される
- **fixture**: seed: config から affiliate_domainlist 行を削除 → 再実行前に config INSERT（履歴追加）で設定、短縮 URL fixture（リダイレクト mock）
- **観測点**: 1 回目の例外型／2 回目の判定結果（最終 URL での ASP 該当）／operation_log SELECT ／ **期待状態**: 1 回目 = 拒否（判定不能）、2 回目 = 表記有無に応じた通常判定
- **期待 DB 差分**: operation_log +1 行（1 回目拒否）、config +1 行（リスト設定 — INSERT 履歴） ／ **期待証跡**: operation_log 拒否行（理由 = domainlist 未設定）
- **禁止副作用**: リスト未設定での通過（fail-open）・展開前 URL のみでの非該当判定 ／ **エラー型**: PrLabelMissing（判定不能時も拒否種別を統一）
- **対象更新**: S1（ゲート層）／domainlist 未設定の fail-close とリダイレクト展開判定 ／ **TC**: （割当待ち）

## FR-25

### AC-25-1（正常）

- **Given**: P5 項目（恐怖訴求・偽希少性・不安増幅・診断の押し付け）に非該当の commit 固定済み記事と、別 principal の verifier ／ **When**: T-REVIEW の審査を実行する ／ **Then**: P5 全項目のチェックを経て verify_pass し、review_pass 証跡の checked_items に P5 全項目の判定が残る
- **fixture**: seed: WF-WP-1 の T-REVIEW（verifying）、非該当記事 fixture、workflows.definition_json に P5 必須項目
- **観測点**: tasks.state／evidence SELECT（kind='review_pass' の payload_json.checked_items） ／ **期待状態**: T-REVIEW = done
- **期待 DB 差分**: evidence +1 行（review_pass）、state_transitions +1 行（verify_pass, passed） ／ **期待証跡**: review_pass 証跡（result=PASS、checked_items に P5 全 4 項目）
- **禁止副作用**: P5 チェックを省略した PASS（checked_items 欠落）の記録 ／ **エラー型**: なし
- **対象更新**: S1（審査 WF）／ethics.check（S0 は fail-close ルールセット） ／ **TC**: （割当待ち）

### AC-25-2（拒否）

- **Given**: 恐怖訴求表現を含む記事（P5 該当）と verifying 状態の T-REVIEW ／ **When**: T-REVIEW の審査を実行する ／ **Then**: EthicsViolation 分類の FAIL となり、差戻し理由つき verify_fail で in_progress へ戻り retry_count が 1 増え、review_pass は生成されない
- **fixture**: seed: T-REVIEW(verifying, retry_count=0)、恐怖訴求文言を含む記事 fixture、config.retry_limit=3
- **観測点**: tasks.state・retry_count／evidence SELECT（review_pass 0 行・FAIL 理由証跡）／state_transitions SELECT ／ **期待状態**: 対象 task = in_progress（retry_count=1）
- **期待 DB 差分**: tasks UPDATE（retry_count+1）、state_transitions +1 行（verify_fail）、verifier の FAIL 理由証跡 +1 行 ／ **期待証跡**: 差戻し理由（P5 該当項目名）を含む verifier 証跡
- **禁止副作用**: review_pass 証跡の生成・done への遷移・pair_plan_quality の成立 ／ **エラー型**: EthicsViolation（verify_fail 分類）
- **対象更新**: S1（審査 WF）／ethics.check FAIL 経路 ／ **TC**: （割当待ち）

### AC-25-3（境界・復旧）

- **Given**: P5 該当の差戻しが繰り返され retry_count + 1 >= config.retry_limit に達する T-REVIEW ／ **When**: 上限到達となる審査 FAIL を実行する ／ **Then**: verify_fail_exhausted で escalated へ遷移して人間裁定待ちとなり、再開は人間の裁定に基づく新 task の明示発行のみ（自動での done 化経路がない）
- **fixture**: seed: T-REVIEW(verifying, retry_count=2)、config.retry_limit=3、P5 該当記事 fixture
- **観測点**: tasks.state・retry_count／state_transitions SELECT／escalated 後の遷移試行の拒否 ／ **期待状態**: 対象 task = escalated（retry_count=3、終端）
- **期待 DB 差分**: tasks UPDATE（escalated）、state_transitions +1 行（verify_fail_exhausted） ／ **期待証跡**: 差戻し理由証跡＋state_transitions 行（escalated 遷移）
- **禁止副作用**: escalated 後の自動遷移・上限超過後の verify_fail 継続（in_progress への差戻し） ／ **エラー型**: EthicsViolation（verify_fail_exhausted 分類）
- **対象更新**: S1（審査 WF）／retry 上限と escalation 境界 ／ **TC**: （割当待ち）

## FR-26

### AC-26-1（正常）

- **Given**: オートモード基準を充足済みの環境で、金銭操作型（価格変更）の task が外部書込み前にある状態 ／ **When**: 外部操作を要求し、束縛承認に approved（binding 3 項目完全一致）で応答する ／ **Then**: オートモードでも承認要求が発行され、approved 確認と evidence(approval) 記録の後にのみ外部操作（prepared→sent→confirmed）へ進む
- **fixture**: seed: config.auto_mode_criteria 充足の実績証跡、金銭操作型 task(in_progress)、承認応答 mock = approved（binding 一致）
- **観測点**: approvals SELECT（pending→approved）／evidence SELECT（kind='approval'）／external_operations の遷移順 ／ **期待状態**: 承認後に外部操作実行、task は verifying へ進行可能
- **期待 DB 差分**: approvals +1 行（approved）、evidence +1 行（approval）、external_operations +1 行 ／ **期待証跡**: evidence.kind = approval（decision=approved、binding_subject/operation/at）
- **禁止副作用**: 承認要求前・approved 確認前の外部書込み（オートモードによるバイパス） ／ **エラー型**: なし
- **対象更新**: S1（ゲート層＋承認チャネル）／money_escalation.require_approval ／ **TC**: （割当待ち）

### AC-26-2（拒否）

- **Given**: 金銭操作型（返金）の task と、束縛承認に rejected で応答する承認者 ／ **When**: 外部操作を要求し、承認が rejected となる ／ **Then**: non_retryable_failure イベントで task は failed になり、外部書込みは 0 件のまま（escalated ではなく failed — 代替 task 発行可）
- **fixture**: seed: 金銭操作型 task(in_progress)、承認応答 mock = rejected
- **観測点**: tasks.state・failure_code／approvals.decision／external_operations SELECT（0 行） ／ **期待状態**: 対象 task = failed（failure_code = 承認却下）
- **期待 DB 差分**: approvals +1 行（rejected）、tasks UPDATE（failed）、state_transitions +1 行、external_operations 差分なし ／ **期待証跡**: approvals 行（decision=rejected・responder_ref）＋state_transitions 行
- **禁止副作用**: 外部書込みの実行・escalated への遷移（rejected は escalate に含まない — s0-contract §3.2） ／ **エラー型**: ApprovalRejected（non_retryable_failure 分類）
- **対象更新**: S1（ゲート層＋承認チャネル）／rejected の failed 化 ／ **TC**: （割当待ち）

### AC-26-3（境界・復旧）

- **Given**: 金銭操作型 task の束縛承認が応答期限切れ（expired）を繰り返す状態と config.approval_retry_limit=2 ／ **When**: expired ごとに承認を再要求し、再要求回数が上限に到達する ／ **Then**: expired の間は再要求を発行して waiting を継続し（failed にしない）、approval_retry_limit 到達で escalate イベントにより escalated へ倒れる
- **fixture**: seed: 金銭操作型 task、承認応答 mock = expired を連続返答、config.approval_retry_limit=2
- **観測点**: approvals SELECT（expired 行＋再要求 pending 行の履歴）／loop_runs/tasks の状態列／state_transitions SELECT ／ **期待状態**: 上限到達前 = waiting 継続、到達後 = escalated（終端）
- **期待 DB 差分**: approvals +3 行（初回＋再要求 2 回、各 expired/pending 履歴）、state_transitions +1 行（escalate） ／ **期待証跡**: approvals の全要求履歴＋state_transitions 行（escalate、guard に再要求回数）
- **禁止副作用**: expired での即 failed 化・上限到達後の再要求継続・未承認での外部書込み ／ **エラー型**: ApprovalExpired（escalate 分類 — 上限到達時）
- **対象更新**: S1（ゲート層＋承認チャネル）／expired 再要求と approval_retry_limit ／ **TC**: （割当待ち）

## FR-27

### AC-27-1（正常）

- **Given**: principal の異なる active な author agent と verifier agent（例: claude 系と gate-engine） ／ **When**: task を発行し、author agent に属する execution が claim する ／ **Then**: tasks INSERT と claim がともに成功し、task は in_progress になる
- **fixture**: seed: agents 2 行（principal='claude-model'／'gate-engine'）、agent_executions 1 行（author 帰属）、workflow・loop_run(running)
- **観測点**: tasks INSERT の成否／tasks.state／state_transitions SELECT（claim, passed） ／ **期待状態**: task = in_progress（lease_owner_execution_id = author の execution）
- **期待 DB 差分**: tasks +1 行、state_transitions +1 行（claim, passed） ／ **期待証跡**: state_transitions 行（guard_result=passed）＋tasks 行の割当そのもの
- **禁止副作用**: verifier execution による lease 取得 ／ **エラー型**: なし
- **対象更新**: S0.1（kernel＋DB 基盤）／assigner.assign・kernel.claim ／ **TC**: （割当待ち）

### AC-27-2（拒否）

- **Given**: (a) author_agent_id == verifier_agent_id の割当要求、(b) 別 agent 行だが principal が同一の割当・claim 要求 ／ **When**: (a) を tasks に直接 INSERT し、(b) をエンジン経由で claim する ／ **Then**: (a) は DB の CHECK 制約が IntegrityError で拒否し、(b) はエンジンが SelfReviewRejected で拒否する（二重拒否の両層をそれぞれ観測）
- **fixture**: seed: agents 3 行（うち 2 行は agent_key 相違・principal 同一）。(a) 同一 id 割当 SQL、(b) 同一 principal ペアの task＋claim 要求
- **観測点**: (a) sqlite3.IntegrityError の捕捉／(b) raise される例外型と state_transitions SELECT（rejected） ／ **期待状態**: (a) 行は作られず、(b) task は pending のまま
- **期待 DB 差分**: (a) 差分なし（rollback）、(b) state_transitions +1 行（claim, rejected） ／ **期待証跡**: state_transitions の rejected 行（(b) の claim 拒否）
- **禁止副作用**: 同一 agent／同一 principal での in_progress 遷移・lease 取得 ／ **エラー型**: IntegrityError（DB 層）／SelfReviewRejected（エンジン層）
- **対象更新**: S0.1（kernel＋DB 基盤）／CHECK 制約と claim ガードの二重拒否 ／ **TC**: （割当待ち）

### AC-27-3（境界・復旧）

- **Given**: author execution の lease が失効（lease_expires_at 経過）した in_progress の task ／ **When**: verifier agent の execution が再 claim を試み、続いて author agent の新 execution が再 claim する ／ **Then**: verifier execution の再 claim は拒否され、author agent に属する新 execution のみが lease を取得して作業を再開できる（失効後も自己審査境界は破れない）
- **fixture**: seed: task(in_progress, lease_expires_at=過去時刻)、verifier の execution 1 行、author の新 execution 1 行
- **観測点**: 再 claim の例外型／tasks.lease_owner_execution_id・heartbeat_at／state_transitions SELECT ／ **期待状態**: lease_owner_execution_id = author の新 execution、task = in_progress で再開
- **期待 DB 差分**: tasks UPDATE（lease 列・row_version）、state_transitions +1 行（拒否 rejected） ／ **期待証跡**: state_transitions の rejected 行（verifier execution の claim 拒否）
- **禁止副作用**: verifier execution への lease 移譲・row_version を経ない lease 上書き ／ **エラー型**: SelfReviewRejected（verifier execution の再 claim）
- **対象更新**: S0.1（kernel）／lease 失効後の再 claim ガード（s0-contract §1・§3.3） ／ **TC**: （割当待ち）

## FR-28

### AC-28-1（正常）

- **Given**: required_evidence_json = ['plan_record'] の T-PLAN（verifying）に、kind 規則を満たす plan_record 証跡が揃った状態 ／ **When**: verify_pass を要求する ／ **Then**: 必須証跡完備の検証を経て done へ遷移し、state_transitions に passed が記録される
- **fixture**: seed: workflows(required_evidence_json='["plan_record"]')、T-PLAN(verifying)、evidence(kind='plan_record', payload に plan_id/appeal/target/intent)
- **観測点**: tasks.state／state_transitions SELECT（verify_pass, passed） ／ **期待状態**: T-PLAN = done（終端）
- **期待 DB 差分**: tasks UPDATE（done）、state_transitions +1 行（passed） ／ **期待証跡**: 既存 plan_record 証跡（完備集合）＋state_transitions 行
- **禁止副作用**: 証跡未検証での done 化・evidence 行の変更（append-only） ／ **エラー型**: なし
- **対象更新**: S0.1（ゲート層＋証跡ストア）／evidence_complete.check ／ **TC**: （割当待ち）

### AC-28-2（拒否）

- **Given**: required_evidence_json = ['published_url','screenshot','approval'] の T-PUB（verifying）で approval 証跡だけが欠落した状態 ／ **When**: verify_pass を要求する ／ **Then**: EvidenceIncomplete で done 遷移が拒否され、task は verifying のまま、state_transitions に guard_result = rejected と欠落 kind が記録される
- **fixture**: seed: T-PUB(verifying)、evidence に published_url・screenshot の 2 行のみ（approval なし）
- **観測点**: raise される例外型／tasks.state（不変）／state_transitions SELECT（rejected, details に欠落 kind） ／ **期待状態**: T-PUB = verifying のまま（状態・retry_count・証跡すべて不変）
- **期待 DB 差分**: state_transitions +1 行（rejected）のみ ／ **期待証跡**: state_transitions の rejected 行（details_json に欠落 kind='approval'）
- **禁止副作用**: done への遷移・retry_count の変更・既存 evidence の変更 ／ **エラー型**: EvidenceIncomplete
- **対象更新**: S0.1（ゲート層）／done 遷移ガードの証跡完備検証 ／ **TC**: （割当待ち）

### AC-28-3（境界・復旧）

- **Given**: required_evidence_json に evidence.kind の enum 外の値（'unknown_kind'）を含む workflow の task（verifying） ／ **When**: verify_pass を要求し、その後 workflow を正しい kind 宣言の新 version に修正し欠落証跡を追記して再要求する ／ **Then**: 未定義 kind の宣言は判定不能として done を拒否（fail-close）し、宣言修正＋証跡追記（append-only INSERT）後の再要求でのみ done へ遷移する
- **fixture**: seed: workflows(required_evidence_json='["unknown_kind"]', version=1) → 修正版 workflows(version=2, 正しい kind)＋適合 evidence を追記して再検証
- **観測点**: 1 回目の例外型と state_transitions（rejected）／2 回目の tasks.state（done） ／ **期待状態**: 1 回目 = verifying のまま、2 回目 = done
- **期待 DB 差分**: state_transitions +2 行（rejected → passed）、workflows +1 行（新 version）、evidence +1 行（追記） ／ **期待証跡**: state_transitions の rejected 行（理由 = 未定義 kind）＋追記された適合証跡
- **禁止副作用**: 未定義 kind の素通し（fail-open）・既存 workflow 行の required_evidence_json の書換え（rename/意味変更禁止 — 新 version で対応） ／ **エラー型**: EvidenceIncomplete（判定不能時も拒否種別を統一）
- **対象更新**: S0.1（ゲート層）／宣言不正の fail-close と証跡追記による復旧 ／ **TC**: （割当待ち）

## FR-31

### AC-31-1（正常）

- **Given**: 必須スロット 3 件中 1 件（例: 価格帯）が未充足の business_profile と、型に合致する人間回答 ／ **When**: 空き検出→問診生成→回答の型検証→充填を実行する ／ **Then**: 質問リストは未充足 1 件のみを含み、回答が型検証 PASS で profile_json に充填され、以後の空き検出が 0 件になる
- **fixture**: seed: business_profiles 1 行（profile_json = 価格帯スロットのみ null）、回答 = {price_range: '3000-5000'}
- **観測点**: 問診生成 API の質問リスト／business_profiles SELECT（profile_json）／evidence SELECT（問診・回答紐付け） ／ **期待状態**: 全必須スロット充足（空き検出 0 件）
- **期待 DB 差分**: business_profiles 1 行 UPDATE（price_range 充填）、evidence +1 行（問診・回答・型検証結果） ／ **期待証跡**: 問診レコードと回答の紐付け行＋型検証 PASS の記録
- **禁止副作用**: 未照会スロットへの値の書込み（推測充填）・他プロファイル行の変更 ／ **エラー型**: なし
- **対象更新**: S1（ヒアリングエンジン）／fillers.detect_gaps・fill_from_answer ／ **TC**: （割当待ち）

### AC-31-2（拒否）

- **Given**: 必須スロット（例: ターゲット顧客）が未充足の business_profile と、そのスロットに依存するタスクの開始要求 ／ **When**: 依存タスクの開始前提判定を実行する ／ **Then**: SlotUnfilledRejected で開始が拒否され、タスク状態は pending のまま変化せず、未充足スロット名が拒否理由として記録される
- **fixture**: seed: business_profiles 1 行（target_customer = null）、tasks 1 行（state='pending'、当該スロット依存）
- **観測点**: raise される例外型／tasks SELECT（state）／構造化ログの拒否行 ／ **期待状態**: tasks.state = 'pending'（遷移なし）
- **期待 DB 差分**: tasks・business_profiles 差分なし、構造化ログ +1 行（拒否） ／ **期待証跡**: 開始拒否ログ（未充足スロット名 = target_customer を含む）
- **禁止副作用**: タスクの in_progress 遷移・スロットへの推測値の自動充填 ／ **エラー型**: SlotUnfilledRejected
- **対象更新**: S1（ヒアリングエンジン）／開始前提ガード ／ **TC**: （割当待ち）

### AC-31-3（境界・復旧）

- **Given**: 未充足スロット 3 件のうち 2 件だけ回答済みの状態でプロセスが強制終了した business_profile ／ **When**: プロセス再起動後にヒアリングエンジンを再実行する ／ **Then**: 充填済み 2 件は再照会されず、残り 1 件のみの質問リストが生成される（申し送りなしで DB 状態から再開）
- **fixture**: seed: business_profiles 1 行（3 スロット中 2 件充填済み — クラッシュ前の確定分を再現）
- **観測点**: 再実行時の質問リスト内容／business_profiles SELECT（充填済み値の不変性） ／ **期待状態**: 質問リスト = 未充足 1 件のみ
- **期待 DB 差分**: 差分なし（再照会前の空き検出時点） ／ **期待証跡**: なし（空き検出は読み取りのみ）
- **禁止副作用**: 充填済みスロットの再照会・充填済み値の消去や上書き ／ **エラー型**: なし
- **対象更新**: S1（ヒアリングエンジン）／空き検出の再開性 ／ **TC**: （割当待ち）

## FR-32

### AC-32-1（正常）

- **Given**: fill=R 指定スロット（例: 媒体標準指標）と、出典 URL・取得日時つきの Web 検索結果（鮮度 90 日以内） ／ **When**: リサーチ起草を実行する ／ **Then**: 全値に出典 URL が紐付いた draft が生成され、structure_checked 日付が付与され、拒否ログは増えない
- **fixture**: seed: config.source_freshness_days=90、検索結果 mock = [{value:'CTR 中央値 1.5%', url:'`https://source.example.test/report`', fetched_at:今日}]
- **観測点**: draft の出典 URL 列／structure_checked 日付／構造化ログ件数 ／ **期待状態**: draft 1 件（全値出典つき・未昇格の draft 状態）
- **期待 DB 差分**: draft +1 件、evidence +1 行（operation_log — Web 取得） ／ **期待証跡**: draft の出典 URL 列＋取得の operation_log 証跡
- **禁止副作用**: draft の正本への自動昇格・外部への書込み ／ **エラー型**: なし
- **対象更新**: S1（リサーチエンジン）／fillers.draft_research ／ **TC**: （割当待ち）

### AC-32-2（拒否）

- **Given**: 出典 URL のない値（記憶ベースの媒体仕様）を含む起草要求 ／ **When**: draft への書込みを実行する ／ **Then**: 出典なし値は UnsourcedValueRejected で破棄され draft に含まれず、拒否理由が記録される（出典ありの値のみ draft 化）
- **fixture**: seed: 検索結果 mock = [{value:'投稿上限 100 件/日', url:null}, {value:'CTR 1.5%', url:'`https://source.example.test`'}]
- **観測点**: raise される例外型（値単位の拒否）／draft の内容／構造化ログ ／ **期待状態**: draft に出典あり 1 値のみ（出典なし値 0 件）
- **期待 DB 差分**: draft +1 件（1 値のみ）、構造化ログ +1 行（拒否） ／ **期待証跡**: 出典なし値の拒否ログ（値と拒否理由）
- **禁止副作用**: 出典なし値の draft・正本への混入 ／ **エラー型**: UnsourcedValueRejected
- **対象更新**: S1（リサーチエンジン）／fillers.validate_source ／ **TC**: （割当待ち）

### AC-32-3（境界・復旧）

- **Given**: Web 検索結果が 0 件のスロットと、鮮度がちょうど 90 日・91 日の 2 出典 ／ **When**: リサーチ起草を実行する ／ **Then**: 0 件スロットは draft に含まれず未充足のまま残り、90 日出典は採用・91 日出典は StaleSourceRejected で drop される
- **fixture**: seed: config.source_freshness_days=90、スロット A = 検索 0 件、スロット B = fetched_at 90 日前と 91 日前の 2 出典
- **観測点**: draft の内容（スロット A 不在・スロット B は 90 日出典のみ）／構造化ログ ／ **期待状態**: スロット A 未充足維持、スロット B は境界内出典のみで draft 化
- **期待 DB 差分**: draft +1 件（スロット B のみ）、構造化ログ +1 行（鮮度拒否） ／ **期待証跡**: 鮮度切れ出典の拒否ログ（G-SRC-FRESH）
- **禁止副作用**: 空値・鮮度切れ値による draft の充填（fail-open） ／ **エラー型**: StaleSourceRejected
- **対象更新**: S1（リサーチエンジン）／鮮度境界判定 ／ **TC**: （割当待ち）

## FR-33

### AC-33-1（正常）

- **Given**: config に retry_limit=3 の既存行があり、reason つきの変更要求（retry_limit=5） ／ **When**: 設定変更（INSERT）と変更後の参照を実行する ／ **Then**: 新行が INSERT され（旧行は不変）、参照は新値 5 を返し、変更前の値 3 と reason が履歴から取得できる
- **fixture**: seed: config 1 行（key='retry_limit', value_json='3'）、変更要求 = {value:'5', reason:'S1 移行に伴う緩和', changed_by_agent_id:1}
- **観測点**: config SELECT（key='retry_limit' の全行）／有効値解決 API の戻り値 ／ **期待状態**: 有効値 = 5、履歴 2 行（supersedes_config_id が旧行を参照）
- **期待 DB 差分**: config +1 行（INSERT のみ — 旧行の UPDATE なし） ／ **期待証跡**: config 履歴行（旧値 3・新値 5・reason）
- **禁止副作用**: 既存 config 行の UPDATE/DELETE ／ **エラー型**: なし
- **対象更新**: S0.1（config 管理）／config.set・config.get ／ **TC**: （割当待ち）

### AC-33-2（拒否）

- **Given**: 既存 config 行への直接 UPDATE 文と、reason 空の変更要求 ／ **When**: UPDATE 実行と reason なし INSERT を試みる ／ **Then**: UPDATE は保護トリガの RAISE(ABORT) で ConfigAppendOnlyViolation、reason なしは ConfigReasonMissing で拒否され、config は変化しない
- **fixture**: seed: config 1 行（key='spend_cap_monthly', value_json='5000'）、UPDATE 文 = SET value_json='99999'、INSERT 要求 = {reason:''}
- **観測点**: raise される例外型／config SELECT（行数・値の不変性） ／ **期待状態**: config 1 行のまま（値 5000 不変）
- **期待 DB 差分**: 差分なし ／ **期待証跡**: 構造化ログの拒否行（append-only 違反・reason 欠落）
- **禁止副作用**: config 行の値変更・reason なし行の混入 ／ **エラー型**: ConfigAppendOnlyViolation／ConfigReasonMissing
- **対象更新**: S0.1（config 管理）／append-only トリガ＋事前検証 ／ **TC**: （割当待ち）

### AC-33-3（境界・復旧）

- **Given**: config に存在しない key の参照要求（安全側既定値表にある key とない key の 2 種） ／ **When**: 有効値の解決を実行する ／ **Then**: 既定値表にある key は保守的既定値を返し、ない key は拒否側へ倒れる（暗黙の fail-open 値を返さない）
- **fixture**: seed: config 空、既定値表 = {spend_cap_monthly: 5000}、参照 key = 'spend_cap_monthly' と 'unknown_key'
- **観測点**: 参照 API の戻り値／raise される例外型 ／ **期待状態**: spend_cap_monthly = 5000（保守的既定値）、unknown_key = 解決拒否
- **期待 DB 差分**: 差分なし（参照は読み取りのみ） ／ **期待証跡**: なし（正常参照）／拒否ログ（unknown_key）
- **禁止副作用**: 未定義 key への暗黙値（0・None 等）の返却 ／ **エラー型**: ConfigKeyUnresolved（unknown_key 側のみ）
- **対象更新**: S0.1（config 管理）／既定値フォールバック ／ **TC**: （割当待ち）

## FR-34

### AC-34-1（正常）

- **Given**: active な business_profile A が存在する状態で、別事業のプロファイル B の登録要求 ／ **When**: プロファイル B を登録し、各プロファイルのスコープ付きクエリを実行する ／ **Then**: A・B が共存し（A の行・参照データは不変）、各スコープのクエリは自プロファイルの行のみを返す
- **fixture**: seed: business_profiles 1 行（profile_key='brand-a', status='active'）＋brand_plans 1 行（A 所属）、登録要求 = {profile_key:'brand-b', name:'事業B', profile_json:{...}}
- **観測点**: business_profiles SELECT（2 行共存）／スコープ付き brand_plans SELECT の結果件数 ／ **期待状態**: business_profiles 2 行、B スコープの brand_plans = 0 件・A スコープ = 1 件
- **期待 DB 差分**: business_profiles +1 行、他テーブル差分なし ／ **期待証跡**: business_profiles の複数行共存（SELECT で確認）
- **禁止副作用**: A の行・A 所属データの変更・コードやワークフロー定義の修正の必要 ／ **エラー型**: なし
- **対象更新**: S1（プロファイル管理）／profiles.register・ストア層スコープ解決 ／ **TC**: （割当待ち）

### AC-34-2（拒否）

- **Given**: プロファイル A のスコープで動作中の処理から、プロファイル B に属する brand_plans 行への参照・書込み要求 ／ **When**: 越境の SELECT と UPDATE をストア層経由で実行する ／ **Then**: いずれも CrossProfileAccessDenied で拒否され、B の行は返らず・変わらず、越境拒否が証跡に残る
- **fixture**: seed: business_profiles 2 行（A/B）、brand_plans 1 行（B 所属）、アクセス要求 = scope=A で B の brand_plan id を指定
- **観測点**: raise される例外型／brand_plans SELECT（B 行の不変性）／構造化ログ ／ **期待状態**: B の brand_plans 行が不変・A へのデータ流出 0 件
- **期待 DB 差分**: 差分なし、構造化ログ +1 行（越境拒否） ／ **期待証跡**: 越境アクセスの拒否ログ（要求スコープ・対象行・理由）
- **禁止副作用**: 他プロファイル行の返却・変更（越境参照・越境書込み） ／ **エラー型**: CrossProfileAccessDenied
- **対象更新**: S1（プロファイル管理）／ストア層スコープ強制（BR-I1） ／ **TC**: （割当待ち）

### AC-34-3（境界・復旧）

- **Given**: archived に遷移済みのプロファイルと、既存 profile_key と重複する登録要求 ／ **When**: archived プロファイルへの新規書込み・読取と、重複 key の登録を実行する ／ **Then**: archived への読取は成功・新規書込みは拒否され、重複 key の登録は ProfileKeyConflict で拒否される（既存行は不変）
- **fixture**: seed: business_profiles 1 行（profile_key='brand-a', status='archived'）、登録要求 = {profile_key:'brand-a'}
- **観測点**: 読取 API の戻り値／raise される例外型／business_profiles SELECT ／ **期待状態**: business_profiles 1 行のまま（archived・不変）
- **期待 DB 差分**: 差分なし ／ **期待証跡**: 書込み拒否・重複拒否のログ
- **禁止副作用**: archived プロファイルへの新規業務行の追加・既存行の上書き登録 ／ **エラー型**: ProfileKeyConflict（重複側）／ArchivedProfileWriteDenied（書込み側）
- **対象更新**: S1（プロファイル管理）／status 境界・UNIQUE 制約 ／ **TC**: （割当待ち）

## FR-41

### AC-41-1（正常）

- **Given**: config に notion のレジストリ行（優先 mcp・fallback browser）が投入済みで、経路をコードに埋め込んだ分岐が存在しない状態 ／ **When**: notion の経路解決を実行し、その後 config INSERT で優先経路を browser に変更して再解決する ／ **Then**: 1 回目は mcp、2 回目は browser が返り、切替はレジストリ行の変更のみで反映される（コード変更なし — AC-41 原文）
- **fixture**: seed: config('registry.notion', {"primary":"mcp","fallback":"browser","auth":"mcp_oauth"})、変更は同 key の config INSERT（履歴保持）
- **観測点**: resolve_route の戻り値（route_type）／config SELECT（2 行の履歴）／operation_log 件数 ／ **期待状態**: 最新 config 行の宣言どおりの経路が返る
- **期待 DB 差分**: config +1 行（経路変更 INSERT）。operation_log 差分なし ／ **期待証跡**: なし（正常解決は証跡不要）
- **禁止副作用**: コード側分岐による経路決定・operation_log への拒否行追加・外部 HTTP 呼出（0 回） ／ **エラー型**: なし
- **対象更新**: S0.2（CMP-07 接続レジストリ）／registry.resolve_route ／ **TC**: （割当待ち）

### AC-41-2（拒否）

- **Given**: レジストリ未登録のサービス（unknown_svc）と、有償 API 例外宣言を持たないサービス（note）への有償経路要求 ／ **When**: unknown_svc の経路解決と、note の route_type=api（有償）強制解決を要求する ／ **Then**: 前者は RouteNotRegistered、後者は PaidRouteDenied で拒否され、いずれも operation_log に理由が残る
- **fixture**: seed: config('registry.note', {"primary":"browser"})（paid_exception なし）、unknown_svc の registry 行なし
- **観測点**: raise される例外型／operation_log SELECT（service・理由） ／ **期待状態**: 経路は 1 件も返却されない
- **期待 DB 差分**: operation_log +2 行（未登録拒否・有償経路拒否） ／ **期待証跡**: operation_log 拒否行（service・要求経路・理由）
- **禁止副作用**: 有償 API への接続試行（外部 HTTP 呼出 0 回）・spend_ledger への行追加 ／ **エラー型**: RouteNotRegistered／PaidRouteDenied
- **対象更新**: S0.2（CMP-07 接続レジストリ） ／ **TC**: （割当待ち）

### AC-41-3（境界・復旧）

- **Given**: registry.gtm の JSON 値が破損（json_valid 不成立相当の型不一致）しており、fallback 宣言のないサービス（instagram）の第一経路が失敗通知済みの状態 ／ **When**: gtm と instagram の経路解決を実行する ／ **Then**: 破損行は解決不能として拒否（fail-close — 推測で経路を返さない）、fallback なしの第一経路失敗は RouteNotRegistered で経路なしとなり呼出元を escalated 誘導する
- **fixture**: seed: config('registry.gtm', "broken-not-json")、config('registry.instagram', {"primary":"api","paid_exception":false}) ＋ instagram 第一経路の失敗通知
- **観測点**: raise される例外型／operation_log SELECT ／ **期待状態**: 両要求とも経路返却 0 件
- **期待 DB 差分**: operation_log +2 行（破損拒否・経路なし） ／ **期待証跡**: operation_log 拒否行（理由 = registry 行破損／fallback なし）
- **禁止副作用**: 破損行からの部分的な経路返却（fail-open）・外部 HTTP 呼出（0 回） ／ **エラー型**: RouteNotRegistered
- **対象更新**: S0.2（CMP-07 接続レジストリ） ／ **TC**: （割当待ち）

## FR-42

### AC-42-1（正常）

- **Given**: status=active な playbooks 行（note の書込み操作）と、seed 固定の Rng・Clock 注入、日次上限未達（当日書込み 0 件） ／ **When**: mock 媒体への書込み系ブラウザ操作を 3 連続で実行する ／ **Then**: 操作は playbook の手順どおり成功し、last_success_at が更新され、連続操作の間隔がすべて 1〜5 秒の範囲内で seed から再現可能な値として構造化ログに残る
- **fixture**: seed: playbooks(service='note', operation='post', route_type='browser', status='active')、config.rate.note.daily_write_cap=10、Rng(seed=42) 注入、mock ブラウザ
- **観測点**: playbooks.last_success_at SELECT／構造化ログ（seed・間隔値）／external_operations.status ／ **期待状態**: external_operations 3 行すべて confirmed、playbook は active のまま
- **期待 DB 差分**: external_operations +3 行、operation_log +3 行、playbooks.last_success_at UPDATE ／ **期待証跡**: operation_log 行（external_operation_id つき）＋構造化ログの seed=42 と間隔 3 値
- **禁止副作用**: 固定間隔での連続送信（3 間隔が全一致）・範囲外（1 秒未満/5 秒超）の間隔・idempotency key の重複 ／ **エラー型**: なし
- **対象更新**: S1（CMP-08 ブラウザ基盤）／browser.execute_playbook ／ **TC**: （割当待ち）

### AC-42-2（拒否）

- **Given**: X への書込み操作要求と、当日すでに書込み 10 件（上限）に達した note への 11 件目の書込み要求 ／ **When**: 両方の書込み系ブラウザ操作を実行する ／ **Then**: X は ProhibitedMediaWrite（BR-M-X-4）、note は RateLimitExceeded で拒否され、外部送信は 0 回で operation_log に理由が残る
- **fixture**: seed: 当日分 external_operations に note 書込み confirmed 10 行、X 用 playbook は書込み系を投入しない、config.rate.note.daily_write_cap=10
- **観測点**: raise される例外型／operation_log SELECT／external_operations 件数 ／ **期待状態**: external_operations に新規 sent/confirmed 行なし
- **期待 DB 差分**: operation_log +2 行（X 拒否・上限拒否）。external_operations 差分なし ／ **期待証跡**: operation_log 拒否行（media・理由 = prohibited／daily_cap）
- **禁止副作用**: 外部サイトへのブラウザ書込み送信（0 回）・playbooks.last_success_at の更新 ／ **エラー型**: ProhibitedMediaWrite／RateLimitExceeded
- **対象更新**: S1（CMP-08 ブラウザ基盤） ／ **TC**: （割当待ち）

### AC-42-3（境界・復旧）

- **Given**: 書込み送信直後に external_operations が sent のままプロセスが強制終了し、mock 媒体側では操作が成功済みの状態（最危険 kill point） ／ **When**: 再起動後に §3.3 の再開規則で当該操作を照合・再開する ／ **Then**: リモート照合（idempotency key / remote object ID）で成功が確認され confirmed 化＋証跡補完され、再送は発生しない。照合不能ケースは unknown とし escalate する
- **fixture**: seed: external_operations(status='sent', idempotency_key='k1') 1 行＋mock 媒体に k1 成功応答、照合不能ケース用に mock が k2 を未知と応答する sent 行 1 行
- **観測点**: external_operations.status SELECT／mock 媒体の受信回数カウンタ／tasks.status ／ **期待状態**: k1 = confirmed、k2 = unknown で対象タスク escalated
- **期待 DB 差分**: external_operations 2 行 UPDATE（confirmed/unknown）、operation_log +2 行（照合結果）、state_transitions +1 行（escalate） ／ **期待証跡**: operation_log 行（照合結果・external_operation_id 補完）
- **禁止副作用**: 同一 idempotency key の再送（mock 受信カウンタ増加 0）・unknown の confirmed 化 ／ **エラー型**: なし（k2 側は escalate 遷移 — OperationUnverifiable 記録）
- **対象更新**: S1（CMP-08）／recovery.reconcile_sent ／ **TC**: （割当待ち）

## FR-43

### AC-43-1（正常）

- **Given**: セレクタ不一致で失敗通知された playbooks 行（status=active→broken 化対象）と、再解析で正セレクタが取得できる mock ページ ／ **When**: 破損検知から自己修復（再解析→地図再生成→検証）を実行する ／ **Then**: playbook が新 selector_json で UPDATE され status=active・consecutive_failures=0 に戻り、検知と再生成の試行が operation_log に各 1 回残る
- **fixture**: seed: playbooks(service='note', status='active', consecutive_failures=2, selector_json=旧セレクタ)、mock ページ DOM に新セレクタ
- **観測点**: playbooks SELECT（status・selector_json・consecutive_failures）／operation_log SELECT ／ **期待状態**: playbook = active（新地図）
- **期待 DB 差分**: playbooks 1 行 UPDATE、operation_log +2 行（検知・再生成成功） ／ **期待証跡**: operation_log 行（不一致セレクタ・再生成結果）＋再解析時 screenshot evidence
- **禁止副作用**: 再解析中の外部サイトへの書込み（mock 書込み受信 0 回）・2 回目の再生成試行 ／ **エラー型**: なし
- **対象更新**: S2（地図自己修復 FN-405）／playbook.self_heal ／ **TC**: （割当待ち）

### AC-43-2（拒否）

- **Given**: 再解析しても検証手順が通らない mock ページ（対象要素が存在しない）と、破損通知済みの playbooks 行 ／ **When**: 自己修復を実行し 1 回目の再生成が失敗する ／ **Then**: 追加試行は行われず playbook は broken のまま、対象タスクが escalated に遷移し FR-46 経路の通知が送出される（BR-H3）
- **fixture**: seed: playbooks(status='active', consecutive_failures=3)、mock ページから対象要素を削除、対象 task = in_progress
- **観測点**: playbooks.status／tasks.status／state_transitions SELECT／通知 mock の送出記録 ／ **期待状態**: playbook = broken、task = escalated
- **期待 DB 差分**: playbooks.status UPDATE（broken）、state_transitions +1 行（escalate）、operation_log +2 行（検知・再生成失敗） ／ **期待証跡**: operation_log 行（再生成失敗理由）＋escalate 遷移行
- **禁止副作用**: 2 回目以降の自動再生成試行・broken 地図での書込み操作続行・地図の推測書換え ／ **エラー型**: PlaybookRepairFailed（escalate 事由として記録）
- **対象更新**: S2（地図自己修復 FN-405） ／ **TC**: （割当待ち）

### AC-43-3（境界・復旧）

- **Given**: 再生成の途中（broken 化コミット後・地図 UPDATE 前）でプロセスが強制終了した状態 ／ **When**: 再起動後に破損中 playbook を検出して自己修復を再実行する ／ **Then**: status=broken が残っているため再生成が最初からやり直され（読取りのみで外部副作用なし）、成功すれば active へ復帰する。status=retired の行は修復対象外として即 escalated となる
- **fixture**: seed: playbooks 2 行（status='broken' の note 行／status='retired' の kdp 行）、mock ページは note の正セレクタを提供
- **観測点**: playbooks SELECT（再実行後の status）／operation_log SELECT／tasks.status（retired 側） ／ **期待状態**: note 行 = active、kdp 行 = retired のまま対象タスク escalated
- **期待 DB 差分**: playbooks 1 行 UPDATE（active）、state_transitions +1 行（retired 側 escalate）、operation_log +2 行以上 ／ **期待証跡**: operation_log 行（再開後の再生成試行・retired 拒否）
- **禁止副作用**: 中間状態の地図（部分更新）での操作再開・retired 行の自動復活・外部書込み ／ **エラー型**: PlaybookRepairFailed（retired 側）
- **対象更新**: S2（地図自己修復 FN-405）／recovery 経路 ／ **TC**: （割当待ち）

## FR-44

### AC-44-1（正常）

- **Given**: 成立済みペア ID（pair_plan_quality status=passed）と approved approval（binding 3 項目一致）を持つ記事タスク、接続先はローカル Docker WP ／ **When**: 下書き作成（key=k-draft）→公開（key=k-pub）を順に実行する ／ **Then**: 各操作が別 external_operations 行として prepared→sent→confirmed で遷移し、公開後に canonical URL の published_url evidence と assets 参照が登録される
- **fixture**: seed: pair_plan_quality(passed) 1 行、approvals(approved・binding 一致) 1 行、Docker WP（または WP mock）稼働、idempotency key を操作別に付与
- **観測点**: external_operations SELECT（2 行の status 遷移）／WP 側 post status／evidence・assets SELECT ／ **期待状態**: 下書き行・公開行とも confirmed、WP 上で記事 published
- **期待 DB 差分**: external_operations +2 行、operation_log +2 行、evidence +1 行（published_url）、assets +1 行（canonical_url・wp_post_id） ／ **期待証跡**: published_url evidence（url・wp_post_id・external_operation_id・asset_id）＋operation_log 2 行
- **禁止副作用**: 下書きと公開の idempotency key 共有・Docker 以外の endpoint への送信・credential の平文ログ出力 ／ **エラー型**: なし
- **対象更新**: S0.2（CMP-10 WP REST コネクタ）／WF-WP-2 手順 2・4 ／ **TC**: （割当待ち）

### AC-44-2（拒否）

- **Given**: 成立済みペア ID なしの書込み要求と、書込み先が Docker 以外の本番 WP URL に設定された書込み要求 ／ **When**: 両方の WP REST 書込みを実行する ／ **Then**: 前者は PairRequired、後者は ProductionWriteDenied で拒否され、外部 HTTP 呼出は 0 回、operation_log に理由が残る（AC-44 原文の拒否側＋環境契約 §6）
- **fixture**: seed: pair_plan_quality 空、config の WP endpoint を '`https://real-site.example.com`' に設定したケースを用意、WP mock の受信カウンタ 0 初期化
- **観測点**: raise される例外型／operation_log SELECT／WP mock 受信カウンタ ／ **期待状態**: external_operations に prepared 行すら作られない（検証は送信前）
- **期待 DB 差分**: operation_log +2 行（ペアなし拒否・本番書込み拒否）。external_operations 差分なし ／ **期待証跡**: operation_log 拒否行（理由 = pair 未成立／非 Docker endpoint）
- **禁止副作用**: 外部 HTTP 呼出（受信カウンタ 0 のまま）・本番 WP への一切の書込み ／ **エラー型**: PairRequired／ProductionWriteDenied
- **対象更新**: S0.2（CMP-10 WP REST コネクタ） ／ **TC**: （割当待ち）

### AC-44-3（境界・復旧）

- **Given**: 公開送信が sent のままクラッシュし WP 側は公開成功済みの状態（最危険 kill point — s0-contract §8）と、同一 idempotency key での再要求 ／ **When**: 再起動後の §3.3 再開と、同一 key の公開再要求を実行する ／ **Then**: WP 側照合（post ID / idempotency key）で成功確認して confirmed 化・証跡補完のみ行い再送しない。同一 key の再要求は UNIQUE 制約で既存行に照合され二重公開が発生しない
- **fixture**: seed: external_operations(status='sent', idempotency_key='k-pub') 1 行＋WP mock に k-pub の公開成功状態、再要求も key='k-pub'
- **観測点**: external_operations.status／WP mock の公開 API 受信回数／evidence SELECT ／ **期待状態**: k-pub 行 = confirmed、WP 上の公開記事は 1 件のまま
- **期待 DB 差分**: external_operations 1 行 UPDATE（confirmed・response 補完）、evidence +1 行（published_url 補完）、operation_log +1 行 ／ **期待証跡**: operation_log 照合行＋published_url evidence（external_operation_id 整合）
- **禁止副作用**: 公開 API の再送（mock 受信回数増加 0）・external_operations の重複行・二重公開 ／ **エラー型**: なし
- **対象更新**: S0.2（CMP-10）／recovery.reconcile_sent（WF-WP-2 手順 4） ／ **TC**: （割当待ち）

## FR-45

### AC-45-1（正常）

- **Given**: Notion mock に計画ページ（last_edited_time 更新済み）があり、レビュー成立済みの結果データが SQLite にある状態 ／ **When**: スプリント開始時の読取りと、レビュー成立時の書戻し（2,500 字 — 分割必要）を実行する ／ **Then**: 計画が draft として SQLite に保存され、書戻しは 2,000 字境界でブロック分割・3 req/秒以下で送信され、external_operations と operation_log 証跡が残る
- **fixture**: seed: Notion mock（計画ページ 1 件・書込み受付）、learnings/sprints に書戻し元データ、config.rate.notion.req_per_sec=3、書戻し本文 2,500 字
- **観測点**: SQLite の draft 保存行／Notion mock の受信ブロック（2 分割・レート）／external_operations.status ／ **期待状態**: 読取り draft 保存済み、書戻し操作 confirmed
- **期待 DB 差分**: external_operations +1 行（confirmed）、operation_log +1 行、draft 保存 +1 行 ／ **期待証跡**: operation_log 行（service=notion・external_operation_id・request_fingerprint）
- **禁止副作用**: 2,000 字超の単一ブロック送信・3 req/秒超過・ループ判定への Notion 値の混入 ／ **エラー型**: なし
- **対象更新**: S1（Notion 同期 FN-408）／notion.sync_read・sync_writeback ／ **TC**: （割当待ち）

### AC-45-2（拒否）

- **Given**: Notion mock が全要求に接続エラーを返す障害状態と、進行中の loop_run・tasks ／ **When**: スプリント開始の読取り同期を実行し、その後ループ本体のタスク遷移を継続実行する ／ **Then**: 同期タスクのみ NotionUnavailable で failed となり operation_log に記録される一方、loop_run と他タスクは SQLite のみで正常に進行する（Notion は判定に関与しない）
- **fixture**: seed: Notion mock を全断（connection error）、loop_runs 1 行進行中＋依存しない task 1 件
- **観測点**: 同期 task の status／loop_runs・他 task の遷移可否／operation_log SELECT ／ **期待状態**: 同期 task = failed、loop_run は継続進行
- **期待 DB 差分**: operation_log +1 行（NotionUnavailable）、state_transitions に同期 task の failed 遷移＋他 task の正常遷移 ／ **期待証跡**: operation_log 行（service=notion・理由 = unavailable）
- **禁止副作用**: ループ本体の停止・待機（Notion 障害の波及）・障害中の書戻し再送連打 ／ **エラー型**: NotionUnavailable
- **対象更新**: S1（Notion 同期 FN-408） ／ **TC**: （割当待ち）

### AC-45-3（境界・復旧）

- **Given**: 前回読取りカーソル直後の同一分内に Notion 側で計画が更新されており（分単位精度の境界）、書戻しは sent のままクラッシュした状態 ／ **When**: 再起動後にポーリング読取りと書戻し再開（§3.3 照合）を実行する ／ **Then**: カーソル余裕により境界更新が重複取得され冪等 upsert で 1 件に収束し取りこぼさない。書戻しは mock 照合で confirmed 化され再送されない
- **fixture**: seed: sync カーソル=T、Notion mock に last_edited_time=T（同一分）の更新、external_operations(status='sent', idempotency_key='k-nt') ＋ mock に k-nt 成功応答、config.sync.notion.cursor_margin_min=2
- **観測点**: draft 保存行数（重複なし）／external_operations.status／Notion mock 書込み受信回数 ／ **期待状態**: 境界更新 1 件が draft に反映、k-nt = confirmed
- **期待 DB 差分**: draft 1 行 upsert（重複行なし）、external_operations 1 行 UPDATE、operation_log +1 行 ／ **期待証跡**: operation_log 照合行（external_operation_id 補完）
- **禁止副作用**: 境界更新の取りこぼし・draft の重複行・書戻しの再送（mock 受信増加 0） ／ **エラー型**: なし
- **対象更新**: S1（Notion 同期 FN-408）／cursor・recovery 経路 ／ **TC**: （割当待ち）

## FR-46

### AC-46-1（正常）

- **Given**: 公開待ちタスクと、binding 3 項目（対象記事・publish 操作・時点）を明記した承認要求、mock 通知 transport が approved を応答する状態 ／ **When**: 承認要求を送出し、応答受領後に binding 3 項目一致の公開を実行する ／ **Then**: 要求が通知され、応答が approvals に証跡化されるまで対象タスクは進行せず（waiting）、approved 受領後に approval evidence が登録され公開が許可される（AC-46 原文）
- **fixture**: seed: task(pending) 1 件、mock transport（approved・responder_ref='po'）、binding = (post:123, publish, 2026-08-01T10:00)
- **観測点**: approvals SELECT（decision・binding・evidence_id）／応答前後の tasks.status／公開ゲートの通過可否 ／ **期待状態**: approvals = approved・evidence 相互整合、task = 進行再開
- **期待 DB 差分**: approvals +1 行（pending→approved UPDATE）、evidence +1 行（kind=approval）、state_transitions +2 行（waiting→in_progress 系） ／ **期待証跡**: approval evidence（decision=approved・binding 3 項目・approvals.evidence_id 整合）
- **禁止副作用**: 応答受領前の公開実行・approvals 行の書換えによる decision 変更 ／ **エラー型**: なし
- **対象更新**: S0.2（CMP-11 承認通知）／WF-WP-2 手順 3 ／ **TC**: （割当待ち）

### AC-46-2（拒否）

- **Given**: binding_at のみ異なる approved approval を持つ公開要求と、decision=rejected の応答を受けた別タスク ／ **When**: binding 不一致のままの公開と、rejected 後のタスク進行を試みる ／ **Then**: 公開は ApprovalBindingMismatch で拒否され（3 項目の 1 つでも不一致なら通らない）、rejected は non_retryable_failure として task が failed になり自動再試行されない
- **fixture**: seed: approvals(approved, binding_at='2026-08-01T10:00') に対し公開時点 '2026-08-01T11:00' を提示、別 task に mock transport が rejected 応答
- **観測点**: raise される例外型／operation_log SELECT／tasks.status・state_transitions ／ **期待状態**: 公開 0 件、rejected 側 task = failed（retry_count 増加なし）
- **期待 DB 差分**: operation_log +1 行（binding 不一致）、approvals 1 行 UPDATE（rejected）、state_transitions +1 行（failed） ／ **期待証跡**: operation_log 拒否行（不一致項目の明示）＋approvals rejected 行
- **禁止副作用**: 不一致のままの公開（外部書込み 0 回）・rejected タスクの自動リトライ・escalated への迂回 ／ **エラー型**: ApprovalBindingMismatch／NonRetryableFailure
- **対象更新**: S0.2（CMP-11 承認通知） ／ **TC**: （割当待ち）

### AC-46-3（境界・復旧）

- **Given**: config.approval_retry_limit=2 で、mock transport が常に expired を返す承認要求と、pending 応答のままクラッシュ→再起動したタスク ／ **When**: expired の再要求ループを上限まで進め、pending 側は再起動後に待機再開する ／ **Then**: expired は再要求で待機を継続し、再要求 2 回目（上限到達）で escalated に遷移する。pending 側は approvals.decision から待機状態が復元され、二重の承認要求は作られない
- **fixture**: seed: config('approval_retry_limit', 2)、mock transport（常時 expired）、pending 行 1 件（UNIQUE binding）を残して再起動
- **観測点**: approvals 行数と decision 履歴／tasks.status／state_transitions SELECT ／ **期待状態**: expired 側 task = escalated、pending 側 = waiting 継続（要求は 1 件のまま）
- **期待 DB 差分**: approvals は再要求分のみ増加（上限到達で停止）、state_transitions +1 行（escalate）。pending 側 approvals 差分なし ／ **期待証跡**: approvals の expired 履歴＋escalate 遷移行（事由 = approval_retry_limit 到達）
- **禁止副作用**: 上限超過後の再要求継続（無限待機）・同一 binding の重複 approvals 行・expired の failed 化（rejected と混同） ／ **エラー型**: ApprovalRetryExhausted（escalate 事由として記録）
- **対象更新**: S0.2（CMP-11 承認通知）／expired 再要求経路 ／ **TC**: （割当待ち）

## FR-47

### AC-47-1（正常）

- **Given**: 暗号化ストア（mock キーチェーン）に WP の Application Password が投入済みで、コネクタが接続を要求する状態 ／ **When**: 秘匿値を実行時注入して外部操作（mock WP 接続）を 1 件実行し、リポジトリ・SQLite・ログ・evidence を全文検索する ／ **Then**: 接続は成功し、平文 credential の検出が 0 件である（AC-47 原文 — 秘匿値はメモリ上のみで永続化されない）
- **fixture**: seed: mock キーチェーンに secret='wp-app-pass-XYZ'、操作後に repo/DB/ログへ 'wp-app-pass-XYZ' の全文検索を実行
- **観測点**: 接続結果／全文検索ヒット件数（repo grep・SQLite LIKE・ログ grep） ／ **期待状態**: 接続成功・平文検出 0 件
- **期待 DB 差分**: external_operations/operation_log は操作分のみ（credential 列・平文なし） ／ **期待証跡**: operation_log 行（external_operation_id — 秘匿値を含まない）
- **禁止副作用**: SQLite・repo・ログ・evidence への平文 credential 書込み（検索ヒット 1 件でも fail） ／ **エラー型**: なし
- **対象更新**: S0.2（CMP-07 秘匿ストア）／secrets.get・masking 層 ／ **TC**: （割当待ち）

### AC-47-2（拒否）

- **Given**: 秘匿ストアに未投入のサービス（notion）への接続要求と、operation_log へ書き出される文字列に secret 値が混入したケース ／ **When**: notion 接続と、混入文字列のログ書出しを実行する ／ **Then**: 接続は SecretUnavailable で開始されず（外部呼出 0 回）、混入書出しはマスクされた上で CredentialLeakDetected が記録され書出し元タスクが escalated へ誘導される
- **fixture**: seed: mock キーチェーン（notion キーなし）、書出し文字列 = 'auth failed: token=wp-app-pass-XYZ'（既知 secret 混入）
- **観測点**: raise される例外型／operation_log SELECT（マスク後文字列）／tasks.status ／ **期待状態**: 接続 0 件、ログには伏字（token=***）のみ、書出し元 task = escalated 誘導
- **期待 DB 差分**: operation_log +2 行（SecretUnavailable・CredentialLeakDetected — いずれも平文なし） ／ **期待証跡**: operation_log 検知行（マスク済み — 秘匿値そのものを含まない）
- **禁止副作用**: 平文のままのログ永続化・秘匿値なしでの外部接続試行（外部 HTTP 呼出 0 回） ／ **エラー型**: SecretUnavailable／CredentialLeakDetected
- **対象更新**: S0.2（CMP-07 秘匿ストア） ／ **TC**: （割当待ち）

### AC-47-3（境界・復旧）

- **Given**: 保管済みセッションが期限切れになった状態と、テスト credential を本番 endpoint に組み合わせた設定（環境契約 §6 違反） ／ **When**: 期限切れセッションでの接続と、不一致組合せでの接続を実行し、その後 credential 再投入からタスクを再開する ／ **Then**: 期限切れは検知され再投入待ちの escalated（人の関与）へ、credential/endpoint 不一致は実行拒否となる。再投入後は同一タスク状態から再実行でき正常接続する
- **fixture**: seed: mock キーチェーンに expired セッション、test credential ＋ production endpoint の組合せ設定、再投入手順で有効値に上書き
- **観測点**: raise される例外型／tasks.status（escalated→再開）／operation_log SELECT ／ **期待状態**: 再投入前 = escalated・接続 0 件、再投入後 = 同一タスクが接続成功
- **期待 DB 差分**: operation_log +2 行（期限切れ・組合せ拒否）、state_transitions に escalate と再開の遷移 ／ **期待証跡**: operation_log 行（理由 = session expired／credential-endpoint mismatch — 平文なし）
- **禁止副作用**: 期限切れセッションでの外部送信・テスト credential の本番 endpoint 使用（fail-open）・再投入値の SQLite 保存 ／ **エラー型**: SecretUnavailable（期限切れ）／CredentialEndpointMismatch
- **対象更新**: S0.2（CMP-07 秘匿ストア）／再投入・再開経路 ／ **TC**: （割当待ち）

## FR-51

### AC-51-1（正常）

- **Given**: commit 済みの入力ソース（記事 HTML）を持つ git ワークスペースと、実行中の T-PROD task、Docker WP 接続 ／ **When**: 同一 commit・同一プロファイル（manuscript）でレンダリングを 2 回実行する ／ **Then**: 2 回とも同一の出力 SHA-256 が得られ（決定性）、assets 参照 1 行と file_hash 証跡が重複なく存在する
- **fixture**: seed: tasks に T-PROD 1 行（実行中）、fixture リポジトリ commit abc…（記事 HTML 1 件）、config.wp_target=docker、WP コネクタは mock（決定的応答）
- **観測点**: 1 回目と 2 回目の出力ファイル SHA-256 比較／assets SELECT／evidence SELECT (kind='file_hash') ／ **期待状態**: assets 1 行（content_hash = 出力 hash、wp_media_id あり）
- **期待 DB 差分**: assets +1 行、evidence +1 行（file_hash）、operation_log +1 行（WP アップ操作）— 2 回目は差分なし ／ **期待証跡**: evidence 行（kind=file_hash、value=出力 SHA-256、payload に file_path・algorithm=SHA-256）
- **禁止副作用**: 2 回目実行での assets/evidence の行増加・出力 hash の変動・本番 WP への書込み ／ **エラー型**: なし
- **対象更新**: S0.2（制作層）／content/renderer.render ／ **TC**: （割当待ち）

### AC-51-2（拒否）

- **Given**: 未 commit の編集（dirty 作業ツリー）を含む入力ソースと、接続先が本番 WP を指す registry 設定 ／ **When**: レンダリングと WP アップロードを要求する ／ **Then**: 未 commit ソースは UnversionedSourceRejected、本番 WP 宛は WpTargetDenied で拒否され、成果物・参照行が一切作られない
- **fixture**: seed: fixture リポジトリに未 commit 変更を作る／config.wp_target を docker 以外（prod 想定値）に seed
- **観測点**: raise される例外型／assets・evidence 件数／operation_log SELECT ／ **期待状態**: assets 空のまま、WP モックへの書込み呼出 0 回
- **期待 DB 差分**: operation_log +2 行（未 commit 拒否・接続先拒否）のみ ／ **期待証跡**: operation_log 拒否行（理由 = uncommitted source／wp target denied）
- **禁止副作用**: assets/evidence への行追加・WP（モック含む）への書込み呼出 ／ **エラー型**: UnversionedSourceRejected／WpTargetDenied
- **対象更新**: S0.2（制作層）／content/renderer 入口検査 ／ **TC**: （割当待ち）

### AC-51-3（境界・復旧）

- **Given**: WP アップロードは成功したが assets/evidence 登録前にプロセスが強制終了した状態 ／ **When**: 同一 task で レンダリングを再実行する ／ **Then**: content_hash 一致の既存 WP メディアを照合して再アップロードせず、参照登録のみ完了する（冪等再開）
- **fixture**: seed: WP モックに hash 一致のメディアを事前配置、assets/evidence は空（クラッシュ直後を再現）
- **観測点**: WP モックのアップロード呼出回数／assets・evidence SELECT ／ **期待状態**: assets 1 行（既存 wp_media_id を参照）、evidence 1 行
- **期待 DB 差分**: assets +1 行、evidence +1 行（file_hash）— WP への新規アップロード 0 回 ／ **期待証跡**: evidence 行（kind=file_hash、value=出力 SHA-256）
- **禁止副作用**: 同一実体の二重アップロード・assets の重複行 ／ **エラー型**: なし
- **対象更新**: S0.2（制作層）／renderer の再開経路 ／ **TC**: （割当待ち）

## FR-52

### AC-52-1（正常）

- **Given**: DesignSync モックがトークン集合 v3（hash T3）を返す構成と、トークン参照を含むレンダリング対象ソース ／ **When**: トークン取得→注入つきレンダリングを実行する ／ **Then**: 出力にトークン値が展開され、キャッシュが v3 に更新され、証跡 payload にトークン版数 v3・hash T3 が記録される
- **fixture**: seed: config.designsync_source=mock、DesignSync モック応答 = {version:'v3', tokens:{color.primary:'#123456'}}、キャッシュは v2 を事前配置
- **観測点**: 出力ファイル内のトークン展開値／キャッシュファイル内容／レンダリング証跡 payload ／ **期待状態**: キャッシュ = v3（hash T3）、出力に #123456 が展開
- **期待 DB 差分**: operation_log +1 行（取得成功）。業務テーブル差分なし ／ **期待証跡**: レンダリング証跡 payload の token_version='v3'・token_hash=T3・stale=false
- **禁止副作用**: トークン外の恣意的スタイル値の混入・キャッシュの破壊的更新（temp→rename 以外） ／ **エラー型**: なし
- **対象更新**: S1（制作層）／content/design_tokens.fetch_and_inject ／ **TC**: （割当待ち）

### AC-52-2（拒否）

- **Given**: DesignSync が到達不能で、トークンキャッシュも存在しない初期状態 ／ **When**: トークン注入つきレンダリングを実行する ／ **Then**: DesignTokenUnavailable が raise され、トークンなしの出力が生成されない（fail-close）
- **fixture**: seed: DesignSync モックを接続エラー応答に設定、config.designsync_cache_path 先を空にする
- **観測点**: raise される例外型／出力ディレクトリの内容／operation_log SELECT ／ **期待状態**: レンダリング出力 0 件
- **期待 DB 差分**: operation_log +1 行（取得失敗・キャッシュなし拒否）のみ ／ **期待証跡**: operation_log 拒否行（理由 = token unavailable, no cache）
- **禁止副作用**: トークン未適用出力の生成・assets/evidence への登録 ／ **エラー型**: DesignTokenUnavailable
- **対象更新**: S1（制作層）／design_tokens の fail-close 経路 ／ **TC**: （割当待ち）

### AC-52-3（境界・復旧）

- **Given**: DesignSync が到達不能だが、直近同期済みキャッシュ v2（hash T2、整合検証 OK）が存在する状態 ／ **When**: 規定回数の再試行後にトークン注入つきレンダリングを実行する ／ **Then**: キャッシュ v2 で継続し、証跡に stale=true と版数 v2 が記録される
- **fixture**: seed: DesignSync モック = タイムアウト応答、config.designsync_fetch_retry_max=2、キャッシュ v2 を hash 整合状態で配置
- **観測点**: 取得試行回数（モック呼出カウント）／出力のトークン展開値／証跡 payload ／ **期待状態**: レンダリング成功（v2 トークン適用）、キャッシュは v2 のまま
- **期待 DB 差分**: operation_log +1 行（フォールバック記録） ／ **期待証跡**: 証跡 payload の token_version='v2'・stale=true
- **禁止副作用**: 破損キャッシュの使用（hash 不一致時の続行）・再試行回数の超過呼出 ／ **エラー型**: なし
- **対象更新**: S1（制作層）／design_tokens のキャッシュフォールバック ／ **TC**: （割当待ち）

## FR-53

### AC-53-1（正常）

- **Given**: commit 済み台本と WP 登録済み素材資産（asset_id=1）、VOICEVOX モックが決定的 mp3 を返す構成 ／ **When**: voice パイプラインを同一入力で 2 回実行する ／ **Then**: 2 回とも同一出力 hash の mp3 が得られ、parent_asset_id=1 の assets 行と実行記録つき証跡が重複なく残る
- **fixture**: seed: assets に元記事資産 1 行、fixture 台本 commit、VOICEVOX/WP モック（決定的応答）、config.voicevox_endpoint=localhost モック
- **観測点**: 出力 mp3 の SHA-256（2 回比較）／assets SELECT（parent_asset_id）／evidence payload ／ **期待状態**: assets +1 行（asset_type=audio、parent_asset_id=1）
- **期待 DB 差分**: assets +1 行、evidence +1 行（file_hash＋実行記録 payload）— 2 回目は差分なし ／ **期待証跡**: evidence payload に入力参照（台本 commit・素材 asset_id）・ツール版数・出力 hash
- **禁止副作用**: localhost 以外への TTS 送信・2 回目実行での行増加・SQLite への mp3 実体格納 ／ **エラー型**: なし
- **対象更新**: S3+（制作層）／content/pipelines.voice ／ **TC**: （割当待ち）

### AC-53-2（拒否）

- **Given**: 存在しない素材 asset_id を参照する台本と、実行途中でエラー終了する ffmpeg モック ／ **When**: video パイプラインを実行する ／ **Then**: 参照不能は UnversionedSourceRejected、実行失敗は PipelineExecutionFailed で拒否され、部分出力が assets/WP に登録されない
- **fixture**: seed: 台本の素材参照 = asset_id 999（不在）／別ケース: ffmpeg モックを exit 1 に設定し中間 mp4 断片を temp に生成させる
- **観測点**: raise される例外型／assets・evidence 件数／temp 領域と WP モックの状態 ／ **期待状態**: assets 差分なし、WP への登録 0 件
- **期待 DB 差分**: operation_log +2 行（参照拒否・実行失敗）のみ ／ **期待証跡**: operation_log 拒否行（理由 = missing asset ref／pipeline failed at encode）
- **禁止副作用**: 部分出力（中間 mp4）の assets 登録・WP アップロード ／ **エラー型**: UnversionedSourceRejected／PipelineExecutionFailed
- **対象更新**: S3+（制作層）／pipelines の fail-close 経路 ／ **TC**: （割当待ち）

### AC-53-3（境界・復旧）

- **Given**: epub 生成の実行途中（pandoc 完了後・登録前）でプロセスが強制終了し、temp に生成物が残った状態 ／ **When**: 同一 task で epub パイプラインを再実行する ／ **Then**: temp の断片は採用されず破棄され、再実行が同一出力 hash に収束して登録が 1 回だけ完了する
- **fixture**: seed: temp 領域に前回断片ファイルを配置、assets/evidence は空、pandoc/WP モックは決定的応答
- **観測点**: temp 領域の掃除結果／出力 hash／assets・evidence 件数 ／ **期待状態**: assets 1 行・evidence 1 行（再実行分のみ）
- **期待 DB 差分**: assets +1 行、evidence +1 行 — 断片由来の行は 0 ／ **期待証跡**: evidence 行（kind=file_hash、value=再実行出力の SHA-256）
- **禁止副作用**: 前回断片の成果物採用・二重登録 ／ **エラー型**: なし
- **対象更新**: S3+（制作層）／pipelines の temp 破棄・再実行復旧 ／ **TC**: （割当待ち）

## FR-54

### AC-54-1（正常）

- **Given**: commit 済み成果物ソース（commit hash H1、40 桁）を持つ T-PROD task と、対応する審査 PASS 要求 ／ **When**: commit_hash 証跡化→review_pass 記録（commit_hash=H1）→hash からのソース復元を順に実行する ／ **Then**: PASS が H1 に束縛されて記録され、H1 の checkout で審査時と同一内容のソースが復元できる
- **fixture**: seed: fixture リポジトリ commit H1（記事ソース）、tasks に T-PROD/T-REVIEW 各 1 行、reviewer は author と別 agent
- **観測点**: evidence SELECT（kind IN ('commit_hash','review_pass') の commit_hash 列）／checkout 後のファイル hash 比較 ／ **期待状態**: review_pass 証跡の commit_hash 列 = H1、復元ソースの内容 hash = 証跡化時と一致
- **期待 DB 差分**: evidence +2 行（commit_hash・review_pass） ／ **期待証跡**: evidence（kind=commit_hash、value=H1、payload に repository・paths）／evidence（kind=review_pass、payload に result=PASS・commit_hash=H1・reviewer）
- **禁止副作用**: 既存証跡行の UPDATE/DELETE（append-only トリガ違反） ／ **エラー型**: なし
- **対象更新**: S0.2（制作層）／content/versioning.record_commit・bind_pass ／ **TC**: （割当待ち）

### AC-54-2（拒否）

- **Given**: task の commit_hash 証跡は H1 だが、PASS 記録要求が別 hash H2 を指定している状態（版すり替え相当） ／ **When**: review_pass 記録を要求する ／ **Then**: CommitHashMismatch で拒否され、review_pass 証跡が作られず operation_log に理由が残る
- **fixture**: seed: evidence に (task, commit_hash, H1) を事前投入、PASS 要求 = {commit_hash: H2, result: 'PASS'}
- **観測点**: raise される例外型／evidence SELECT (kind='review_pass')／operation_log SELECT ／ **期待状態**: review_pass 証跡 0 件のまま
- **期待 DB 差分**: operation_log +1 行（hash 不一致拒否）のみ ／ **期待証跡**: operation_log 拒否行（理由 = commit hash mismatch H1≠H2）
- **禁止副作用**: H2 での review_pass 記録・既存 commit_hash 証跡の書換え ／ **エラー型**: CommitHashMismatch
- **対象更新**: S0.2（制作層）／versioning の束縛検査 ／ **TC**: （割当待ち）

### AC-54-3（境界・復旧）

- **Given**: 同一 task・同一 commit H1 の証跡化要求が再実行（クラッシュ後リトライ相当）で二重到達し、hash 桁数が 40/64/その他の 3 パターンある状態 ／ **When**: commit_hash 証跡化をそれぞれ実行する ／ **Then**: 40 桁・64 桁は受理され再実行でも 1 行に収束し、その他桁数（39 桁）は拒否される
- **fixture**: seed: 同一 (task, H1[40桁]) を 2 回投入／64 桁 hash を 1 回投入／39 桁文字列を 1 回投入
- **観測点**: evidence SELECT（kind='commit_hash' の件数・value）／raise される例外型 ／ **期待状態**: commit_hash 証跡 = 2 行（40 桁 1・64 桁 1）
- **期待 DB 差分**: evidence +2 行（重複分・不正桁は増えない） ／ **期待証跡**: operation_log 行（39 桁の拒否）
- **禁止副作用**: 同一 (task, kind, value) の重複行・不正桁数 hash の記録 ／ **エラー型**: InvalidCommitHash（不正桁のみ。重複再実行は正常収束）
- **対象更新**: S0.2（制作層）／versioning の冪等・桁検査 ／ **TC**: （割当待ち）

## FR-55

### AC-55-1（正常）

- **Given**: WP アップロード済みの元記事資産（asset A1）と、その記事から派生した SNS 用画像の WP アップロード結果 ／ **When**: 派生資産を parent_asset_id=A1 で登録し、系譜クエリで根まで辿る ／ **Then**: 派生 assets 行が参照情報のみで登録され、parent_asset_id を辿って元記事 A1 に到達できる
- **fixture**: seed: assets に A1（記事、canonical_url='`http://wp.test/post/1`'）、登録要求 = {asset_type:'image', wp_media_id:'m-77', content_hash:…, parent_asset_id:A1}
- **観測点**: assets SELECT（新行の列値）／再帰 CTE による系譜クエリ結果 ／ **期待状態**: assets 2 行（A1 と派生行）、系譜クエリ結果 = [派生, A1]
- **期待 DB 差分**: assets +1 行（本文実体列なし・参照のみ） ／ **期待証跡**: なし（登録行自体が系譜の正本。公開時の published_url は別 FR）
- **禁止副作用**: SQLite への画像バイナリ・本文テキストの格納 ／ **エラー型**: なし
- **対象更新**: S0.2（制作層）／content/assets.register_derived ／ **TC**: （割当待ち）

### AC-55-2（拒否）

- **Given**: 本文実体（50KB の記事テキスト）を metadata に含む登録要求と、存在しない parent_asset_id=999 を指す派生登録要求 ／ **When**: それぞれ assets 登録を実行する ／ **Then**: 実体混入は ContentBodyRejected、不在 parent は AssetReferenceInvalid で拒否され、行が作られない
- **fixture**: seed: config.asset_metadata_max_bytes=4096、要求 1 = metadata_json に 50KB 本文、要求 2 = {parent_asset_id:999}
- **観測点**: raise される例外型／assets 件数／operation_log SELECT ／ **期待状態**: assets 差分なし
- **期待 DB 差分**: operation_log +2 行（実体混入拒否・参照不正拒否）のみ ／ **期待証跡**: operation_log 拒否行（理由 = content body in metadata／parent not found）
- **禁止副作用**: 本文実体を含む行の INSERT・出自なし派生行の作成 ／ **エラー型**: ContentBodyRejected／AssetReferenceInvalid
- **対象更新**: S0.2（制作層）／assets 登録の入口検査 ／ **TC**: （割当待ち）

### AC-55-3（境界・復旧）

- **Given**: 登録済み資産と同一 canonical_url での再登録要求（クラッシュ後リトライ相当）と、自己参照系譜（parent = 自 ID）を作る要求 ／ **When**: それぞれ assets 登録を実行する ／ **Then**: 同一 URL の再登録は行を増やさず既存行で冪等完了し、自己参照・循環は拒否される
- **fixture**: seed: assets に A1（canonical_url='`http://wp.test/post/1`'）、要求 1 = 同一 URL 再登録、要求 2 = A1 の parent を A1 自身へ更新する派生登録
- **観測点**: assets 件数・戻り値（既存 ID）／raise される例外型 ／ **期待状態**: assets 1 行のまま（A1）、循環系譜 0 件
- **期待 DB 差分**: assets 差分なし、operation_log +1 行（循環拒否） ／ **期待証跡**: operation_log 拒否行（理由 = circular lineage）
- **禁止副作用**: canonical_url 重複行の作成・循環系譜の成立 ／ **エラー型**: AssetReferenceInvalid（循環のみ。再登録は正常冪等）
- **対象更新**: S0.2（制作層）／assets の冪等・系譜検査 ／ **TC**: （割当待ち）

## FR-61

### AC-61-1（正常）

- **Given**: business_profile 1 件と、露出層の親ノード（node_key='exposure.blog'）が登録済みの状態 ／ **When**: 5 階層それぞれに非有料指標ノード（例: micro_cv 層の 'newsletter_signup'、metric_type='count'）を登録し、layer×medium の横断集計クエリを実行する ／ **Then**: 全ノードが 5 階層のいずれかに接地して登録され、集計クエリが媒体横断の断面を返す
- **fixture**: seed: business_profiles 1 行、kpi_nodes に exposure 親 1 行、measurements にノード紐付き値 2 行（媒体 blog/x）
- **観測点**: kpi_nodes SELECT（layer・node_key・UNIQUE）／横断集計クエリの結果セット ／ **期待状態**: kpi_nodes に 5 階層のノードが存在し、全 measurements がノードへ FK 接続
- **期待 DB 差分**: kpi_nodes +5 行、operation_log 差分なし ／ **期待証跡**: なし（正常登録は証跡不要 — 拒否時のみ operation_log）
- **禁止副作用**: 戦略正本（brand_plans 等）への書込み・有料指標型の混入 ／ **エラー型**: なし
- **対象更新**: S0.3（計測層）／measure/kpi_tree.register_node・cross_query ／ **TC**: （割当待ち）

### AC-61-2（拒否）

- **Given**: 有料指標型（metric_type='roas'）のノード定義と、登録済み node_key と重複する定義と、別 profile の親を指す定義 ／ **When**: それぞれ kpi_nodes 登録を実行する ／ **Then**: 有料指標は PaidMetricRejected（FR-23 連携）、重複キー・越境親は KpiNodeInvalid で拒否され、いずれも行が作られない
- **fixture**: seed: business_profiles 2 行、profile1 に node_key='exposure.blog' 登録済み、要求 = {metric_type:'roas'}／{node_key:'exposure.blog'}／{parent: profile2 のノード}
- **観測点**: raise される例外型／kpi_nodes 件数／operation_log SELECT ／ **期待状態**: kpi_nodes は seed の行のみ
- **期待 DB 差分**: operation_log +3 行（有料拒否・重複拒否・越境拒否）のみ ／ **期待証跡**: operation_log 拒否行（指標型・node_key・理由）
- **禁止副作用**: cac/roas/ad_spend 型ノードの成立（アプリ層を迂回した直接 INSERT も DDL CHECK で拒否されること） ／ **エラー型**: PaidMetricRejected／KpiNodeInvalid
- **対象更新**: S0.3（計測層）／kpi_tree の登録検査＋DDL CHECK ／ **TC**: （割当待ち）

### AC-61-3（境界・復旧）

- **Given**: measurements から参照されているノード N1 と、根ノード（parent なし）だけの最小ツリー ／ **When**: N1 の DELETE を試み、次に N1 を archived 化し、根ノードのみで横断集計を実行する ／ **Then**: DELETE は FK RESTRICT で失敗し、archived 化は成功して参照整合が保たれ、最小ツリーでも集計が空でなく決定的に返る
- **fixture**: seed: kpi_nodes に根 N1、measurements に N1 参照 1 行
- **観測点**: DELETE の失敗（sqlite3.IntegrityError）／kpi_nodes.status／集計クエリ結果 ／ **期待状態**: N1 は status='archived' で存続、measurements の FK は不変
- **期待 DB 差分**: kpi_nodes 1 行 UPDATE（status）のみ、行数不変 ／ **期待証跡**: なし（構造保護は DDL の領分）
- **禁止副作用**: 参照中ノードの物理削除・measurements の孤児化 ／ **エラー型**: IntegrityError（DELETE 試行のみ。archived 化・集計は正常）
- **対象更新**: S0.3（計測層）／kpi_tree の退役・FK 保護 ／ **TC**: （割当待ち）

## FR-62

### AC-62-1（正常）

- **Given**: GA4 fixture エクスポート（PV 10 行、source hash S1）と、投入先 kpi_node・T-MEAS task が登録済みの状態 ／ **When**: 同一エクスポートで取り込みを 2 回実行する ／ **Then**: 1 回目は取得証跡が投入前に記録されて 10 行が投入され、2 回目は冪等で measurements 差分ゼロになる
- **fixture**: seed: kpi_nodes 1 行（exposure/pv）、tasks に T-MEAS 1 行、fixture ファイル ga4_export.csv（10 行、SHA-256=S1）
- **観測点**: measurements 件数（1 回目 +10・2 回目 ±0）／evidence SELECT（kind='measurement'）の created_at と measurements.imported_at の順序 ／ **期待状態**: measurements 10 行（全行 evidence_id が S1 証跡へ FK 接続）
- **期待 DB 差分**: 1 回目: evidence +1 行・measurements +10 行。2 回目: 差分なし ／ **期待証跡**: evidence（kind=measurement、value=S1、payload に source・file_hash・period・row_count=10）
- **禁止副作用**: 2 回目実行での行重複・証跡なし行の投入・有料指標ノードへの投入 ／ **エラー型**: なし
- **対象更新**: S0.3（計測層）／measure/importer.import_export ／ **TC**: （割当待ち）

### AC-62-2（拒否）

- **Given**: 10 行中 3 行が破損（列欠落・期間逆転・未登録ノード宛）した GA4 エクスポートと、全行破損の別ファイル ／ **When**: それぞれ取り込みを実行する ／ **Then**: 部分破損は正常 7 行のみ投入・3 行が隔離され、全行破損は ImportSourceInvalid で全体拒否される（AC-62 検証）
- **fixture**: seed: fixture broken_partial.csv（破損 3/10）・broken_all.csv（全行破損）、config.import_quarantine_dir=scratch 隔離先
- **観測点**: measurements 件数／隔離ファイルの行数・件数記録／raise される例外型 ／ **期待状態**: 部分破損: measurements 7 行＋隔離 3 行。全破損: measurements 差分なし
- **期待 DB 差分**: 部分: evidence +1・measurements +7・operation_log +1（隔離記録）。全破損: operation_log +1 のみ ／ **期待証跡**: operation_log 行（隔離件数・理由）／取得証跡（部分破損側は投入前に記録済み）
- **禁止副作用**: 破損行の measurements 混入・全破損ファイルからの部分コミット ／ **エラー型**: ImportSourceInvalid（全破損のみ。部分破損は正常終了＋隔離）
- **対象更新**: S0.3（計測層）／importer のエラー隔離・fail-close ／ **TC**: （割当待ち）

### AC-62-3（境界・復旧）

- **Given**: 投入 transaction の途中（5 行 INSERT 後）で強制終了させるフォールト注入と、データ 0 行の空エクスポート ／ **When**: クラッシュ後に同一エクスポートを再実行し、続けて空エクスポートを取り込む ／ **Then**: クラッシュ分は全行 rollback されて部分コミットが残らず、再実行で 10 行が一括投入され、空エクスポートは証跡のみ残して正常終了する
- **fixture**: seed: AC-62-1 と同じ fixture＋5 行目 INSERT 後に例外を注入するフック／empty.csv（ヘッダのみ、hash S2）
- **観測点**: クラッシュ直後の measurements 件数（0 件）／再実行後の件数（10 件）／空取込後の evidence ／ **期待状態**: measurements 10 行（再実行分のみ）、空取込は行 0・証跡 1
- **期待 DB 差分**: 再実行: measurements +10。空取込: evidence +1（value=S2、row_count=0）のみ ／ **期待証跡**: evidence（kind=measurement、value=S2、payload.row_count=0）
- **禁止副作用**: 5 行だけの部分コミット残留・再実行での 15 行化 ／ **エラー型**: なし（注入クラッシュは transaction rollback で吸収）
- **対象更新**: S0.3（計測層）／importer の transaction・空境界 ／ **TC**: （割当待ち）

## FR-63

### AC-63-1（正常）

- **Given**: kpi_nodes・measurements に集計対象データが投入済みの SQLite 状態 ／ **When**: 同一 DB 状態で HTML ダッシュボード生成を 2 回実行する ／ **Then**: 2 回とも同一 SHA-256 の自己完結 HTML（外部参照 0 件）が生成され、dashboard 証跡が 1 件に収束する
- **fixture**: seed: kpi_nodes 3 行（exposure/micro_cv/conversion）・measurements 6 行、Clock 注入で生成時刻を固定
- **観測点**: 出力 HTML の SHA-256（2 回比較）／HTML 内の src/href 走査（外部 URL 0 件）／evidence SELECT（kind='dashboard'） ／ **期待状態**: 自己完結 HTML 1 ファイル（CSS/JS インライン）
- **期待 DB 差分**: evidence +1 行（dashboard）— 2 回目は差分なし。業務テーブル不変 ／ **期待証跡**: evidence（kind=dashboard、value=出力 hash、payload に file_path・file_hash・period_end）
- **禁止副作用**: 外部 CDN・外部 URL 参照の混入・業務テーブルへの書込み ／ **エラー型**: なし
- **対象更新**: S1（計測層）／measure/dashboard.generate_html ／ **TC**: （割当待ち）

### AC-63-2（拒否）

- **Given**: テンプレートに外部 CDN 参照（script src='`https://cdn.example.com/x.js`'）が混入した構成と、credential 様文字列が config 経由で集計に紛れ込む構成 ／ **When**: HTML ダッシュボード生成を実行する ／ **Then**: 自己検査が外部参照・secret 混入を検出して ExternalReferenceDetected で成果物を破棄し、証跡化されない
- **fixture**: seed: 汚染テンプレート fixture／集計対象に 'password=…' 様文字列を含む seed 行
- **観測点**: raise される例外型／出力ディレクトリ（成果物なし）／evidence 件数／operation_log SELECT ／ **期待状態**: 出力ファイル 0 件、dashboard 証跡 0 件
- **期待 DB 差分**: operation_log +1 行（検出・破棄）のみ ／ **期待証跡**: operation_log 拒否行（理由 = external reference detected／secret pattern）
- **禁止副作用**: 汚染 HTML の出力先残留・汚染成果物の証跡化 ／ **エラー型**: ExternalReferenceDetected
- **対象更新**: S1（計測層）／dashboard の自己検査・fail-close ／ **TC**: （割当待ち）

### AC-63-3（境界・復旧）

- **Given**: measurements が 0 件の空 DB 状態と、HTML 書出し途中（temp 書込み中）でプロセスが強制終了した状態 ／ **When**: 空状態で生成を実行し、クラッシュ後に再度生成を実行する ／ **Then**: 空状態でも「データなし」表示の自己完結 HTML が決定的に生成され、クラッシュの temp 断片は出力先に現れず再実行のみで復旧する
- **fixture**: seed: measurements 空・Clock 固定／temp 書込み中に例外を注入するフック、出力先には rename 前の断片なしを検証
- **観測点**: 空生成の出力 hash（再実行と一致）／出力ディレクトリの断片有無／evidence 件数 ／ **期待状態**: 自己完結 HTML 1 ファイル（空データ表示）、断片 0 件
- **期待 DB 差分**: evidence +1 行（dashboard）— クラッシュ試行分の証跡は 0 ／ **期待証跡**: evidence（kind=dashboard — 成功分のみ）
- **禁止副作用**: temp 断片の出力先残留・生成失敗分の証跡化 ／ **エラー型**: なし（クラッシュは temp→rename 方式で吸収）
- **対象更新**: S1（計測層）／dashboard の空境界・アトミック書出し ／ **TC**: （割当待ち）

## FR-71

### AC-71-1（正常）

- **Given**: 空の SQLite ファイルと全 migration ファイル（DDL 正本 s0-contract §2 準拠） ／ **When**: スキーマ生成と DU-11 verify() を実行する ／ **Then**: 業務 23＋インフラ 2 の 25 テーブル・append-only トリガ・FK が生成され、verify() が pass を返し使用開始が許可される
- **fixture**: seed: 空 DB（0 バイト新規ファイル）、migrations/ 配下の全 NNNN_*.sql
- **観測点**: sqlite_master SELECT（テーブル・トリガ数）／verify() 戻り値／PRAGMA foreign_key_check・integrity_check ／ **期待状態**: 25 テーブル＋保護トリガ 6 件（config/evidence/state_transitions × update/delete）存在、verify() = pass
- **期待 DB 差分**: 全 25 テーブル CREATE、schema_version +N 行（migration ごと） ／ **期待証跡**: schema_version 行（version・migration 名・checksum・適用者・時刻）
- **禁止副作用**: DDL 正本にないテーブル・トリガの生成、FK OFF での使用開始 ／ **エラー型**: なし
- **対象更新**: S0.1（DB 基盤）／db.migrate・db.verify ／ **TC**: （割当待ち）

### AC-71-2（拒否）

- **Given**: テーブルが 1 件欠落（例: spend_ledger なし）した不完全スキーマの DB ／ **When**: DU-11 verify() と使用開始判定を実行する ／ **Then**: verify() が 25 テーブル存在検査で fail し、SchemaVerificationFailed で使用開始が拒否される（不完全スキーマ上の業務書込みは始まらない）
- **fixture**: seed: 全 migration 適用後に DROP TABLE spend_ledger を直接実行した DB
- **観測点**: verify() 戻り値／raise される例外型／業務書込み API の拒否 ／ **期待状態**: 使用開始拒否（kernel 起動せず）
- **期待 DB 差分**: 差分なし（拒否後の業務書込み 0 件） ／ **期待証跡**: verify() の検証結果ログ（欠落テーブル名 = spend_ledger）
- **禁止副作用**: 不完全スキーマへの業務行 INSERT・欠落の黙認（fail-open） ／ **エラー型**: SchemaVerificationFailed
- **対象更新**: S0.1（DB 基盤）／db.verify の fail-close ／ **TC**: （割当待ち）

### AC-71-3（境界・復旧）

- **Given**: 全 migration 適用済みの DB への再適用要求と、append-only テーブル（evidence）への UPDATE 試行 ／ **When**: migration を再実行し、evidence 行の UPDATE を試みる ／ **Then**: 再適用は schema_version 照合で no-op（二重適用なし）、UPDATE は保護トリガの ABORT で拒否され、DB は不変
- **fixture**: seed: 全 migration 適用済み DB＋evidence 1 行、UPDATE 文 = SET value='tampered'
- **観測点**: schema_version SELECT（行数不変）／UPDATE の例外／evidence SELECT（値の不変性） ／ **期待状態**: schema_version 行数不変・evidence 値不変
- **期待 DB 差分**: 差分なし ／ **期待証跡**: なし（no-op と拒否のみ）
- **禁止副作用**: migration の二重適用・append-only 行の改変 ／ **エラー型**: AppendOnlyViolation（UPDATE 側のみ）
- **対象更新**: S0.1（DB 基盤）／冪等適用＋保護トリガ ／ **TC**: （割当待ち）

## FR-72

### AC-72-1（正常）

- **Given**: 旧版（version=1）の DB と、新テーブル追加の expand migration（0002_add_table.sql） ／ **When**: backup 作成→昇格適用→verify()→schema_version 記録を実行する ／ **Then**: 昇格が成功し、schema_version に version=2・checksum・適用者が記録され、旧形式 reader（既存テーブルの読取）が壊れていない
- **fixture**: seed: version=1 の DB（業務データ数行入り）、0002 = CREATE TABLE（NULL 許容列のみ）
- **観測点**: schema_version SELECT／PRAGMA foreign_key_check・integrity_check／既存データの行数・hash 比較 ／ **期待状態**: version=2、既存行の行数・hash 一致（破壊なし）
- **期待 DB 差分**: schema_version +1 行、新テーブル CREATE（既存行の変更なし） ／ **期待証跡**: schema_version 行（version=2・migration 名・checksum_sha256・applied_by・applied_at）
- **禁止副作用**: 既存の列・値・意味の変更（破壊的変更）・rename ／ **エラー型**: なし
- **対象更新**: S0.1（DB 基盤）／db.migrate の expand 昇格 ／ **TC**: （割当待ち）

### AC-72-2（拒否）

- **Given**: 適用済み migration ファイルを事後編集して checksum が schema_version の記録と食い違う状態 ／ **When**: 昇格の前提検証（checksum 照合）を実行する ／ **Then**: MigrationChecksumMismatch で適用前に停止し、DB は一切変更されない（改竄・不変性違反を通さない）
- **fixture**: seed: version=1 適用済み DB、0001_init.sql の内容を 1 文字改変（checksum 不一致を再現）
- **観測点**: raise される例外型／schema_version SELECT（行数不変）／DB ファイルの hash 比較 ／ **期待状態**: 昇格停止・DB 不変
- **期待 DB 差分**: 差分なし ／ **期待証跡**: 構造化ログ（checksum 不一致 — 期待値と実測値）
- **禁止副作用**: checksum 不一致のままの適用続行・schema_version の書換え ／ **エラー型**: MigrationChecksumMismatch
- **対象更新**: S0.1（DB 基盤）／checksum 照合ゲート ／ **TC**: （割当待ち）

### AC-72-3（境界・復旧）

- **Given**: 適用後の verify() が fail する migration（FK 無効化を含む）と、適用前 backup ／ **When**: 昇格適用→verify() 失敗→backup 復元の復旧経路を実行する ／ **Then**: MigrationVerifyFailed が raise され、backup から復元されて昇格前の状態・version に戻る（壊れた版で運転を続けない）
- **fixture**: seed: version=1 の DB＋適用前 backup、0002 = FK 整合を壊す不正 DDL（verify() fail を再現）
- **観測点**: raise される例外型／復元後の schema_version SELECT（version=1）／PRAGMA integrity_check ／ **期待状態**: version=1 に復元済み・integrity_check ok
- **期待 DB 差分**: 最終的に差分なし（適用→復元で相殺） ／ **期待証跡**: verify() の失敗結果ログ＋復元実施の記録
- **禁止副作用**: verify() fail のままの運転継続・失敗した同一 version の書換え修正 ／ **エラー型**: MigrationVerifyFailed
- **対象更新**: S0.1（DB 基盤）／backup 復元経路 ／ **TC**: （割当待ち）

## FR-73

### AC-73-1（正常）

- **Given**: 承認済みの有償 API 利用（Seedance 動画生成 300 円）が external_operations で confirmed になった状態 ／ **When**: 支出記録と当月累計の照会を実行する ／ **Then**: spend_ledger に 1 行（service・金額・用途・task_id・approval_id）が INSERT され、当月累計にその 300 円が反映される
- **fixture**: seed: tasks 1 行、approvals 1 行（approved）、external_operations 1 行（confirmed, external_operation_id='seed-001'）、記録要求 = {service:'seedance', amount_minor:300, currency:'JPY', purpose:'動画生成', occurred_at:今日}
- **観測点**: spend_ledger SELECT／月間累計クエリの戻り値 ／ **期待状態**: 台帳 1 行・当月累計 300 円
- **期待 DB 差分**: spend_ledger +1 行 ／ **期待証跡**: spend_ledger 行（external_operation_id で operation_log 証跡と紐付く）
- **禁止副作用**: 既存台帳行の変更・二重計上 ／ **エラー型**: なし
- **対象更新**: S1（支出台帳）／spend.record・spend.monthly_total ／ **TC**: （割当待ち）

### AC-73-2（拒否）

- **Given**: purpose を欠く記録要求と、記録済みと同一 (service, external_operation_id) の再記録要求 ／ **When**: 2 件の INSERT を実行する ／ **Then**: purpose 欠落は SpendRecordIncomplete、再記録は DuplicateSpendEntry（UNIQUE 制約）で拒否され、台帳は 1 行のまま
- **fixture**: seed: spend_ledger 1 行（service='seedance', external_operation_id='seed-001'）、要求 1 = {purpose:null}、要求 2 = seed と同一 (service, external_operation_id)
- **観測点**: raise される例外型／spend_ledger SELECT（行数） ／ **期待状態**: spend_ledger 1 行のまま（不完全行・重複行なし）
- **期待 DB 差分**: 差分なし ／ **期待証跡**: 構造化ログの拒否行（欠落フィールド名・重複キー）
- **禁止副作用**: 用途不明の支出行の混入・同一操作の二重計上 ／ **エラー型**: SpendRecordIncomplete／DuplicateSpendEntry
- **対象更新**: S1（支出台帳）／NOT NULL・UNIQUE 制約＋事前検証 ／ **TC**: （割当待ち）

### AC-73-3（境界・復旧）

- **Given**: amount_minor=0 の無償枠内利用と、external_operations が sent のままクラッシュした有償操作 ／ **When**: 0 円利用の記録と、再起動後の §3.3 照合→記録再開を実行する ／ **Then**: 0 円利用も 1 行として記録され（全件記録 — 閾値なし）、クラッシュ分は照合で confirmed 化後に記録され、同一 external_operation_id の再記録は UNIQUE で 1 行に吸収される
- **fixture**: seed: 記録要求 = {amount_minor:0}、external_operations 1 行（status='sent', external_operation_id='seed-002'）＋リモート照合 mock = 成功
- **観測点**: spend_ledger SELECT（0 円行の存在・seed-002 の行数 = 1）／external_operations SELECT（confirmed 化） ／ **期待状態**: 台帳 +2 行（0 円行・復旧行が各 1 行）
- **期待 DB 差分**: spend_ledger +2 行、external_operations 1 行 UPDATE（sent→confirmed） ／ **期待証跡**: spend_ledger 行＋照合復旧の operation_log 証跡
- **禁止副作用**: 0 円利用の記録省略・復旧再送での二重計上 ／ **エラー型**: なし
- **対象更新**: S1（支出台帳）／0 円境界＋クラッシュ復旧の冪等記録 ／ **TC**: （割当待ち）

## SR-01

### AC-SR-01-1（正常）

- **Given**: upper run と lower run が各 1 件実行され、upper は意味モデル、lower は TLP を提出する ／ **When**: 両 run の成果物提出を型 × loop_kind 対応表で検証しながら完了させる ／ **Then**: upper の成果物は意味モデル群のみ、lower の成果物は TLP のみとして受理され、両ループの学習正本が交差しない
- **fixture**: seed: upper run（brand plan 有）＋ lower run（有効 brief 保持）、提出 payload = 各正規型
- **観測点**: 提出 API 戻り値／tactical_learning_packets SELECT（loop_run の loop_kind 別件数） ／ **期待状態**: upper に TLP 0 件、lower に TLP 1 件、意味モデルは upper 由来のみ
- **期待 DB 差分**: tactical_learning_packets +1 行（lower 分のみ） ／ **期待証跡**: TLP 行（lower run 起点）
- **禁止副作用**: upper run への TLP 追加・lower からの意味モデル追加 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス — SCM-06/07/08） ／ **TC**: （割当待ち）

### AC-SR-01-2（拒否）

- **Given**: lower run が strategy_revision（上流の学習成果物）を提出しようとし、upper run が TLP を提出しようとする ／ **When**: 両提出を実行する ／ **Then**: 両方とも LoopScopeViolation（TLP 側は DDL 整合トリガの IntegrityError）で拒否され、DB は変化しない
- **fixture**: seed: AC-SR-01-1 と同じ run 構成、提出 payload = 越境型
- **観測点**: raise される例外型／operation_log SELECT／対象テーブル行数 ／ **期待状態**: 両 run の状態・学習正本とも提出前のまま
- **期待 DB 差分**: operation_log +2 行（越境拒否 ×2）のみ ／ **期待証跡**: operation_log 拒否行（loop_kind・提出型・理由）
- **禁止副作用**: 越境成果物の永続化・単一ループへの統合的書込み ／ **エラー型**: LoopScopeViolation／IntegrityError
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

## SR-02

### AC-SR-02-1（正常）

- **Given**: 観測事実（fact）のみで構成された market_observation payload ／ **When**: リサーチ工程の観測投入を実行する ／ **Then**: schema 適合として受理され、fact フィールドに解釈が混在していないことが検証済みになる
- **fixture**: fixture: json/strategy/fixtures/ の valid market_observation（fact のみ）
- **観測点**: 投入 API 戻り値／受理レコードの schema 検証結果 ／ **期待状態**: observation 1 件受理（fact のみ）
- **期待 DB 差分**: observation レコード +1（S1 ストア） ／ **期待証跡**: schema 検証 PASS の記録
- **禁止副作用**: 解釈フィールドの自動付加・operation_log への拒否行 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス — SCM-05） ／ **TC**: （割当待ち）

### AC-SR-02-2（拒否）

- **Given**: fact フィールドに AI 解釈文が混在した（又は解釈用フィールドを付加した）market_observation payload ／ **When**: 観測投入を実行する ／ **Then**: ObservationInterpretationRejected（G-OBS-INTERPRETATION）で拒否され、operation_log に違反フィールドが記録される
- **fixture**: fixture: json/strategy/fixtures/ の invalid market_observation（解釈混在）
- **観測点**: raise される例外型／operation_log SELECT ／ **期待状態**: observation 未受理
- **期待 DB 差分**: operation_log +1 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（違反フィールド・理由）
- **禁止副作用**: 混在 payload の部分受理・fact の自動書換え ／ **エラー型**: ObservationInterpretationMixRejected
- **対象更新**: S1（上流戦略スライス — G-OBS-INTERPRETATION） ／ **TC**: （割当待ち）

### AC-SR-02-3（境界・復旧）

- **Given**: market_observation schema がロード不能（fixture/schema 破損）の状態と、同一テキストを TLP.causal_interpretation として提出するケース ／ **When**: 観測投入と TLP 提出をそれぞれ実行する ／ **Then**: schema 判定不能の観測投入は拒否側へ倒れ（fail-close）、同一テキストでも TLP の解釈フィールド経由なら受理される（分離の単位はフィールド・レコード）
- **fixture**: seed: schema ファイルを破損させた環境＋正規 TLP payload（causal_interpretation に同一文）
- **観測点**: raise される例外型／tactical_learning_packets SELECT ／ **期待状態**: 観測 0 件受理、TLP は正規経路で受理
- **期待 DB 差分**: operation_log +1 行（判定不能拒否）、tactical_learning_packets +1 行 ／ **期待証跡**: operation_log 拒否行（理由 = schema 判定不能）
- **禁止副作用**: 判定不能時の受理（fail-open） ／ **エラー型**: ObservationInterpretationMixRejected（判定不能時）
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

## SR-03

### AC-SR-03-1（正常）

- **Given**: 受理済み market_observation 群と、schema 必須フィールドを完備した market_model／segment_context／problem_model payload ／ **When**: 市場分析の成果物投入を実行する ／ **Then**: 3 モデルとも schema 適合として版付きで受理され、観測への trace を保持する
- **fixture**: fixture: json/strategy/fixtures/ の valid 3 モデル＋観測 ID 参照
- **観測点**: 投入 API 戻り値／受理レコードの schema 検証結果と trace ／ **期待状態**: 3 モデル各 1 版受理
- **期待 DB 差分**: モデルレコード +3（S1 ストア） ／ **期待証跡**: schema 検証 PASS と観測 trace の記録
- **禁止副作用**: 自由 JSON としての受理・trace なし受理 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス — SCM-06） ／ **TC**: （割当待ち）

### AC-SR-03-2（拒否）

- **Given**: schema 必須フィールドを欠いた market_model と、3 モデル以外の自由 JSON 成果物 ／ **When**: 市場分析の成果物投入を実行する ／ **Then**: 両方とも ModelSchemaRejected で拒否され、欠落フィールド一覧が operation_log に残る
- **fixture**: fixture: json/strategy/fixtures/ の invalid market_model（必須欠落）＋自由 JSON
- **観測点**: raise される例外型／operation_log SELECT ／ **期待状態**: モデル 0 件受理
- **期待 DB 差分**: operation_log +2 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（欠落フィールド一覧）
- **禁止副作用**: 部分受理・自由 JSON の正本混入 ／ **エラー型**: ModelSchemaRejected
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

### AC-SR-03-3（境界・復旧）

- **Given**: schema 外の未知フィールドを付加した segment_context と、観測 0 件を根拠とする problem_model ／ **When**: 成果物投入を実行する ／ **Then**: additionalProperties 違反と根拠欠落の両方が拒否され（黙認しない）、観測補充後の再投入は新版として受理される
- **fixture**: fixture: 未知フィールド付き segment_context＋観測参照空の problem_model、その後 valid 版
- **観測点**: raise される例外型／再投入後のモデルレコード SELECT ／ **期待状態**: 初回 0 件受理→再投入で 1 版受理
- **期待 DB 差分**: operation_log +2 行（拒否）、その後モデルレコード +1 ／ **期待証跡**: operation_log 拒否行（additionalProperties／根拠欠落）
- **禁止副作用**: 未知フィールドの黙認（fail-open） ／ **エラー型**: ModelSchemaRejected
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

## SR-04

### AC-SR-04-1（正常）

- **Given**: 状況・制約・代替行動・意思決定条件が実質記入された segment_context payload ／ **When**: セグメント投入を実行する ／ **Then**: 状況ベース segment として受理される
- **fixture**: fixture: json/strategy/fixtures/ の valid segment_context（状況ベース）
- **観測点**: 投入 API 戻り値／受理レコード ／ **期待状態**: segment 1 件受理
- **期待 DB 差分**: segment レコード +1（S1 ストア） ／ **期待証跡**: schema 検証 PASS の記録
- **禁止副作用**: operation_log への拒否行 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス — G-SEGMENT-CONTEXT） ／ **TC**: （割当待ち）

### AC-SR-04-2（拒否）

- **Given**: 年齢・性別・職業・趣味の人口統計属性だけで構成された segment_context payload（状況フィールドなし） ／ **When**: セグメント投入を実行する ／ **Then**: PersonaSegmentRejected（G-SEGMENT-CONTEXT）で拒否され、欠落した状況フィールド一覧が operation_log に残る
- **fixture**: fixture: json/strategy/fixtures/ の invalid segment_context（人口統計のみ）
- **観測点**: raise される例外型／operation_log SELECT ／ **期待状態**: segment 0 件受理
- **期待 DB 差分**: operation_log +1 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（欠落状況フィールド一覧）
- **禁止副作用**: ペルソナ型 segment の正本混入 ／ **エラー型**: PersonaSegmentRejected
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

### AC-SR-04-3（境界・復旧）

- **Given**: 状況フィールドが空文字・空配列のみで人口統計が併記された segment と、状況＋人口統計（補助）が両方実質記入された segment ／ **When**: 両者のセグメント投入を実行する ／ **Then**: 空文字・空配列は「実質未記入」として拒否され、混在（人口統計が補助）は受理される
- **fixture**: fixture: 状況空の segment＋状況実記入・人口統計併記の segment
- **観測点**: raise される例外型／受理レコード SELECT ／ **期待状態**: 前者 0 件・後者 1 件受理
- **期待 DB 差分**: operation_log +1 行（拒否）、segment レコード +1 ／ **期待証跡**: operation_log 拒否行（理由 = 状況フィールド実質未記入）
- **禁止副作用**: 空フィールドの記入扱い（fail-open） ／ **エラー型**: PersonaSegmentRejected（空フィールド時）
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

## SR-05

### AC-SR-05-1（正常）

- **Given**: rejected_options 2 件（各棄却理由つき）を持つ strategic_choice と disconfirming_conditions を持つ value_hypothesis ／ **When**: マーケティング戦略の成果物投入を実行する ／ **Then**: 両モデルとも受理され、棄却案・棄却理由・反証条件が保持される
- **fixture**: fixture: json/strategy/fixtures/ の valid strategic_choice＋value_hypothesis
- **観測点**: 投入 API 戻り値／受理レコードの rejected_options・disconfirming_conditions ／ **期待状態**: 2 モデル各 1 版受理
- **期待 DB 差分**: 戦略モデルレコード +2（S1 ストア） ／ **期待証跡**: schema 検証 PASS の記録
- **禁止副作用**: 棄却案・反証条件の欠落したままの受理 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス — SCM-07） ／ **TC**: （割当待ち）

### AC-SR-05-2（拒否）

- **Given**: rejected_options が空の strategic_choice と disconfirming_conditions 欠落の value_hypothesis ／ **When**: 成果物投入を実行する ／ **Then**: 両方とも IncompleteStrategyRejected で拒否され、欠落要素が operation_log に残る
- **fixture**: fixture: json/strategy/fixtures/ の invalid strategic_choice（棄却案空）＋invalid value_hypothesis（反証なし）
- **観測点**: raise される例外型／operation_log SELECT ／ **期待状態**: 0 件受理
- **期待 DB 差分**: operation_log +2 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（欠落要素一覧）
- **禁止副作用**: 反証不能な仮説の正本混入 ／ **エラー型**: IncompleteStrategyRejected
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

### AC-SR-05-3（境界・復旧）

- **Given**: rejected_options ちょうど 1 件（minItems 境界）の strategic_choice と、棄却理由が空文字の strategic_choice ／ **When**: 両者の成果物投入を実行する ／ **Then**: 1 件（理由実記入）は受理され、空文字理由は欠落と同等に拒否される
- **fixture**: fixture: rejected_options 1 件 valid＋理由空文字 invalid
- **観測点**: raise される例外型／受理レコード SELECT ／ **期待状態**: 前者 1 版受理・後者 0 件
- **期待 DB 差分**: 戦略モデルレコード +1、operation_log +1 行（拒否） ／ **期待証跡**: operation_log 拒否行（理由 = 棄却理由空）
- **禁止副作用**: 空文字理由の記入扱い ／ **エラー型**: IncompleteStrategyRejected（空文字時）
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

## SR-06

### AC-SR-01（正常）

- **Given**: 同一内容でキー順・空白・NFC 表現だけが異なる strategic_brief JSON 2 通 ／ **When**: digest（正準化 JSON SHA-256）を両方に対して算出する ／ **Then**: 両者の digest が一致し、digest/status/created_at の変更では digest が変化しない
- **fixture**: fixtures/strategic-brief.valid.json とキー順を入替えた同内容 JSON
- **観測点**: digest 算出関数の戻り値比較 ／ **期待状態**: digest 一致（決定性）
- **期待 DB 差分**: 差分なし（算出は pure） ／ **期待証跡**: なし（拒否・算出は証跡対象外）
- **禁止副作用**: DB への書込み・brief 行の変更 ／ **エラー型**: なし
- **対象更新**: S0.1（戦略ストア）／canonical_digest ／ **TC**: STC-I-01

### AC-SR-06-1（拒否）

- **Given**: trace ID（strategic_choice_id）欠落の brief draft と、計測計画が KPI 目標値の割当だけの brief draft ／ **When**: issue_strategic_brief（S0 シードコマンド）を実行する ／ **Then**: 両方とも BriefSchemaRejected で INSERT されず、operation_log に理由（trace 欠落／計測計画の実質欠如）が残る
- **fixture**: seed: strategic_choice_id 空の draft＋measurement_plan_json = KPI 目標値のみの draft
- **観測点**: raise される例外型／strategic_briefs SELECT／operation_log SELECT ／ **期待状態**: strategic_briefs 空のまま
- **期待 DB 差分**: operation_log +2 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（欠落・無効理由）
- **禁止副作用**: 無効 brief の INSERT・digest の発番 ／ **エラー型**: BriefSchemaRejected
- **対象更新**: S0.1（DU-02 — issue_strategic_brief） ／ **TC**: （割当待ち）

### AC-SR-06-2（境界・復旧）

- **Given**: active な brief v1 を保持して実行中の lower run が存在する状態 ／ **When**: supersede_strategic_brief で v2（supersedes_id = v1）を発行し、その後に新規 lower run の start と既存 run の完走を行う ／ **Then**: v1 は superseded へ遷移し内容列は不変、既存 run は v1 digest のまま完走でき、新規 run は v2 のみ参照して開始する
- **fixture**: seed: brief v1（active）＋v1 参照の running lower run、v2 draft
- **観測点**: strategic_briefs SELECT（status・supersedes_id）／loop_runs の digest 列／新規 start の参照先 ／ **期待状態**: v1 = superseded・v2 = active、既存 run = completed（v1 digest 保持）、新規 run = v2 参照
- **期待 DB 差分**: strategic_briefs +1 行（v2）、v1 の status UPDATE のみ ／ **期待証跡**: v2 行（supersedes_id = v1）・既存 run の TLP（v1 digest 三者一致）
- **禁止副作用**: v1 内容列の変更・既存 run の digest 差替え・新規 run の v1 参照 ／ **エラー型**: なし
- **対象更新**: S0.1（DU-02 — supersede 連鎖） ／ **TC**: （割当待ち）

## SR-07

### AC-SR-02（拒否）

- **Given**: brief が存在しない／status=draft／superseded／有効期間外の 4 状態 ／ **When**: lower loop_run の開始を要求する ／ **Then**: 4 状態すべてで開始が拒否され（DDL CHECK＋validate_strategic_brief）、loop_runs に行が増えない
- **fixture**: fixtures/strategic-brief.*.invalid 系 seed 4 種
- **観測点**: raise される GateRejected／loop_runs SELECT COUNT ／ **期待状態**: run 未作成
- **期待 DB 差分**: 差分なし ／ **期待証跡**: 拒否の構造化ログ
- **禁止副作用**: loop_runs への INSERT ／ **エラー型**: GateRejected
- **対象更新**: S0.1（開始ガード） ／ **TC**: STC-I-02

### AC-SR-07-1（正常）

- **Given**: status = active・有効期間内・digest 一致の strategic_brief と pending の lower loop_run ／ **When**: start イベントを発火する ／ **Then**: running へ遷移し、run が brief の id と digest（64 桁）を固定保持し、state_transitions に passed 行が残る
- **fixture**: seed: valid_from ≤ now ≤ valid_until の active brief＋brief 参照の pending lower run（親 upper running）
- **観測点**: loop_runs SELECT（state・strategic_brief_id・strategic_brief_digest）／state_transitions SELECT ／ **期待状態**: run = running（brief id・digest 保持）
- **期待 DB 差分**: loop_runs UPDATE 1 行、state_transitions +1 行（passed） ／ **期待証跡**: state_transitions 行（guard_result = passed）
- **禁止副作用**: digest の書換え・brief 行の変更 ／ **エラー型**: なし
- **対象更新**: S0.1（DU-01 — start ガード） ／ **TC**: （割当待ち）

### AC-SR-07-2（境界・復旧）

- **Given**: valid_until = now ちょうどの brief、valid_until NULL の brief、開始後に superseded 化された brief を保持する running run の 3 ケース ／ **When**: 前 2 者で start を、後者で run の完走を実行する ／ **Then**: valid_until = now は有効（≤ 判定）で開始成立、NULL は無期限として成立、superseded 化後も実行中 run は旧 digest のまま完走できる
- **fixture**: seed: valid_until = now の brief／valid_until NULL の brief／start 後に supersede した brief＋running run
- **観測点**: loop_runs SELECT（state・digest）／state_transitions SELECT ／ **期待状態**: 2 run 開始成立・1 run 完走（旧 digest 保持）
- **期待 DB 差分**: loop_runs UPDATE ×3、state_transitions +3 行（passed） ／ **期待証跡**: state_transitions の passed 行と完走 run の TLP（旧 digest 三者一致）
- **禁止副作用**: 境界時刻の拒否側誤判定・実行中 run の digest 差替え・強制中断 ／ **エラー型**: なし
- **対象更新**: S0.1（DU-01/02 — 有効期間境界） ／ **TC**: （割当待ち）

## SR-08

### AC-SR-03（正常）

- **Given**: 有効 brief に紐づく lower run が終端遷移（completed／failed）する状況 ／ **When**: 終端遷移を実行する ／ **Then**: 同一 transaction で TLP が 1 件生成され、completed=learning／それ以外=failure の packet_kind になる
- **fixture**: conftest の seed_brief＋seed_lower_run
- **観測点**: tactical_learning_packets SELECT（loop_run_id・packet_kind） ／ **期待状態**: run 終端＋TLP 1 件
- **期待 DB 差分**: loop_runs UPDATE 1 行＋tactical_learning_packets INSERT 1 行（同一 tx） ／ **期待証跡**: state_transitions 行＋TLP 行
- **禁止副作用**: packet なし終端・二重 packet ／ **エラー型**: なし
- **対象更新**: S0.1（TLP 生成） ／ **TC**: STC-I-05

### AC-SR-06（拒否）

- **Given**: brief_id・digest の不一致、upper run、非終端 run、既存 packet ありの各不正 TLP ／ **When**: tactical_learning_packets へ INSERT する ／ **Then**: DDL 整合トリガ・UNIQUE 制約がすべて拒否する（run／brief／digest の三者一致・lower＋終端・1 run 1 packet）
- **fixture**: conftest insert_tlp の不正系 seed 4 種
- **観測点**: IntegrityError の発生とメッセージ ／ **期待状態**: TLP 未挿入
- **期待 DB 差分**: 差分なし ／ **期待証跡**: なし（拒否・算出は証跡対象外）
- **禁止副作用**: 不正 packet の INSERT 成功 ／ **エラー型**: IntegrityError
- **対象更新**: S0.1（TLP 整合トリガ） ／ **TC**: STC-I-06

### AC-SR-08-1（拒否）

- **Given**: failed で終端する lower run と、causal_interpretation を含む failure packet payload ／ **When**: 終端遷移＋TLP INSERT を実行する ／ **Then**: failure への causal_interpretation 混入は DDL CHECK が IntegrityError で拒否し、transaction 全体が rollback して終端遷移も成立しない
- **fixture**: seed: running lower run＋failure payload（failure_fact あり・causal_interpretation あり）
- **観測点**: raise される例外型／loop_runs.state／tactical_learning_packets 件数 ／ **期待状態**: run = running のまま（遷移未成立）、TLP 0 件
- **期待 DB 差分**: 差分なし（全 rollback） ／ **期待証跡**: なし（transaction 不成立のため証跡も残らない）
- **禁止副作用**: 因果解釈つき failure packet の永続化・遷移だけの先行成立 ／ **エラー型**: IntegrityError
- **対象更新**: S0.1（DU-10 — packet_kind CHECK） ／ **TC**: （割当待ち）

### AC-SR-08-2（境界・復旧）

- **Given**: 終端遷移＋TLP INSERT の transaction 中にプロセスを強制終了させた lower run ／ **When**: プロセスを再起動し、終端処理を再実行する ／ **Then**: クラッシュ時は遷移と packet の両方が消えて中間状態が残らず、再実行で遷移＋learning packet が揃ってちょうど 1 回成立する
- **fixture**: seed: running lower run（brief digest 保持）＋commit 直前で kill する pytest フック
- **観測点**: 再起動後の loop_runs.state／tactical_learning_packets 件数／state_transitions ／ **期待状態**: 1 回目クラッシュ後 = running・TLP 0 件、再実行後 = completed・TLP 1 件
- **期待 DB 差分**: 最終: loop_runs UPDATE 1 行、tactical_learning_packets +1 行、state_transitions +1 行 ／ **期待証跡**: TLP 行（digest 三者一致）と終端の state_transitions 行
- **禁止副作用**: 遷移のみ成立した孤児終端 run・TLP 二重生成 ／ **エラー型**: なし（復旧正常系）
- **対象更新**: S0.1（DU-02 — 同一 transaction 契約） ／ **TC**: （割当待ち）

## SR-09

### AC-SR-04（拒否）

- **Given**: 下流・コネクタ・計測処理に相当する呼出経路 ／ **When**: strategic_briefs／TLP の内容列を直接 UPDATE/DELETE しようとする ／ **Then**: DDL 保護トリガが拒否し、書込みは issue/supersede_strategic_brief の 2 API のみ許される
- **fixture**: seed 済み brief（id=1 参照つき・id=2 未参照）への直接 DML 4 種
- **観測点**: sqlite3.IntegrityError のメッセージ（'append-only'） ／ **期待状態**: 正本無変更
- **期待 DB 差分**: 差分なし ／ **期待証跡**: なし（拒否はトリガ層）
- **禁止副作用**: 上流正本の行変更 ／ **エラー型**: IntegrityError（append-only）
- **対象更新**: S0.1（保護トリガ） ／ **TC**: STC-I-04

### AC-SR-09-1（正常）

- **Given**: 終端に達した lower run と正規の TLP payload（recommended_next_action = modify_tactic） ／ **When**: kernel 経由で TLP を提出する ／ **Then**: TLP は受理され、strategic_briefs の全行（内容列・status とも）が提出前後で変化しない — 還流は提出のみで完結する
- **fixture**: seed: active brief＋終端遷移直前の lower run＋learning payload
- **観測点**: tactical_learning_packets SELECT／strategic_briefs 全行の前後比較（digest 含む） ／ **期待状態**: TLP 1 件・brief 完全不変
- **期待 DB 差分**: tactical_learning_packets +1 行のみ（brief 差分なし） ／ **期待証跡**: TLP 行（evidence_ids で run の証跡へ接続）
- **禁止副作用**: strategic_briefs のいかなる列の変更 ／ **エラー型**: なし
- **対象更新**: S0.1（DU-02 — 還流経路） ／ **TC**: （割当待ち）

### AC-SR-09-2（境界・復旧）

- **Given**: recommended_next_action = request_strategy_review の TLP が同一 brief に対し複数 run から提出された状態 ／ **When**: 全 TLP 提出後に strategic_briefs を検査する ／ **Then**: 戦略見直し推奨が何件積まれても brief は 1 バイトも変わらない（推奨は上流への入力であり決定ではない）— 変更は上流の revision 手続きのみが行える
- **fixture**: seed: active brief＋終端 lower run 3 件（各 request_strategy_review の TLP）
- **観測点**: strategic_briefs 全行の前後比較／tactical_learning_packets 件数 ／ **期待状態**: TLP 3 件・brief 完全不変（status も active のまま）
- **期待 DB 差分**: tactical_learning_packets +3 行のみ ／ **期待証跡**: 3 件の TLP 行（recommended_next_action = request_strategy_review）
- **禁止副作用**: 推奨の蓄積による brief の自動 supersede・status 自動遷移 ／ **エラー型**: なし
- **対象更新**: S0.1（DU-02/10 — 推奨≠決定の境界） ／ **TC**: （割当待ち）

## SR-10

### AC-SR-10-1（正常）

- **Given**: 異なる ID の支持根拠 2 件・counter_evidence_ids = []（明示）・信頼度・対象版一致の refine 提案 ／ **When**: revision を accepted として適用する ／ **Then**: new_version_id を持つ新版（supersedes_id = target_id）が生成され、旧版が superseded へ遷移し、revision 記録とともに単一 transaction で成立する
- **fixture**: seed: 意味モデル v1（active）＋TLP 由来の根拠 2 件＋refine 提案 payload
- **観測点**: revision 記録／新版・旧版の SELECT（supersedes_id・status） ／ **期待状態**: v2 = active・v1 = superseded・revision = accepted
- **期待 DB 差分**: 新版 +1 行、旧版 status UPDATE、revision 記録 +1 ／ **期待証跡**: strategy_revision 行（根拠 2 件・反証空配列明示・信頼度・対象版）
- **禁止副作用**: 旧版内容列の変更・transaction 分割による中間状態 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス — SCM-08） ／ **TC**: （割当待ち）

### AC-SR-10-2（拒否）

- **Given**: 支持根拠 1 件（単一の計測値）だけの accept 提案と、counter_evidence_ids フィールド自体を欠いた提案 ／ **When**: revision の accepted 適用を試行する ／ **Then**: 両方とも RevisionEvidenceRejected（G-REVISION-EVIDENCE）で拒否され、新版・旧版遷移とも発生しない
- **fixture**: seed: 意味モデル v1＋根拠 1 件（KPI 計測のみ）の提案＋反証フィールド欠落の提案
- **観測点**: raise される例外型／意味モデル行数・status／operation_log SELECT ／ **期待状態**: v1 = active のまま・revision accepted 0 件
- **期待 DB 差分**: operation_log +2 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（根拠不足／反証未明示）
- **禁止副作用**: 単一計測値による自動 accept・新版の先行生成 ／ **エラー型**: RevisionEvidenceRejected
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

### AC-SR-10-3（境界・復旧）

- **Given**: 同一根拠 ID を 2 回列挙した提案（実質 1 件）、異なる ID ちょうど 2 件の提案、maintain 提案の 3 ケース ／ **When**: 各 revision の適用を実行する ／ **Then**: 重複 ID は uniqueItems 違反で拒否、異なる 2 件は accept 成立（最低境界）、maintain は new_version_id なしで revision 記録のみ残り「見て維持した」が記録される
- **fixture**: seed: 根拠 [E1, E1] の提案＋[E1, E2] の提案＋maintain 提案
- **観測点**: raise される例外型／revision 記録／版の増減 ／ **期待状態**: 重複 = 拒否、2 件 = v2 生成、maintain = 版不変・記録 1 件
- **期待 DB 差分**: 新版 +1（2 件ケースのみ）、revision 記録 +2（accept・maintain）、operation_log +1（拒否） ／ **期待証跡**: maintain の revision 記録（版遷移なし）
- **禁止副作用**: 重複 ID の 2 件扱い・maintain での版生成 ／ **エラー型**: RevisionEvidenceRejected（重複時）
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

## SR-11

### AC-SR-05（拒否）

- **Given**: 既存の strategic_brief／TLP 行 ／ **When**: UPDATE・DELETE（上書き・削除）を実行する ／ **Then**: append-only トリガが IntegrityError（'append-only' を含む）で拒否する（FK 等の別要因でのマスクなし）
- **fixture**: 未参照 brief id=2 への DELETE を含む DML 4 本
- **観測点**: 各 DML の例外型とメッセージ ／ **期待状態**: 全行が実行前と同一
- **期待 DB 差分**: 差分なし ／ **期待証跡**: なし（拒否・算出は証跡対象外）
- **禁止副作用**: 1 本でも成功する DML ／ **エラー型**: IntegrityError（append-only）
- **対象更新**: S0.1（append-only 版管理） ／ **TC**: STC-I-06

### AC-SR-11-1（正常）

- **Given**: active な strategic_brief v1 が存在する状態 ／ **When**: supersedes_id = v1 を持つ v2 を INSERT し、v1 の status を superseded へ遷移させる ／ **Then**: v2 が追加され、v1 は内容列不変のまま履歴として残存し、supersedes_id で版連鎖を復元できる
- **fixture**: seed: brief v1（active）＋v2 payload（supersedes_id = v1）
- **観測点**: strategic_briefs SELECT（全列前後比較・supersedes_id 連鎖） ／ **期待状態**: v1 = superseded（内容不変）・v2 = active
- **期待 DB 差分**: strategic_briefs +1 行、v1 の status UPDATE のみ ／ **期待証跡**: 版連鎖そのもの（v2.supersedes_id = v1.id）
- **禁止副作用**: v1 内容列の変更・v1 の削除 ／ **エラー型**: なし
- **対象更新**: S0.1（DU-10 — 版連鎖） ／ **TC**: （割当待ち）

### AC-SR-11-2（境界・復旧）

- **Given**: active な strategic_brief 行（内容列＋status・valid_until） ／ **When**: status のみの UPDATE、valid_until のみの UPDATE、内容 1 列（media_role）だけの UPDATE をそれぞれ実行する ／ **Then**: status・valid_until の UPDATE は許可され（トリガ WHEN 境界内）、内容列は 1 列でも IntegrityError（'append-only'）で拒否される — 拒否後も行は無傷で残る
- **fixture**: seed: active brief 1 行、UPDATE 文 3 種
- **観測点**: raise される例外型（メッセージに 'append-only' を含む）／行の前後比較 ／ **期待状態**: status・valid_until のみ更新済み、内容列は初期値のまま
- **期待 DB 差分**: 許可 2 列の UPDATE のみ（内容差分なし） ／ **期待証跡**: IntegrityError の pytest 捕捉記録（トリガ主体の拒否 — FK 等の別要因でない）
- **禁止副作用**: 内容列の部分更新・拒否時の行破損 ／ **エラー型**: IntegrityError（内容列 UPDATE 時）
- **対象更新**: S0.1（DU-10 — トリガ WHEN 境界） ／ **TC**: （割当待ち）

## SR-12

### AC-SR-12-1（正常）

- **Given**: WF-MEAS-1 で取得した PV 計測と、KPI ノード参照の metrics を持つ TLP ／ **When**: 計測投入と TLP 提出を実行する ／ **Then**: kpi_nodes／measurements（観測背骨）と TLP のみが更新され、意味モデル正本・strategic_briefs は不変である
- **fixture**: seed: kpi_nodes（PV node）＋measurement fixture＋learning TLP（metrics = node 参照）
- **観測点**: measurements SELECT／strategic_briefs 全行の前後比較 ／ **期待状態**: 計測・TLP 受理、意味正本不変
- **期待 DB 差分**: measurements +N 行、tactical_learning_packets +1 行（brief 差分なし） ／ **期待証跡**: measurements 行（evidence_id 接続）と TLP の metrics 参照
- **禁止副作用**: 計測投入による意味モデル・brief の変更 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス — KPI/意味正本の分離） ／ **TC**: （割当待ち）

### AC-SR-12-2（拒否）

- **Given**: PV 急落という単一の計測値変動だけを根拠とした戦略モデルの自動 revision accept 要求 ／ **When**: revision 適用を試行する ／ **Then**: SR-10 の根拠規律（支持根拠 ≥2・重複不可）により RevisionEvidenceRejected で拒否され、数値変化だけでは戦略が変わらない
- **fixture**: seed: 意味モデル v1＋根拠 = 計測 1 件のみの accept 提案
- **観測点**: raise される例外型／意味モデルの版・status ／ **期待状態**: 意味モデル不変（v1 = active）
- **期待 DB 差分**: operation_log +1 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（理由 = 単一計測値根拠）
- **禁止副作用**: KPI 変動による戦略正本の自動更新 ／ **エラー型**: RevisionEvidenceRejected
- **対象更新**: S1（上流戦略スライス — SCM-08） ／ **TC**: （割当待ち）

### AC-SR-12-3（境界・復旧）

- **Given**: 閾値超の KPI 異常値（急変）が計測された下流 run ／ **When**: run を終端させ TLP を生成する ／ **Then**: 異常は TLP の anomalies と recommended_next_action = request_strategy_review として還流されるに留まり、意味正本・brief への自動書込みは発生しない（決定は上流）
- **fixture**: seed: 異常値 measurement fixture＋終端 lower run
- **観測点**: TLP の anomalies_json・recommended_next_action／strategic_briefs の前後比較 ／ **期待状態**: TLP 1 件（異常記録つき）・意味正本不変
- **期待 DB 差分**: tactical_learning_packets +1 行のみ ／ **期待証跡**: TLP 行（anomalies・request_strategy_review）
- **禁止副作用**: 急変を契機とした brief の自動 supersede・意味モデル自動更新 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

## SR-13

### AC-SR-13-1（正常）

- **Given**: 5 宣言（defined_problem・recognition_change・comparison_axes・defined_value・target_hypothesis_ids）を実質記入した主要コンテンツ企画 ／ **When**: T-PLAN の plan_record 承認を実行する ／ **Then**: content-plan-contract.json 適合として承認され、5 宣言が evidence（plan_record）の payload_json に保持される
- **fixture**: fixture: json/strategy/fixtures/ の valid content plan（5 キー完備）
- **観測点**: 承認 API 戻り値／evidence SELECT（kind = plan_record） ／ **期待状態**: 企画承認済み・plan_record 証跡 1 件
- **期待 DB 差分**: evidence +1 行（plan_record） ／ **期待証跡**: evidence 行（payload_json に 5 宣言）
- **禁止副作用**: operation_log への拒否行 ／ **エラー型**: なし
- **対象更新**: S1（SCM-10 — 実行時強制。S1 前半は docs ゲート） ／ **TC**: （割当待ち）

### AC-SR-13-2（拒否）

- **Given**: recognition_change キーを欠いた集客目的のコンテンツ企画 ／ **When**: T-PLAN の plan_record 承認を実行する ／ **Then**: ContentValueDeclarationRejected（G-CONTENT-VALUE-DEFINITION）で承認が拒否され、集客目的であることは免除理由にならない
- **fixture**: fixture: json/strategy/fixtures/ の invalid content plan（recognition_change 欠落）
- **観測点**: raise される例外型／evidence 件数／operation_log SELECT ／ **期待状態**: 企画未承認・plan_record 0 件
- **期待 DB 差分**: operation_log +1 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（欠落キー = recognition_change）
- **禁止副作用**: 宣言なし企画の主要企画としての承認 ／ **エラー型**: ContentValueDeclarationRejected
- **対象更新**: S1（SCM-10） ／ **TC**: （割当待ち）

### AC-SR-13-3（境界・復旧）

- **Given**: 5 キーが存在するが comparison_axes = []・defined_value = 空文字の企画と、target_hypothesis_ids が実在しない仮説 ID を指す企画 ／ **When**: 両企画の承認を実行する ／ **Then**: 空配列・空文字は「未宣言」として拒否され、実在しない仮説参照も拒否される — 宣言補完後の再提出は承認される
- **fixture**: fixture: 空値 5 キー企画＋架空 ID 参照企画、その後の補完版
- **観測点**: raise される例外型／再提出後の evidence SELECT ／ **期待状態**: 初回 2 件拒否→補完後 1 件承認
- **期待 DB 差分**: operation_log +2 行（拒否）、その後 evidence +1 行 ／ **期待証跡**: operation_log 拒否行（空値／参照不整合）
- **禁止副作用**: 空値の宣言扱い（fail-open） ／ **エラー型**: ContentValueDeclarationRejected
- **対象更新**: S1（SCM-10） ／ **TC**: （割当待ち）

## SR-14

### AC-SR-14-1（正常）

- **Given**: media_role = 'problem-framing'（media-roles.json 台帳語彙）を宣言した brief draft ／ **When**: issue_strategic_brief を実行する ／ **Then**: 台帳照合に合格して brief が発行され、media_role 列に役割語彙が保存される
- **fixture**: seed: media-roles.json（12 語彙）＋valid brief draft（problem-framing）
- **観測点**: strategic_briefs SELECT（media_role 列） ／ **期待状態**: brief 1 行発行（media_role = problem-framing）
- **期待 DB 差分**: strategic_briefs +1 行 ／ **期待証跡**: brief 行そのもの（役割語彙保存）
- **禁止副作用**: operation_log への拒否行 ／ **エラー型**: なし
- **対象更新**: S1（SCM-09 — G-MEDIA-ROLE） ／ **TC**: （割当待ち）

### AC-SR-14-2（拒否）

- **Given**: media_role = 'wordpress'（媒体名）と media_role = 'Proof'（大文字揺れ）を宣言した brief draft 2 件 ／ **When**: issue_strategic_brief を実行する ／ **Then**: 両方とも MediaRoleRejected（G-MEDIA-ROLE）で発行が拒否され、宣言値と台帳語彙が operation_log に残る
- **fixture**: seed: media-roles.json＋invalid draft 2 件（媒体名・大小文字揺れ）
- **観測点**: raise される例外型／strategic_briefs 件数／operation_log SELECT ／ **期待状態**: brief 0 件発行
- **期待 DB 差分**: operation_log +2 行（拒否）のみ ／ **期待証跡**: operation_log 拒否行（宣言値・台帳版）
- **禁止副作用**: 媒体名の media_role としての保存・揺れの自動正規化 ／ **エラー型**: MediaRoleRejected
- **対象更新**: S1（SCM-09） ／ **TC**: （割当待ち）

### AC-SR-14-3（境界・復旧）

- **Given**: media-roles.json が欠損（削除・パース不能）した環境 ／ **When**: 任意の media_role で brief 発行を試行し、その後台帳を復旧して再発行する ／ **Then**: 台帳欠損時は全宣言が拒否され（deny-by-default）、台帳復旧後の再発行は成立する
- **fixture**: seed: media-roles.json を削除した環境→復旧した環境、valid draft
- **観測点**: raise される例外型／復旧後の strategic_briefs SELECT ／ **期待状態**: 欠損時 0 件・復旧後 1 件発行
- **期待 DB 差分**: operation_log +1 行（拒否）、復旧後 strategic_briefs +1 行 ／ **期待証跡**: operation_log 拒否行（理由 = 台帳ロード不能）
- **禁止副作用**: 台帳欠損時の全許可（fail-open） ／ **エラー型**: MediaRoleRejected（台帳欠損時）
- **対象更新**: S1（SCM-09） ／ **TC**: （割当待ち）

## SR-15

### AC-SR-15-1（正常）

- **Given**: S0.1 実装完了時点のリポジトリ（DDL・シードコマンド・kernel・トリガ・12 schema） ／ **When**: python-ci で STC-I-01〜06 の pytest と validate_requirements.py を実行する ／ **Then**: S0 必須 5 点（brief シード／run の id・digest 保持／TLP 生成／直接変更不可／schema・実装契約確定）がすべて green で検証され、S0.1 完了条件が成立する
- **fixture**: fixture: 空 SQLite＋migration 0001＋json/strategy/ の 12 schema・fixtures
- **観測点**: python-ci の pytest レポート（STC-I-01〜06）／validate_requirements.py 終了コード ／ **期待状態**: STC-I-01〜06 全 green・全ゲート PASS
- **期待 DB 差分**: 差分なし（検証のみ — テスト DB は使い捨て） ／ **期待証跡**: CI ログ（pytest green・ゲート PASS）
- **禁止副作用**: S0 スコープ外機能（上流生成系）の実装混入 ／ **エラー型**: なし
- **対象更新**: S0.1（完了ゲート — STC-I-01〜06） ／ **TC**: （割当待ち）

### AC-SR-15-2（拒否）

- **Given**: S0 の FN 数を増やす・SCM-05〜10（上流生成系）の実装を S0 に混入させる・STC-I の分母を減らすコミット ／ **When**: validate_requirements.py（baseline 照合）と python-ci を実行する ／ **Then**: ratchet／baseline 違反として CI が fail-close で赤になり、S0.1 完了と main への取込みが認められない
- **fixture**: fixture: baseline.json の分母と矛盾する要件 JSON／スコープ外実装を含むブランチ
- **観測点**: validate_requirements.py の終了コードとエラーメッセージ／CI ジョブ結果 ／ **期待状態**: CI 赤・コミット差戻し
- **期待 DB 差分**: 差分なし（検証のみ） ／ **期待証跡**: CI ログ（baseline 違反・ゲート名つき）
- **禁止副作用**: 分母縮小・スコープ拡大の黙認（fail-open） ／ **エラー型**: GateFailure（CI exit 非 0）
- **対象更新**: S0.1（G-BASELINE／ratchet） ／ **TC**: （割当待ち）

## SR-16

### AC-SR-16-1（正常）

- **Given**: 上流 run の 1 回転中に、segment_context を対象とする accepted refine revision（新版生成つき）が 1 件成立した状態 ／ **When**: 上流ループの一周判定を実行する ／ **Then**: 意味モデルが revision を経て更新されたため一周（True）と判定され、ループ計数に 1 が記録される
- **fixture**: seed: upper run＋accepted revision（target_type = segment、new_version_id あり）
- **観測点**: 一周判定 API 戻り値／ループ計数記録 ／ **期待状態**: 一周判定 = True・計数 +1
- **期待 DB 差分**: ループ計数記録 +1（upper run メタデータ） ／ **期待証跡**: accepted revision 行と新版行（supersedes_id 連鎖 — 一周の根拠）
- **禁止副作用**: 同一回転の重複計上 ／ **エラー型**: なし
- **対象更新**: S1（上流戦略スライス — SCM-08） ／ **TC**: （割当待ち）

### AC-SR-16-2（拒否）

- **Given**: brief の微修正（行動計画のみの supersede）だけで意味モデルの revision がゼロの上流回転 ／ **When**: 一周判定を実行する ／ **Then**: 行動計画の微修正だけの回転は一周と数えられず、判定 False・計数は増えない
- **fixture**: seed: upper run＋brief v2 発行のみ（意味モデル revision なし）
- **観測点**: 一周判定 API 戻り値／ループ計数記録 ／ **期待状態**: 一周判定 = False・計数不変
- **期待 DB 差分**: ループ計数の差分なし ／ **期待証跡**: なし（計上されないことが期待 — revision 記録の不在を確認）
- **禁止副作用**: 微修正回転の一周計上（管理ループへの縮退） ／ **エラー型**: なし（判定 False — 例外ではない）
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）

### AC-SR-16-3（境界・復旧）

- **Given**: maintain revision のみの回転と、同一回転で 2 つの意味モデル（market_model・value_hypothesis）が更新された回転、revision 記録が欠損した回転の 3 ケース ／ **When**: 各回転の一周判定を実行する ／ **Then**: maintain のみは更新なしとして False、複数モデル更新でも一周は 1 回（重複計上なし）、記録欠損は判定不能として一周にしない側へ倒れる（fail-close）
- **fixture**: seed: maintain のみの run／2 モデル accepted の run／revision 記録を欠いた run
- **観測点**: 一周判定 API 戻り値／ループ計数記録 ／ **期待状態**: False・True（計数 +1）・False
- **期待 DB 差分**: ループ計数 +1（複数更新ケースのみ） ／ **期待証跡**: maintain の revision 記録（「見て維持」— 計上されない根拠）
- **禁止副作用**: 複数更新の多重計上・判定不能時の一周扱い（fail-open） ／ **エラー型**: なし（判定 False — 例外ではない）
- **対象更新**: S1（上流戦略スライス） ／ **TC**: （割当待ち）
