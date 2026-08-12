<!-- GENERATED FILE — 編集禁止。正本は docs/L3-system-requirements/canonical/functional/fr-contracts.json。再生成 = python3 scripts/render_views.py -->

# 機能要件 実行契約（FR contracts） v0.1

> status: **confirmed**（2026-08-01 PO 承認 — receipt bbb591341b15）。JSON 内容正本の生成ビュー（全層再降下 §3）
> 各 FR に 18 観点の実行・検証・拒否・復旧契約を必須化（G-REQ-CONTRACT／G-INVARIANT-TRACE）。

## FR-11 ループ状態機械

- **入力**: イベント（str — cli/kernel 発火）／対象 loop_run_id（int — loop_runs）／ガード評価に必要な現 DB 状態（sqlite3.Connection）
- **出力**: 新状態へ更新された loop_runs 行／state_transitions への遷移証跡行／拒否時: TransitionRejected 例外（理由つき）
- **事前条件**: 対象 loop_run が存在する／遷移表（transitions.json 由来）がロード済み／DB マイグレーション適用済み（DU-11 verify() green）
- **事後条件**: (現状態, イベント) に合致する遷移が 1 件だけ適用されている／state_transitions に遷移 1 行が追記されている／ガード不成立時は状態が変化していない
- **不変条件**: 終端状態からの遷移は存在しない／遷移は宣言表にある (entity, from, event) のみ／lower run は有効 strategic_brief の id/digest を保持し続ける（SR-07）
- **状態遷移**: loop_runs: 遷移表（json/s0/transitions.json）の全行が本 FR の対象
- **正常動作**: イベント受領 → 遷移表から (現状態, イベント) を一意解決 → ガード条件を DB 状態で評価 → 成立なら loop_runs.state を次状態へ UPDATE し state_transitions へ証跡 INSERT（同一 transaction）。
- **拒否・異常動作**: 遷移表に合致がない・ガード不成立・終端からの遷移要求は TransitionRejected を raise する。loop_runs の業務状態は変更せず、state_transitions に guard_result = rejected の拒否行だけを同一 transaction で追記する（fail-close）。
- **境界動作**: 同一 run への同時イベントは transaction の直列化で 1 件のみ成立し、後続は再読込後に再判定。存在しない run_id は即拒否。
- **再試行・再開・復旧**: クラッシュ時は transaction ごと消えるため中間状態が残らない。再開はプロセス再起動後に loop_runs の現状態から続行（申し送りなし — BR-A1）。
- **人間判断／escalation**: なし（全自動。escalated への遷移後の対処は BR-H3 経由で人間）
- **副作用**: loop_runs UPDATE／state_transitions INSERT／state_transitions INSERT（拒否時 — guard_result = rejected）
- **冪等性**: 同一イベントの再送は現状態不一致で拒否される（状態遷移自体が冪等キー）。証跡は重複しない。
- **証跡**: state_transitions 行（遷移ごと）／state_transitions 行（拒否ごと、guard_result = rejected）
- **使用テーブル・正本**: 参照: 遷移表 JSON 正本（json/s0/transitions.json — DB テーブルではない）／rw: loop_runs／w: state_transitions／r: strategic_briefs（lower 開始ガード）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 遷移表（transitions.json — 変更は要件改訂）
- **trace**: 上流 = BR-A1 REQ-001 REQ-002 REQ-006 ／ 下流 = AC-11-1 AC-11-2 AC-11-3 AC-11-4 AC-11-5 AC-11-6 FN-101 CMP-01 ／ スライス = S0

## FR-12 タスク発行

- **入力**: ループステップ到達イベント（loop_run_id: int・step_key: str — kernel オーケストレータ発火）／workflow 定義（workflows 行 — task_type・definition_json・required_evidence_json）／エージェント登録（agents 行 — role・principal・status）
- **出力**: tasks 行（workflow_id・author_agent_id・verifier_agent_id・expected_output_kind すべて非 NULL、state = pending）／拒否時: TaskIssuanceRejected 例外（理由つき）
- **事前条件**: 親 loop_run が running 状態で存在する／step_key に対応する active な workflow が存在する／author/verifier に割当可能な active agent が存在する（principal の異なる 2 体）／T-PUB の場合: pair_plan_quality（status = passed）が成立している（T-R2）
- **事後条件**: tasks に 1 行が INSERT され、ワークフロー ID・担当・期待成果物型がすべて非 NULL（AC-12）／author_agent_id != verifier_agent_id かつ principal が異なる（自己審査禁止 FR-27 の前提充足）／idempotency_key と UNIQUE(loop_run_id, step_key, attempt) が既存行と衝突していない
- **不変条件**: T-PUB は審査 PASS のペア成立なしに生成されない（T-R2 — 発行段階で拒否）／tasks.verifier_agent_id は全タスクで必須（NULL の三値論理に委ねない — s0-contract §1）／発行済み行の workflow_id・担当は発行後に差し替えない（再発行は新 attempt 行）
- **状態遷移**: tasks: 発行は state = pending の行 INSERT（遷移前）。以降の pending→in_progress→verifying→done/failed/escalated は s0-contract §3.2 遷移表を FR-11 の状態機械が駆動
- **正常動作**: ループステップ到達 → workflows から step_key/task_type に対応する active 定義を一意解決 → assigner が role と principal 差で author/verifier を割当 → idempotency_key を付与して tasks 行を INSERT（state = pending、expected_output_kind = workflow 宣言の出力型）。
- **拒否・異常動作**: workflow 不在・active agent 不足・author と verifier の principal 同一・T-PUB のペア未成立は TaskIssuanceRejected を raise し tasks に行を作らない（fail-close）。自己審査割当は DB CHECK（author_agent_id != verifier_agent_id）でも二重に拒否される。
- **境界動作**: 同一 (loop_run_id, step_key, attempt) の再発行は UNIQUE 制約で 1 件のみ成立。同一 idempotency_key の再送は既存 tasks 行を返し重複行を作らない。差戻し再試行は attempt の別行ではなく同一行の retry_count で数える（§3.2）。
- **再試行・再開・復旧**: 発行は単一 transaction の INSERT であり、クラッシュ時は行ごと消える。再起動後はループステップの再評価で同一 idempotency_key により再発行され、既存行があればそれを採用して続行する（申し送りなし — BR-A1）。
- **人間判断／escalation**: なし（全自動。割当不能の恒常化は FR-16 経由で escalated）
- **副作用**: tasks INSERT
- **冪等性**: idempotency_key（UNIQUE）と (loop_run_id, step_key, attempt) の UNIQUE が重複発行を検出し、再実行は既存行の採用に収束する（二重発行なし）。
- **証跡**: tasks 行そのもの（発行記録の正本 — workflow_id・担当・期待成果物型）／state_transitions 行（発行後の claim 以降の遷移で記録）
- **使用テーブル・正本**: r: loop_runs（親 running 検査）／r: workflows（定義解決）／r: agents（割当候補・principal 検査）／r: pair_plan_quality（T-PUB ガード）／w: tasks
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: タスク型カタログ（T-PLAN〜T-OPS — loop-task-workflow §2.1。author/verifier 役割と必須証跡 kind の割当）
- **trace**: 上流 = BR-A4 REQ-007 ／ 下流 = AC-12-1 AC-12-2 AC-12-3 AC-12-4 AC-12-5 AC-12-6 FN-102 FN-104 CMP-02 ／ スライス = S0

## FR-13 検証マイクロループ

- **入力**: verifying 到達タスク（tasks 行 — output_json 保存済み）／検証結果（verifier agent の PASS/FAIL 判定＋FAIL 時の差戻し理由）／config.retry_limit（int — config 有効値。暫定既定値 3）
- **出力**: PASS: done へ遷移した tasks 行／FAIL: in_progress へ差し戻された tasks 行（retry_count +1・差戻し理由記録）／リトライ上限到達: escalated へ遷移した tasks 行／ガード不成立時: TransitionRejected 例外
- **事前条件**: 対象 task が verifying 状態で存在する／verifier が author と principal の異なる active agent である／config.retry_limit の有効値が解決できる
- **事後条件**: verify_pass: 全必須証跡・全ゲート PASS を確認したうえで done に遷移している／verify_fail: retry_count が 1 だけ増加し、差戻し理由（failure_detail）と verifier 証跡が残っている／retry_count + 1 >= config.retry_limit の FAIL は verify_fail_exhausted で escalated に遷移している
- **不変条件**: retry_count を消費するのは verify_fail 系イベントのみ（通信再送は同一 idempotency key の無消費再送 — §3.2）／PASS の判定者は常に author と別 principal（自己審査禁止 FR-27）／差戻し理由・verifier 証跡を欠く FAIL 遷移は存在しない
- **状態遷移**: tasks: verifying → done（verify_pass）／tasks: verifying → in_progress（verify_fail・retry_count を 1 増加）／tasks: verifying → escalated（verify_fail_exhausted・retry_count を 1 増加）
- **正常動作**: verifying 到達で検証エージェント（verifier）を起動 → 出力・必須証跡・通過ゲートを検査 → PASS なら verify_pass で done、FAIL なら差戻し理由と verifier 証跡を伴い verify_fail で in_progress へ戻して retry_count を 1 増加（各遷移は state_transitions 記録つき単一 transaction）。
- **拒否・異常動作**: 差戻し理由又は verifier 証跡を欠く FAIL、verifier の principal が author と同一、verifying 以外の状態への verify_* 適用は TransitionRejected を raise し、状態・retry_count を変更せず state_transitions に guard_result = rejected で記録する（fail-close）。
- **境界動作**: retry_count + 1 >= config.retry_limit（暫定 3）の FAIL は in_progress へ戻さず verify_fail_exhausted で escalated（retry_count は 1 増加）。retry_count = limit - 1 が最後の差戻し機会であり、境界ちょうどで escalated 側へ倒れる。
- **再試行・再開・復旧**: 強制終了時は §3.3 に従い verifier が既存出力・証跡を再検証する。PASS/FAIL 証跡が既にあれば同じ結果を採用し、retry_count を二重加算しない。escalated 到達後は終端であり新 task の明示発行まで遷移しない。
- **人間判断／escalation**: escalated 到達後の対処のみ人間（BR-H3 — FR-16 経由の通知）。PASS/FAIL 判定と差戻しは全自動
- **副作用**: tasks UPDATE（state・retry_count・failure_detail）／state_transitions INSERT
- **冪等性**: 同一 FAIL の再適用は現状態不一致（in_progress）で拒否され retry_count の二重加算は起きない。再検証は既存 PASS/FAIL 証跡を採用して同一結果に収束する。
- **証跡**: evidence: review_pass（PASS 時 — T-REVIEW の証跡）／state_transitions 行（verify_fail／verify_fail_exhausted の遷移・rejected 記録）／tasks.failure_detail（差戻し理由）
- **使用テーブル・正本**: rw: tasks／w: state_transitions／r: config（retry_limit）／r: evidence（必須証跡・verifier 証跡の検査）／r: agents（principal 検査）
- **外部依存**: なし
- **設定値**: config.retry_limit（C・暫定既定値 3 — 差戻し上限） ／ **固定値**: なし
- **trace**: 上流 = BR-A4 REQ-003 ／ 下流 = AC-13-1 AC-13-2 AC-13-3 AC-13-4 AC-13-5 AC-13-6 AC-13-7 AC-13-8 AC-13-9 FN-103 CMP-02 ／ スライス = S0

## FR-17 Kanban pull・WIP・blocked・flow 制御

- **入力**: pull 要求（business_profile_id, bounded_domain_id, lane, principal_id）／ready queue（優先順位・class_of_service・依存・DoR を持つ work item）／flow policy（config.kanban.<domain>.wip_limits／pull_policy／blocked_policy／cadence）
- **出力**: pull 成立: claim 済み work item と pending→in_progress 遷移／拒否時: GateRejected（WIP 上限・DoR/依存未充足・binding 非 active の理由つき）／flow snapshot（WIP・throughput・lead_time・cycle_time・work_item_age・blocked_time）
- **事前条件**: work item が ready policy と依存関係を満たし、対象 domain と active media_binding に scope されている／対象 lane の WIP limit と現 WIP が同一 transaction 内で評価可能である／replenishment で優先順位と class_of_service が確定している
- **事後条件**: pull 成立後も lane WIP は設定上限以下である／拒否された work item の状態・claim owner・WIP は不変である／blocked/unblocked は理由・時刻・解除条件を持つ状態履歴として再計算可能である
- **不変条件**: work item は push で in_progress へ投入されず、全 claim が pull gate を通る／WIP limit 超過を priority や expedite の自由記述で迂回できない／Scrum cadence 到達だけを理由に進行中 item を強制完了・強制取消ししない
- **状態遷移**: なし
- **正常動作**: ready queue を priority・class_of_service・age の決定的 policy で評価し、対象 lane の現 WIP が上限未満の場合だけ最上位 eligible item を claim して in_progress へ遷移する。replenishment は ready queue を補充し、review/retrospective は flow snapshot と TLP を評価するが、Kanban の連続運転を停止しない。
- **拒否・異常動作**: WIP 上限到達、DoR/依存未充足、domain scope 不一致、paused/retired media_binding、push による直接開始は GateRejected とし、tasks・claim・WIP を変更しない。拒否理由は構造化ログと遷移 guard_result に残す。
- **境界動作**: WIP limit=0 は lane 停止として全 pull を拒否する。expedite は設定された専用上限内のみ許可する。blocked item は policy で WIP に含めるかを明示し、未定義なら含める側へ倒す。cadence 境界を跨ぐ item は同一 ID・状態のまま継続する。
- **再試行・再開・復旧**: pull と WIP 判定は単一 transaction とし、競合 claim は更新 0 行で一方だけ成立する。クラッシュ後は tasks・state_transitions・config から queue と WIP を再構成し、メモリ上のボードを正本にしない。
- **人間判断／escalation**: 人間: replenishment の優先順位、class_of_service、WIP policy の変更、長期 blocked の解消。通常 pull と gate は全自動
- **副作用**: tasks UPDATE（claim・state・blocked metadata の S1 拡張）／state_transitions INSERT（pull/block/unblock の成立・拒否）／構造化 flow snapshot 生成
- **冪等性**: 同一 work item の pull は現 state と claim token を冪等条件とし二重 claim しない。flow 指標は同一履歴・同一時刻窓から同一値を再計算する。
- **証跡**: state_transitions 行（pull/block/unblock と guard_result）／flow snapshot（算出窓・policy version・対象 item ID つき）
- **使用テーブル・正本**: rw: tasks（S1 で blocked metadata を expand）／w: state_transitions／r: config（Kanban policy）／参照: S1 schema で追加する media_bindings・bounded_domains（scope と active 判定）
- **外部依存**: なし
- **設定値**: config.kanban.<domain>.wip_limits／config.kanban.<domain>.pull_policy／config.kanban.<domain>.blocked_policy／config.kanban.<domain>.cadence ／ **固定値**: pull gate 必須・未定義 blocked policy は WIP に含める（fail-close）
- **trace**: 上流 = BR-J1 REQ-053 ／ 下流 = AC-17-1 AC-17-2 AC-17-3 ／ スライス = S1

## FR-35 bounded domain registry と safe workspace 解決

- **入力**: domain 登録要求（business_profile_id, domain_key, domain_type, display_name, manifest_version）／workspace 解決要求（business_profile_id, bounded_domain_id, relative_path）／profile workspace registry と domain manifest
- **出力**: profile に scope された bounded_domain 登録と canonical workspace root／標準 directory（strategy／backlog／work/drafts／work/assets-src／evidence／exports）／拒否時: GateRejected（越境・重複・manifest 不一致・path/symlink escape）
- **事前条件**: 親 business_profile が active で、profile workspace root が明示設定されている／domain_key が profile 内で一意かつ slug 制約を満たす／要求 relative_path は未解決の絶対 path を含まない
- **事後条件**: bounded_domain はちょうど 1 business_profile に属し registry と manifest が同じ ID・version・root を指す／解決 path は canonical domain root 配下にあり、他 profile/domain の root と重ならない／登録失敗時は directory・registry・manifest の部分生成が残らない
- **不変条件**: business_profile と bounded_domain の二段 scope を省略した読書きは deny-by-default／domain は業務境界であり media_binding と同一視しない／drafts/assets-src/evidence は domain root 配下にのみ存在し profile/domain 間で暗黙共有しない
- **状態遷移**: なし
- **正常動作**: profile workspace root の直下に opaque な domain_key から canonical root を決定し、domain manifest と標準 directory を staging root へ生成する。registry 記録と manifest hash の検証後に atomic rename で有効化し、以降の path は resolver だけが返す。
- **拒否・異常動作**: profile 越境、domain_key 重複、絶対 path、..、NUL、root 外を指す symlink、registry/manifest の ID・version・hash 不一致は GateRejected とし、書込み前または staging cleanup 後に拒否する。
- **境界動作**: 空 profile は最初の domain 登録を許可する。archived domain は既存成果物の読取のみ許可し、新規 task・binding・ファイル書込みを拒否する。domain rename は in-place 変更せず新版 domain＋supersedes と明示 migration で扱う。
- **再試行・再開・復旧**: 登録は staging directory＋registry transaction＋atomic rename の recovery protocol とし、再開時は manifest hash で完成済み・staging・不一致を判定する。不一致は自動採用せず quarantine して escalation する。
- **人間判断／escalation**: 人間: domain の意味境界・追加・archive・migration の承認。path 検査・scope 強制・recovery は全自動
- **副作用**: bounded domain registry INSERT/UPDATE（S1 schema）／domain manifest と標準 directory の生成／不一致 staging の quarantine
- **冪等性**: (business_profile_id, domain_key, manifest_version) を冪等キーとし、同一 manifest hash の再登録は既存 root を返す。異なる hash は競合として拒否する。
- **証跡**: domain registry 行と manifest hash／workspace resolution audit（profile/domain/root/relative path）／越境・escape・不一致の拒否ログ
- **使用テーブル・正本**: r: business_profiles／r: config（profile workspace root）／参照: S1 schema で追加する bounded_domains（profile FK・domain_key・manifest hash・status）
- **外部依存**: ローカル filesystem（canonicalize・symlink 検査・atomic rename）
- **設定値**: config.workspace.<profile_key>.root ／ **固定値**: 標準 directory 名（strategy／backlog／work/drafts／work/assets-src／evidence／exports）／domain_key slug と path escape 拒否規則
- **trace**: 上流 = BR-J2 REQ-054 ／ 下流 = AC-35-1 AC-35-2 AC-35-3 ／ スライス = S1

## FR-48 戦略 trace 付き media binding lifecycle

- **入力**: binding 変更要求（business_profile_id, bounded_domain_id, media_role, service_key, connector_ref, workflow_ref, playbook_ref）／有効な strategic brief/revision と supporting evidence／停止時 policy（drain/cancel、effective_at、replacement binding）
- **出力**: 版付き media_binding（planned/active/paused/retired、supersedes_id、strategy trace）／下流 pull eligibility と解決済み connector/workflow/playbook 参照／拒否時: GateRejected（戦略 trace・scope・接続・規約・承認の不足）
- **事前条件**: business_profile と bounded_domain が active で一致する／media_role が SR-14 台帳語彙、service route が FR-41 で解決可能である／strategic brief/revision が有効期間内で binding 変更理由と対象 domain を参照する
- **事後条件**: active binding は strategy revision・media_role・connector・workflow・playbook へ完全 trace する／paused/retired binding から新規 work item は pull されない／差替え後も旧 binding・旧 run・TLP は不変で追跡可能である
- **不変条件**: media_role は戦略上の役割、media_binding は実媒体への版付き束縛であり同じ値を要求しない／binding 変更は下流から strategic_briefs を直接更新せず、上流判断→binding、TLP→上流評価の経路だけを使う／媒体追加・停止・差替えで kernel・状態機械・固定 workspace directory を変更しない
- **状態遷移**: なし
- **正常動作**: 上流の有効な brief/revision を検証し、media_role を実 service・connector route・workflow・playbook へ束縛した planned binding を INSERT する。接続・規約・承認 gate の成立後に active 化し、下流 Kanban は active binding の work item だけを pull する。下流終端結果は TLP として同じ brief/binding trace を保持して上流へ返す。
- **拒否・異常動作**: 戦略 trace 欠落、期限切れ brief、domain/profile 越境、台帳外 media_role、未解決 route、禁止媒体経路、workflow/playbook 欠落、必要承認欠如は GateRejected とし binding・task・外部操作を変更しない。
- **境界動作**: pause は新規 pull を即時停止し in-flight item は policy に従い drain または理由付き cancel とする。差替えは旧 binding を破壊せず replacement を active 化してから旧版を retired にし、同時 active を許す移行窓は明示期限内だけ認める。
- **再試行・再開・復旧**: binding lifecycle は idempotency key と現 status を条件に単一 transaction で更新する。差替え途中のクラッシュは operation record と現 status から再開し、active binding 0 件または意図しない 2 件を fail-close で検出する。
- **人間判断／escalation**: 人間: 媒体構成の戦略判断、高リスク・有償経路の承認、drain/cancel policy。trace・scope・route gate は全自動
- **副作用**: media binding registry INSERT/UPDATE（S1 schema）／binding lifecycle の構造化監査ログ／pause/retire 時の新規 pull gate 更新
- **冪等性**: (bounded_domain_id, strategy_revision_id, service_key, binding_version) と operation key で重複を検出し、同一変更要求は既存 binding を返す。
- **証跡**: binding 行（strategy/role/connector/workflow/playbook/supersedes trace）／pause/retire/difference operation の監査ログ／binding と brief/run/TLP の trace query 結果
- **使用テーブル・正本**: r: strategic_briefs／r: tactical_learning_packets／r: config（media role・connector registry）／r: workflows・playbooks／参照: S1 schema で追加する media_bindings・bounded_domains
- **外部依存**: なし
- **設定値**: config.media_roles_ledger／config.registry.<service>／config.media_binding.transition_window ／ **固定値**: binding status 語彙（planned/active/paused/retired）／差替えは新版 INSERT＋supersedes（破壊更新禁止）
- **trace**: 上流 = BR-J3 REQ-055 ／ 下流 = AC-48-1 AC-48-2 AC-48-3 ／ スライス = S1

## FR-14 スプリント制御

- **入力**: スプリント開始要求（sprint_id: int — sprints 行、status = planned）／KPI 目標（sprints.kpi_target_json ＋対応 kpi_nodes.target_json — 計画側の充足）／媒体別サイクル設定（config.loop.<媒体>.cycle）
- **出力**: 開始成立: status = active へ更新された sprints 行／拒否時: SprintStartRejected 例外（KPI 目標欠如等の理由つき）
- **事前条件**: sprint が planned 状態で存在し、active な action_plan に FK 接続している／sprint の期間が ends_at >= starts_at を満たす（DDL CHECK）／媒体のサイクル設定が config で解決できる（LP-R3）
- **事後条件**: 開始した sprint は空でない KPI 目標を保持している（LP-R2 — 開始条件 = 計画側の充足）／他媒体の sprint 状態は変化していない（独立性 — LP-R1）／開始条件未充足の sprint は planned のまま変化していない
- **不変条件**: KPI 目標（計画側の充足）を満たさない限り sprint は開始できない／媒体ごとの sprint は独立に回り、他媒体の遅延・blocked に影響されない（BR-A2 — 同期強制なし）／サイクル長・回転数の変更は config 行のみで反映されコード変更を要しない（LP-R3・NFR-8）
- **状態遷移**: テーブル列: sprints.status: planned→active（開始）／active→reviewing（期間終了・レビュー入り）／reviewing→completed（レビュー成立）／active→blocked（開始条件喪失・異常）。※ state_transitions テーブルの entity_type は loop_run/task のみのため、sprint の状態変化は sprints 行の列更新が正本（遷移ログの entity 拡張は S1 の expand migration で設計）
- **正常動作**: 開始要求 → sprints.kpi_target_json と対応 kpi_nodes.target_json を検査（KPI 目標の存在 = 計画側の充足）→ 充足なら status を planned から active へ UPDATE。同条件は下位 loop_run の start ガード（§3.1 — sprint の KPI target 存在）でも二重に強制される。
- **拒否・異常動作**: kpi_target_json が空・対象 kpi_node の target 欠如・sprint 不在・planned 以外からの開始要求は SprintStartRejected を raise し、sprints 行を変更しない（fail-close）。当該 sprint に紐づく下位 loop_run の start も §3.1 ガードで拒否され、state_transitions に rejected で記録される。
- **境界動作**: 複数媒体の sprint が並走し、一方が blocked でも他方は開始・進行できる（同期強制なし）。starts_at 前の開始要求は拒否。ends_at 到達時は reviewing へ移行し、以降の新規タスク発行を止める。
- **再試行・再開・復旧**: 開始判定は無状態（DB 読取り＋1 UPDATE）。クラッシュ時は planned のまま残り、再起動後に同じ判定を再実行して開始できる。active で中断した sprint は現 status から続行する（申し送りなし）。
- **人間判断／escalation**: なし（全自動。blocked の恒常化は FR-16 経由で通知）
- **副作用**: sprints UPDATE（status）
- **冪等性**: active への開始要求の再送は現 status 不一致で拒否され二重開始しない。開始判定は同一入力→同一結果の pure な検査。
- **証跡**: sprints 行（status 変化の正本）／state_transitions 行（当該 sprint に紐づく下位 loop_run start の guard_result — KPI target 欠如は rejected で記録）
- **使用テーブル・正本**: rw: sprints／r: action_plans（FK・active 検査）／r: kpi_nodes（target_json 検査）／r: config（媒体別サイクル）／r: loop_runs（並走・進行検査）
- **外部依存**: なし
- **設定値**: config.loop.<媒体>.cycle（媒体別サイクル長 — LP-R3。暫定値は C 充填） ／ **固定値**: sprints.status の enum（planned/active/reviewing/completed/blocked — DDL 正準）
- **trace**: 上流 = BR-A2 REQ-005 ／ 下流 = AC-14-1 AC-14-2 AC-14-3 FN-106 CMP-02 ／ スライス = S1

## FR-15 還流（learnings 生成と上位還流）

- **入力**: スプリントレビュー成立イベント（FR-22 — pair_kpi_measure 行 status = passed）／対象 sprint（sprints 行 — reviewing 状態）／レビュー根拠（kpi_nodes・measurements・evidence の参照群）
- **出力**: learnings 行（sprint_id・source_pair_id・summary・learning_json、status = draft）／上位ループ次回転の入力キュー登録（learnings を LP-U の入力として参照可能化。上流へは TLP の構成要素として還流 — §5bis）／拒否時: PairNotEstablished 例外
- **事前条件**: pair_kpi_measure（status = passed）が成立している（REQ-009 — ペア成立まで還流は発生しない）／対象 sprint が reviewing 状態である／learning_json が schema 検証を通る
- **事後条件**: learnings に source_pair_id で成立ペアへ FK 接続した行が 1 件存在する／上位ループの次回転が当該 learnings を入力として参照できる／同一 pair から learnings が重複生成されていない
- **不変条件**: ペア未成立のスプリントから learnings は生成されない（片肺禁止 — REQ-009）／還流は learnings→TLP 構成要素の経路のみで上流へ届き、下流から strategic_briefs を直接更新しない（s0-contract §1・SR-07）／learnings の採否（accepted/superseded）は上位ループ側の判断であり、生成側は draft までしか進めない
- **状態遷移**: テーブル列: learnings.status: draft→accepted（上位ループ取り込み）／draft→superseded（pair 失効・新版置換）。※ state_transitions ログの対象外（entity_type は loop_run/task のみ）の列更新であり、learnings 行が正本
- **正常動作**: レビュー成立イベント受領 → 成立 pair_kpi_measure と計測根拠から summary・learning_json を決定的に構成 → learnings に INSERT（status = draft、source_pair_id つき）→ 上位ループ次回転の入力キューへ積む。下位 run 終端時はこの learnings が tactical_learning_packet の構成要素として上流へ還流する。
- **拒否・異常動作**: pair 未成立（passed 行なし）・revoked のみ・sprint が reviewing 以外は PairNotEstablished を、learning_json の schema 違反は LearningSchemaViolation を raise し、learnings に行を作らず上位キューにも積まない（fail-close）。
- **境界動作**: 同一 pair からの再実行は既存 learnings を検出して重複生成しない。pair が成立後に revoked へ落ちた場合、生成済み learnings は superseded とし、当該 pair からの新規生成は拒否する。
- **再試行・再開・復旧**: 生成は単一 transaction の INSERT でクラッシュ時は行ごと消える。再実行は同一 source_pair_id の既存行検出で冪等に収束する。上位キューへの投入は learnings 行の存在を正本として再構成できる（申し送りなし）。
- **人間判断／escalation**: なし（生成は全自動。learnings の採否・戦略反映は上位ループ = strategy_revision 側の工程 — SR-10）
- **副作用**: learnings INSERT／learnings UPDATE（status = superseded — pair 失効時のみ）
- **冪等性**: 同一 source_pair_id の既存行検出により再実行は無副作用。summary・learning_json は同一入力→同一内容の決定的構成とする。
- **証跡**: learnings 行（source_pair_id つき — 還流の正本）／evidence: measurement（レビュー成立の根拠側 — FR-22 と共有）
- **使用テーブル・正本**: w: learnings／r: pair_kpi_measure（成立検査）／r: sprints（reviewing 検査）／r: measurements（根拠参照）／r: kpi_nodes（根拠参照）／r: loop_runs（上位ループ次回転の特定）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: learnings.status の enum（draft/accepted/superseded — DDL 正準）
- **trace**: 上流 = BR-A1 BR-I4 REQ-009 ／ 下流 = AC-15-1 AC-15-2 AC-15-3 FN-107 CMP-02 ／ スライス = S1

## FR-16 エスカレーション制御

- **入力**: 異常検知シグナル（ゲート赤・予算超過・地図破損・リトライ超過 — ゲート層/コネクタ/kernel が事由コード付きで発火）／対象 task／loop_run（tasks・loop_runs 行）／config.approval_retry_limit・config.retry_limit（境界値 — config 有効値）
- **出力**: escalated へ遷移した tasks 行（failure_code に事由コード記録）／安全停止: fatal_failure で escalated へ遷移した親 loop_runs 行（該当ループの保留）／通知送出（FR-46 経路 — ApprovalTransport、初期 Discord）／誤分類・不正遷移時: TransitionRejected 例外
- **事前条件**: 対象 task／loop_run が非終端状態で存在する／異常が事由コードへ分類済みである（分類は検出した層の責務 — §3.2）／遷移表（escalate／fatal_failure／retry_exhausted の行）がロード済み
- **事後条件**: 人の関与が必要な異常の task は escalated、該当 loop_run は fatal_failure で escalated（安全停止）に遷移している／tasks.failure_code に事由コードが記録されている／通知が FR-46 経路へ 1 件送出されている（transport 失敗でも状態遷移は成立し、通知のみ再送する）
- **不変条件**: escalate は常に escalated、non_retryable_failure は常に failed（同一 (現状態, イベント) から複数の次状態は存在しない — §3.2）／承認 decision = rejected は escalate に含めない（non_retryable_failure → failed が正準）／escalated は終端であり、人が新しい run/task を明示発行するまで遷移しない
- **状態遷移**: tasks: pending/in_progress/verifying → escalated（escalate — 人の関与が必要な異常）／tasks: verifying → escalated（verify_fail_exhausted — リトライ超過。FR-13 と共有）／loop_runs: pending/running/waiting → escalated（fatal_failure — 認証失効・ゲート赤・地図破損・予算超過等）／loop_runs: running/waiting → escalated（retry_exhausted — retry_count >= config.retry_limit）
- **正常動作**: 検出層（ゲート・コネクタ・kernel）が異常を事由コードへ分類 → 人の関与が必要なら該当 task へ escalate を発火して failure_code を記録 → 親 loop_run へ fatal_failure を発火して安全停止（保留）→ FR-46 経路で通知を送出。各遷移は state_transitions 証跡つきの単一 transaction。
- **拒否・異常動作**: 終端状態への escalate、事由コード未分類の異常、承認 rejected の escalate への誤投入は TransitionRejected を raise し状態を変更しない（rejected は non_retryable_failure で failed へ倒すのが正準）。拒否は state_transitions に guard_result = rejected で記録する。
- **境界動作**: 承認 expired は即 escalate せず承認再要求で待機継続し、config.approval_retry_limit 到達で escalated（§4.2 ステップ 3）。retry_exhausted は retry_count >= config.retry_limit ちょうどで発火。通知 transport の一時失敗は遷移を巻き戻さず通知のみ再送する。
- **再試行・再開・復旧**: 遷移は transaction 原子的でクラッシュ時に中間状態が残らない。再起動後、escalated は終端のまま保持され、未達通知は tasks/loop_runs の escalated 行と state_transitions を正本に再送出できる（推測による再開なし — §3.3）。
- **人間判断／escalation**: escalated 到達後の対処（credential 再投入・設計判断・地図修復の承認等）は人間（BR-H3）。検知・分類・遷移・通知は全自動
- **副作用**: tasks UPDATE（state・failure_code）／loop_runs UPDATE（state）／state_transitions INSERT／通知送出（FR-46 経路 — 外部 transport。テストでは mock）
- **冪等性**: 同一異常の再発火は現状態不一致（escalated = 終端）で拒否され二重遷移しない。通知は task/run 単位で重複を抑止し、再送は同一内容に収束する。
- **証跡**: state_transitions 行（escalate／fatal_failure／retry_exhausted の遷移と rejected 記録）／tasks.failure_code・failure_detail（事由コードと詳細）／approvals 行（expired 再要求の系列 — 境界の証跡）
- **使用テーブル・正本**: rw: tasks／rw: loop_runs／w: state_transitions／r: config（approval_retry_limit・retry_limit）／r: approvals（expired／rejected の分類入力）／r: playbooks（地図破損の検出源）／r: spend_ledger（予算超過の検出源）
- **外部依存**: 通知 transport（ApprovalTransport — FR-46 経路、初期 Discord。テストでは mock で approve/reject/timeout を再現）
- **設定値**: config.approval_retry_limit（expired 時の承認再要求上限）／config.retry_limit（retry_exhausted 境界 — FR-13 と共有） ／ **固定値**: 異常種別カタログ（ゲート赤・予算超過・地図破損・リトライ超過 — failure_code 分類の正本）
- **trace**: 上流 = BR-H3 BR-F5 REQ-039 ／ 下流 = AC-16-1 AC-16-2 AC-16-3 AC-16-4 AC-16-5 AC-16-6 FN-110 CMP-01 ／ スライス = S0

## FR-21 企画↔品質ペア判定

- **入力**: ペア成立要求（plan_id・review_task_id・review_evidence_id — WF-WP-1 ステップ 5）／公開前検証要求（action plan ID＋成立ペア ID — 公開系コネクタ FR-4x 経由）／ペア失効イベント（企画変更・commit 変更の検知 — kernel）
- **出力**: 成立時: pair_plan_quality 行（status = passed）／公開許可判定（通過 or PairNotEstablished 例外）／失効時: 該当 pair の status = revoked への更新
- **事前条件**: 対象 action_plans 行が存在する／review_pass 証跡（evidence.kind = review_pass、result = PASS）が T-REVIEW の task に存在する／review_pass の commit_hash が制作物の commit_hash と一致している
- **事後条件**: 成立時のみ pair_plan_quality に passed 行が 1 件存在する／pair 不成立・revoked の plan に対する公開系外部書込みが 0 件である／企画又は commit の変更後、旧 pair は revoked になっている
- **不変条件**: 企画レコードと審査 PASS 証跡の両参照が揃わない限り pair は成立しない（片肺禁止 — BR-B1）／revoked な pair を根拠にした公開は存在しない／pair 判定に人間によるバイパス経路が存在しない
- **状態遷移**: tasks: T-PUB の pending→failed（公開前検証で pair 不成立 = non_retryable_failure）
- **正常動作**: review PASS 成立時に (plan_id, review_task_id, review_evidence_id) の三参照を検証し、review_pass の commit_hash が制作 hash と一致する場合のみ pair_plan_quality に passed 行を INSERT。公開系コネクタは呼出し時に成立ペア ID を要求し、status = passed の pair が実在する場合のみ WP API 呼出しへ進む（WF-WP-2 ステップ 1）。
- **拒否・異常動作**: ペア ID なし・pair 不在・status = revoked・review_pass 証跡欠落・commit_hash 不一致の公開呼出しは PairNotEstablished を raise し、WP API を一切呼ばず T-PUB を non_retryable_failure で failed に倒す。参照整合が判定不能な場合（FK 破損・evidence 不在）も拒否側へ倒す（fail-close）。
- **境界動作**: 企画又は commit を変更した時点で既存 pair を revoked とし、再審査まで公開不可。revoke と公開の競合は公開直前の同一 transaction 内再検証で拒否側が勝つ。同一 (plan_id, review_evidence_id) の重複成立は UNIQUE 制約で 1 行に抑止。
- **再試行・再開・復旧**: ペア判定は DB 状態のみで再評価可能（申し送りなし）。クラッシュ後は pair_plan_quality の現在行から再判定して続行。revoked 後の復旧は再審査 PASS → 新 pair 成立のみ。
- **人間判断／escalation**: なし（判定は全自動。審査 PASS 自体は FR-25/FR-27 の規律下で verifier agent が行う）
- **副作用**: pair_plan_quality INSERT（成立時）／pair_plan_quality の status UPDATE（revoked 化）／秘匿化済み構造化拒否ログ（公開拒否時）
- **冪等性**: 同一 (plan_id, review_evidence_id) の成立要求は UNIQUE 制約により 1 行のみ。公開前検証は pure（同一 DB 状態→同一判定）で再実行安全。
- **証跡**: pair_plan_quality 行（成立・失効の状態）／evidence.kind = review_pass／plan_record（成立根拠）／構造化ログの拒否行（ペア不成立の公開試行）
- **使用テーブル・正本**: rw: pair_plan_quality／r: action_plans／r: tasks（review_task 参照）／r: evidence（review_pass・plan_record）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: pair 成立条件 = 両参照実在＋review_pass PASS＋commit_hash 一致（s0-contract §4.1）
- **trace**: 上流 = BR-B1 REQ-008 ／ 下流 = AC-21-1 AC-21-2 AC-21-3 AC-21-4 AC-21-5 FN-201 FN-202 CMP-03 ／ スライス = S0

## FR-22 計画↔計測ペア判定

- **入力**: ペア登録要求（sprint_id・kpi_node_id・measurement_id）／レビュー成立判定要求（対象 sprint_id — スプリント制御 FR-14 経由）／KPI 目標（sprints.kpi_target_json／kpi_nodes.target_json）と計測スナップショット（measurements 行）
- **出力**: 成立時: pair_kpi_measure 行（status = passed）＋レビュー成立イベントの発火（learnings 生成 FR-15 の起点）／不成立時: ReviewNotEstablished 例外（レビュー・還流は発生しない）
- **事前条件**: 対象 sprint が存在し KPI 目標（kpi_target_json）が設定済み／measurement 行が evidence_id（取得証跡）への FK を持つ／kpi_node が当該 sprint の目標対象ノードである
- **事後条件**: 成立時のみ pair_kpi_measure に passed 行が存在する／不成立の sprint でレビュー成立イベント・learnings 生成・上位還流が 0 件である
- **不変条件**: KPI 目標と計測スナップショットの両参照が揃わない限りレビューは成立しない（片肺禁止 — BR-B2）／取得証跡（evidence）に FK 接続しない measurement をペアの根拠にしない／レビュー成立イベントは成立済みペアからのみ発火する
- **状態遷移**: テーブル列: sprints.status: reviewing→completed（レビュー成立イベントが駆動）
- **正常動作**: sprint のレビュー判定時に、KPI 目標が設定された各対象ノードについて (KPI 目標, 計測スナップショット) の両参照を検証し、揃ったノードのペアを pair_kpi_measure に passed で INSERT。全対象ノードのペア成立をもってレビュー成立イベントを発火し、learnings 生成（FR-15）と上位ループ還流の起点とする。
- **拒否・異常動作**: 計測スナップショット不在・KPI 目標未設定・measurement の evidence FK 不整合はいずれも ReviewNotEstablished として不成立に倒し、レビュー成立イベントを発火せず learnings も生成しない。判定不能（target_json 破損等）も不成立側へ倒す（fail-close）。
- **境界動作**: kpi_target_json が空 JSON・目標ノード 0 件の sprint は判定不能として不成立（fail-open で素通しにしない）。期間外の measurement（period が sprint 期間と重ならない）はスナップショットとして不採用。重複ペアは UNIQUE(sprint_id, kpi_node_id, measurement_id) で 1 行。
- **再試行・再開・復旧**: 判定は DB 状態のみで再評価可能。クラッシュ後は pair_kpi_measure の現在行から再判定。計測の後着（取り込み完了）後に再判定すれば成立し得る（不成立は恒久拒否ではなく待機）。
- **人間判断／escalation**: なし（全自動。レビュー成立後の learnings 内容の評価は上位ループの工程）
- **副作用**: pair_kpi_measure INSERT（成立時）／レビュー成立イベント発火（sprints 遷移・learnings 生成の起点）／operation_log は使用しない（外部操作なし）
- **冪等性**: 同一 (sprint, kpi_node, measurement) の登録は UNIQUE 制約で 1 行。レビュー成立イベントは sprint 状態遷移（reviewing→completed）が冪等キーとなり二重発火しない。
- **証跡**: pair_kpi_measure 行（成立状態）／measurements 行と evidence.kind = measurement（スナップショット根拠）／state_transitions 行（sprint レビュー遷移）
- **使用テーブル・正本**: rw: pair_kpi_measure／r: sprints（kpi_target_json）／r: kpi_nodes／r: measurements／r: evidence（取得証跡 FK）／w: learnings（成立イベント下流 — FR-15 経由）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: ペア成立条件 = KPI 目標実在＋期間整合スナップショット＋取得証跡 FK（s0-contract §2）
- **trace**: 上流 = BR-B2 REQ-009 ／ 下流 = AC-22-1 AC-22-2 AC-22-3 FN-203 CMP-03 ／ スライス = S1

## FR-23 ゼロ広告費ゲート

- **入力**: KPI ノード登録要求（kpi_node の型・名称）／ブラウザ遷移先 URL（str — コネクタ経由）
- **出力**: 登録拒否: PaidMetricRejected 例外／URL 遮断: UrlDenied 例外＋秘匿化済み構造化拒否ログ／許可時: 通過（副作用なし）
- **事前条件**: 有料指標型の定義リスト（固定値）がロード済み／URL 許可リスト（allow-list）が config に存在する
- **事後条件**: 有料指標は kpi_nodes に存在しない／課金ドメインへの外部呼出しが 0 件
- **不変条件**: deny-by-default（許可リストにない URL は常に拒否）／本ゲートに人間によるバイパス経路が存在しない
- **状態遷移**: なし
- **正常動作**: KPI 登録時は指標型を有料指標定義と照合し、非該当のみ登録を通す。ブラウザ遷移時は URL を許可リストと照合し、一致のみ通す。
- **拒否・異常動作**: 有料指標（CAC/ROAS/広告費 系の型）は PaidMetricRejected で登録拒否。許可リスト外 URL は UrlDenied で遷移拒否し秘匿化済み構造化拒否ログに記録。判定不能（リスト破損等）も拒否側へ倒す。
- **境界動作**: サブドメイン・リダイレクト先も最終 URL で判定。許可リスト空 = 全遮断（安全側）。
- **再試行・再開・復旧**: ゲートは無状態（判定のみ）。再実行は同一判定を返す。リスト更新後は次回判定から反映。
- **人間判断／escalation**: なし（PO でも解除不可の機械的制約 — BR-C1）
- **副作用**: 構造化ログ出力（拒否時のみ — FN-704）
- **冪等性**: 判定は pure（同一入力→同一判定）。拒否ログは操作単位で 1 行。
- **証跡**: 拒否の構造化ログ（FN-704。状態遷移拒否は state_transitions の拒否行）（URL・指標名・理由）
- **使用テーブル・正本**: r: config（URL 許可リスト）／r: kpi_nodes（重複検査）
- **外部依存**: なし
- **設定値**: config.url_allowlist（媒体別） ／ **固定値**: 有料指標型の定義リスト（CAC/ROAS/広告費/CPC/CPM）
- **trace**: 上流 = BR-C1 REQ-012 ／ 下流 = AC-23-1 AC-23-2 AC-23-3 AC-23-4 AC-23-5 FN-204 CMP-03 ／ スライス = S0

## FR-24 PR 表記ゲート

- **入力**: 公開前成果物（記事 HTML/ソース — git workspace、commit hash で特定）／アフィリエイト判定用 ASP ドメインリスト（config）／PR 表記ブロックの検証規則（固定値 — 必須文言・配置）
- **出力**: 通過判定（アフィリエイト非該当 or 表記検証合格）／拒否時: PrLabelMissing 例外＋秘匿化済み構造化拒否ログ（公開ゲート不通過）
- **事前条件**: 成果物が commit hash で固定済み（FR-54）／ASP ドメインリストが config に存在する／公開ゲート（FR-21 経路）の前段として本検証が配線されている
- **事後条件**: PR 表記ブロックなしのアフィリエイト成果物が公開ゲートを通過していない／拒否時、外部書込み（WP API 呼出し）が 0 件である
- **不変条件**: 表記検証に合格しないアフィリエイト成果物の公開は存在しない（ステマ規制遵守 — BR-C2）／判定不能な成果物はアフィリエイト該当として扱う（fail-close）／検証は commit 固定済み成果物に対して行い、検証後の内容差し替えは pair 失効（FR-21）で無効化される
- **状態遷移**: tasks: T-PUB の pending→failed（表記検証不合格 = non_retryable_failure）
- **正常動作**: 公開前検証時に成果物からリンクを抽出し、ASP ドメインリストと照合してアフィリエイト該当性を判定。該当時は PR 表記ブロック（必須文言・配置規則）の存在を検証し、合格した場合のみ公開ゲートへ通す。非該当の成果物は表記検証なしで通過する。
- **拒否・異常動作**: アフィリエイトリンクを含み表記ブロックがない・文言不備の成果物は PrLabelMissing を raise して公開ゲートを通さず、秘匿化済み構造化拒否ログに拒否理由（対象 URL・欠落規則）を記録して T-PUB を failed に倒す。リンク抽出不能・HTML パース不能はアフィリエイト該当扱いで拒否（fail-close）。
- **境界動作**: ASP ドメインリスト未設定（config 欠落）は判定不能として全公開を拒否（fail-close）。短縮 URL・リダイレクトは展開後の最終 URL で判定。リンク 0 件の成果物は非該当として通過。
- **再試行・再開・復旧**: ゲートは無状態（判定のみ）。再実行は同一 commit に対し同一判定を返す。表記追加後は再 commit → 再審査 → 新 pair 成立を経て再判定。
- **人間判断／escalation**: なし（機械検証。表記規則自体の改訂は要件改訂で行う）
- **副作用**: 構造化ログ出力（拒否時のみ — FN-704）
- **冪等性**: 判定は pure（同一 commit＋同一リスト→同一判定）。拒否ログは公開試行単位で 1 行。
- **証跡**: 拒否の構造化ログ（FN-704。状態遷移拒否は state_transitions の拒否行）（対象成果物 commit hash・検出リンク・欠落規則）／通過時は review_pass 証跡の checked_items に表記検証結果を含める
- **使用テーブル・正本**: r: config（ASP ドメインリスト）／r: assets（成果物参照）
- **外部依存**: なし
- **設定値**: config.affiliate_domainlist（ASP ドメインリスト — 媒体拡張時に追記） ／ **固定値**: PR 表記ブロックの検証規則（必須文言・配置 — 景表法ステマ規制準拠）
- **trace**: 上流 = BR-C2 REQ-013 NFR-9 ／ 下流 = AC-24-1 AC-24-2 AC-24-3 FN-205 CMP-03 ／ スライス = S1

## FR-25 倫理ゲート

- **入力**: 審査対象（成果物＋企画情報 — T-REVIEW の入力）／P5 チェック項目定義（固定値: 恐怖訴求・偽希少性・不安増幅・診断の押し付け）
- **出力**: PASS 時: review_pass 証跡（checked_items に P5 全項目の判定を含む）／FAIL 時: 差戻し理由つき verify_fail（EthicsViolation 分類）
- **事前条件**: 審査ワークフローの必須項目として P5 が定義済み（workflows.definition_json）／verifier が author と別 principal（FR-27）／審査対象が commit hash で固定済み
- **事後条件**: P5 該当の成果物に review_pass（PASS）証跡が存在しない／FAIL 時は差戻し理由が残り task が in_progress へ戻っている（上限到達時は escalated）
- **不変条件**: P5 チェックを実施しない審査 PASS は無効（checked_items に P5 全項目がない review_pass を証跡ストアが拒否）／境界事例（該当疑い）は FAIL 側へ倒す（fail-close）／P5 項目定義の縮小はコードからできない（変更は要件改訂）
- **状態遷移**: tasks: verifying→in_progress（verify_fail — P5 FAIL、retry_count +1）／tasks: verifying→escalated（verify_fail_exhausted — retry 上限到達）／tasks: verifying→done（verify_pass — P5 全項目クリア時のみ）
- **正常動作**: T-REVIEW 実行時に verifier が P5 チェック項目（恐怖訴求・偽希少性・不安増幅・診断の押し付け）を必須項目として全件評価し、全項目非該当の場合のみ review_pass 証跡（checked_items に判定を格納）を残して verify_pass する。
- **拒否・異常動作**: P5 いずれかに該当した場合は EthicsViolation として verify_fail（差戻し理由＋verifier 証跡必須）で in_progress へ戻し、review_pass は生成しない。該当性が判定不能な境界事例も FAIL 側へ倒す（fail-close）。checked_items に P5 全項目を含まない PASS 証跡は証跡ストアが INSERT を拒否する。
- **境界動作**: verify_fail の反復で retry_count + 1 >= config.retry_limit に達した場合は verify_fail_exhausted で escalated へ遷移し人間の裁定を待つ。差戻し理由のない verify_fail は遷移ガードで拒否。
- **再試行・再開・復旧**: 差戻し後は author が修正 → 再 commit → 再審査（同一 task の retry）。escalated 後の再開は人間の裁定に基づく新 task/run の明示発行のみ。クラッシュ時は verifying の再開規則（§3.3 — 既存 PASS/FAIL 証跡があれば同一結果を採用）に従う。
- **人間判断／escalation**: 実在: retry 上限到達で escalated となった境界事例の裁定は人間（PO）が行う（BR-H3 経由）。自動判定側にバイパス経路はなく、裁定結果は新 run/task の明示発行として反映する。
- **副作用**: evidence INSERT（review_pass — PASS 時／verifier の FAIL 理由証跡）／tasks UPDATE（verify_fail での差戻し・retry_count 増加）／state_transitions INSERT（遷移ごと）
- **冪等性**: 同一 commit への再審査は同一判定を返す（決定的ルールセット — S0 は fail-close のルールベース）。PASS/FAIL 証跡は UNIQUE(task_id, kind, value) で重複しない。
- **証跡**: evidence.kind = review_pass（checked_items に P5 全項目の判定）／verifier の FAIL 理由証跡（差戻しごと）／state_transitions 行（verify_fail／verify_fail_exhausted）
- **使用テーブル・正本**: r: workflows（審査項目定義）／rw: tasks（T-REVIEW）／w: evidence（review_pass）／w: state_transitions
- **外部依存**: なし
- **設定値**: config.retry_limit（差戻し上限 — FR-13 と共通） ／ **固定値**: P5 チェック項目定義（恐怖訴求・偽希少性・不安増幅・診断の押し付け — 変更は要件改訂）
- **trace**: 上流 = BR-C3 REQ-014 ／ 下流 = AC-25-1 AC-25-2 AC-25-3 FN-206 CMP-03 ／ スライス = S1

## FR-26 金銭 escalation

- **入力**: タスクの操作型（task_type — 金銭操作型判定の対象）／束縛承認要求（binding_subject・binding_operation・binding_at — FR-46 経路）／承認応答（approvals.decision — 許可済み ApprovalTransport）
- **出力**: 承認要求: approvals 行（decision = pending）＋アプリ通知／approved 時: evidence.kind = approval ＋外部操作の実行許可／rejected/expired 時: 失敗分類イベント（non_retryable_failure／escalate）
- **事前条件**: 金銭操作型の定義リスト（価格変更・返金・決済設定）がロード済み／承認チャネル（初期 channel = discord）が構成済み（FR-46）／対象 task が in_progress で外部書込み前である
- **事後条件**: 金銭操作型 task の外部書込みは approved な approval（binding 3 項目完全一致）を持つ場合のみ実行されている／rejected の task は failed、approval_retry_limit 到達の task は escalated になっている
- **不変条件**: オートモード状態（config.auto_mode_criteria の充足）に関わらず金銭操作型は束縛承認を要する（バイパス不可 — BR-C4）／binding subject/operation/at の 3 項目が完全一致しない応答は承認として無効／承認なしの金銭系外部書込みが operation_log 上に 0 件
- **状態遷移**: tasks: in_progress→failed（non_retryable_failure — 承認 decision = rejected）／tasks: in_progress→escalated（escalate — expired が config.approval_retry_limit 到達）／テーブル列: approvals.decision: pending / approved / rejected / expired
- **正常動作**: task の操作型を金銭操作型定義と照合し、該当時はオートモード判定より先に束縛承認を要求: approvals へ pending 行を INSERT しアプリ通知（対象・操作・時点を明記）→ ループを waiting 化 → decision = approved かつ binding 3 項目完全一致を確認 → evidence.kind = approval を記録してから外部操作（prepared→sent→confirmed）へ進む。
- **拒否・異常動作**: approved な approval なしの金銭系外部書込み要求は ApprovalRequired で拒否し WP/決済系 API を呼ばない。decision = rejected は non_retryable_failure イベントで task を failed に倒す（代替 task の発行は可）。操作型が金銭該当か判定不能な場合は金銭型として扱い承認を要求する（fail-close）。
- **境界動作**: decision = expired は承認の再要求を発行して待機を継続し、再要求回数が config.approval_retry_limit に到達したら escalate イベントで escalated へ倒す。binding 3 項目のいずれかが不一致の応答は無効として待機継続。pending のままの場合は waiting を維持する。
- **再試行・再開・復旧**: クラッシュ後は approvals の現在行を再照合し、approved（binding 完全一致）なら実行再開、pending なら待機継続、expired なら再要求カウントから継続（§3.3 waiting 再開規則）。外部操作は idempotency key と external_operations 照合で二重実行を防ぐ。
- **人間判断／escalation**: 実在: 承認者（利用者）が許可済み承認入口で approve/reject を決定する。オートモード移行後もこの判断は機械化されない（BR-C4 の escalation 境界）。escalated 後の対処も人間（BR-H3）。
- **副作用**: approvals INSERT（要求・再要求ごと）／アプリ通知送信（FR-46 経路）／evidence INSERT（kind = approval — approved 時）／state_transitions INSERT（waiting 化・failed/escalated 遷移）
- **冪等性**: 同一 (task, binding_subject, binding_operation, binding_at) の承認要求は UNIQUE 制約で 1 行。approved の再確認は pure。外部操作は専用 idempotency key で二重送信しない。
- **証跡**: approvals 行（要求・応答の全履歴）／evidence.kind = approval（decision = approved、binding 3 項目）／秘匿化済み構造化拒否ログ（承認なし実行）
- **使用テーブル・正本**: rw: approvals／r: tasks（操作型判定）／r: config（auto_mode_criteria・approval_retry_limit）／w: evidence（approval）／w: state_transitions／r: external_operations（再開照合）
- **外部依存**: ApprovalTransport（初期 Discord、将来 Web UI / PWA — テストでは mock 可）
- **設定値**: config.approval_retry_limit（expired 再要求の上限）／config.auto_mode_criteria（オートモード判定 — 本 FR はこれに優先する） ／ **固定値**: 金銭操作型の定義リスト（価格変更・返金・決済設定に類する操作型）
- **trace**: 上流 = BR-C4 REQ-015 ／ 下流 = AC-26-1 AC-26-2 AC-26-3 FN-207 CMP-03 CMP-11 ／ スライス = S1

## FR-27 自己審査禁止

- **入力**: タスク割当要求（author_agent_id・verifier_agent_id — タスク発行 FR-12）／claim 要求（execution → task — kernel）／agents / agent_executions の principal 情報
- **出力**: 有効な割当: tasks 行（author != verifier、principal 相違）／拒否時: DB 層 IntegrityError（CHECK 違反）又はエンジン層 SelfReviewRejected
- **事前条件**: tasks に CHECK (author_agent_id != verifier_agent_id) が適用済み（DDL — s0-contract §2）／agents.principal が全 agent に設定済み／agent_executions.principal が複合 FK (agent_id, principal) で agents と一致強制済み
- **事後条件**: author_agent_id == verifier_agent_id の tasks 行が存在しない／author と同一 principal の verifier による verify_pass が存在しない／verifier 側 execution による claim が成立していない
- **不変条件**: 自己審査の拒否は DB 制約とエンジンの二重で強制され、片方の欠落でも成立しない（BR-B4・P4）／判定単位は principal（agent 行の差だけでは相違と認めない — s0-contract §1）／verifier_agent_id は全タスクで NOT NULL（三値論理に委ねない）
- **状態遷移**: tasks: pending→in_progress（claim — ガードで principal 相違・execution の author 帰属を検査）／tasks: verifying→done（verify_pass — ガードで verifier の別 principal を再検査）
- **正常動作**: タスク発行時に author と verifier を別 agent かつ別 principal で割り当てて tasks を INSERT（T-REVIEW の verifier は critic 以外の gate-engine 等）。claim 時は kernel ガードが execution の author agent 帰属と principal 相違を検査し、verify_pass 時も verifier の別 principal を再検査してから done へ遷移する。
- **拒否・異常動作**: author_agent_id == verifier_agent_id の INSERT/UPDATE は DB の CHECK 制約が IntegrityError で拒否。別 agent 行でも principal が同一の割当・verify はエンジン（kernel の claim／verify_pass ガード）が SelfReviewRejected で拒否し state_transitions に guard_result = rejected を記録。principal が照合不能（agents 不整合等）な場合も拒否側へ倒す（fail-close）。二重拒否のため、エンジンを迂回した直接 DML も DB 層で止まる。
- **境界動作**: lease 失効後の再 claim も author agent に属する execution のみ許可（verifier や第三 agent の execution による claim はガードで拒否）。agent の disabled 化後は claim ガードの active 検査で拒否。同時 claim は row_version の楽観ロックで 1 件のみ成立。
- **再試行・再開・復旧**: 制約・ガードは無状態で、クラッシュ後も DB の CHECK と kernel ガードがそのまま有効。再開時の再 claim も同一ガードを通る（§3.3 — プロセス内メモリの lease を再開根拠にしない）。
- **人間判断／escalation**: なし（PO でも解除不可の機械的制約。escalated 後の再割当判断は人間だが、その割当も本制約下に置かれる）
- **副作用**: state_transitions INSERT（claim/verify の guard_result = rejected 行）／DB 層拒否は副作用なし（transaction rollback）
- **冪等性**: 判定は pure（同一割当→同一判定）。拒否は DB 状態を変更せず、再試行しても同一結果。
- **証跡**: state_transitions 行（guard_result = rejected の claim/verify 拒否）／tasks 行そのもの（author/verifier の割当証跡）／agent_executions 行（実行系譜と principal）
- **使用テーブル・正本**: rw: tasks（CHECK 制約・lease 列）／r: agents（principal・status）／r: agent_executions（execution の帰属照合）／w: state_transitions（拒否記録）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: CHECK (author_agent_id != verifier_agent_id)（DDL 固定 — 変更は migration＋要件改訂）／principal 相違の判定規則（s0-contract §1）
- **trace**: 上流 = BR-B4 REQ-011 ／ 下流 = AC-27-1 AC-27-2 AC-27-3 AC-27-4 AC-27-5 FN-105 CMP-02 CMP-05 ／ スライス = S0

## FR-28 証跡完備検証

- **入力**: done 遷移要求（verify_pass イベント — 対象 task_id）／workflows.required_evidence_json（タスク種別ごとの必須 kind 集合）／evidence テーブルの当該 task 行（kind・payload_json）
- **出力**: 完備時: done 遷移の通過（tasks.state = done）／欠落時: EvidenceIncomplete 例外＋遷移拒否（state_transitions に rejected 記録）
- **事前条件**: task が verifying 状態である／task の workflow に required_evidence_json が宣言済み（S0 基準: T-PLAN = plan_record、T-PROD = commit_hash、T-REVIEW = review_pass、T-PUB = published_url・screenshot・approval、T-MEAS = measurement・file_hash・screenshot）／evidence は append-only トリガで保護済み
- **事後条件**: done な task は required_evidence_json の全 kind の evidence 行を持つ／kind 固有規則（§2.1 — payload 必須キー・列対応）を満たさない証跡を根拠に done になっていない
- **不変条件**: 宣言のみの完了は構造的に不可能（証跡の DB 収束が完了の必要条件 — BR-B3）／証跡の検証は INSERT 時（証跡ストア FN-703）と done 遷移時の二重で行う／done 遷移の拒否は task の状態・retry_count・証跡を変更しない
- **状態遷移**: tasks: verifying→done（verify_pass — 必須証跡完備がガード条件）／tasks: verifying→done の拒否（ガード不成立 = 遷移せず rejected 記録）
- **正常動作**: verify_pass 処理時に task の workflow の required_evidence_json を読み、宣言された全 kind について当該 task_id の evidence 行の存在を確認し、各 kind の固有規則（payload_json 必須キー・列対応・hash 桁数等 — s0-contract §2.1）を再検証してから、同一 transaction で done へ遷移し state_transitions に passed を記録する。
- **拒否・異常動作**: 必須 kind の欠落・kind 規則違反（payload 必須キー欠落・result != PASS・hash 不正等）は EvidenceIncomplete として done 遷移を拒否し、state_transitions に guard_result = rejected を記録して task は verifying のまま留める。required_evidence_json が読解不能・kind が未定義の場合も判定不能として拒否する（fail-close）。
- **境界動作**: required_evidence_json に evidence.kind の enum 外の値を含む workflow は判定不能として done を常に拒否（宣言の誤りを素通しにしない）。同一 kind の重複証跡は UNIQUE(task_id, kind, value) の範囲で許容し、最低 1 件の適合で充足。空配列宣言は「必須なし」として通過（ただし S0 の全 task type は非空を seed）。
- **再試行・再開・復旧**: 検証は DB 状態のみで再評価可能。欠落分の証跡を追記（append-only INSERT）後に verify_pass を再要求すれば通過する。クラッシュ後は verifying の再開規則（§3.3）に従い既存証跡を再検証する。
- **人間判断／escalation**: なし（全自動の機械検証。証跡が揃えられない task の扱いは §3 の失敗分類で escalated/failed へ）
- **副作用**: tasks UPDATE（done 遷移 — 完備時のみ）／state_transitions INSERT（passed/rejected）
- **冪等性**: 検証は pure（同一 evidence 集合→同一判定）。done 遷移自体は状態機械の冪等キー（verifying 以外からの verify_pass は拒否）で二重完了しない。
- **証跡**: evidence 行（kind ごとの完備集合そのもの）／state_transitions 行（done 遷移の passed／拒否の rejected）
- **使用テーブル・正本**: r: workflows（required_evidence_json）／r: evidence（当該 task の kind 集合）／rw: tasks（done 遷移）／w: state_transitions
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: evidence kind の enum と kind 固有規則（s0-contract §2.1 — rename 禁止）／S0 のタスク種別ごとの必須 kind 集合（§2.1 末尾）
- **trace**: 上流 = BR-B3 REQ-010 REQ-052 ／ 下流 = AC-28-1 AC-28-2 AC-28-3 AC-28-4 AC-28-5 AC-28-6 FN-208 CMP-03 CMP-04 ／ スライス = S0

## FR-31 ヒアリングエンジン

- **入力**: §4 スキーマの必須スロット定義（fill=H — JSON 正本）／対象 business_profile の現充填状態（business_profiles.profile_json）／人間回答（構造化回答 UI/API 経由 — 構造化値）／依存タスクの開始前提判定要求（task_id）
- **出力**: 未充足スロットごとの質問リスト（構造化問診）／型検証済み充填値で更新された business_profiles 行／拒否時: SlotUnfilledRejected（依存タスク開始）／AnswerTypeInvalid（型不一致回答）
- **事前条件**: §4 スキーマ（必須スロット・型定義）がロード済み／対象 business_profiles 行が存在する／DB マイグレーション適用済み（DU-11 verify() green）
- **事後条件**: 充填された値はすべて型検証 PASS 済みの人間回答由来である／未充足スロットが残る限り依存タスクは pending のまま／問診・回答・型検証結果の紐付け証跡が残っている
- **不変条件**: 未充足スロットを推測値で充填する経路がコード上に存在しない（値の出所は人間回答のみ — BR-D1 禁止事項）／型検証を通らない値は profile_json に一切書き込まれない／充填状態の判定は business_profiles の正本のみを根拠とする
- **状態遷移**: tasks: pending → pending（依存タスクの開始イベントは前提スロット未充足のガード不成立で拒否 — 遷移せず）
- **正常動作**: 必須スロットの空きをスキーマと profile_json の突合で検出 → 未充足スロットごとに質問リストを生成 → 構造化回答 UI/API で人に照会 → 回答を型検証し、PASS した値のみ profile_json へ充填して証跡を残す。Claude Code は任意クライアントに限り、全スロット充足後に依存タスクの開始前提判定が通る。
- **拒否・異常動作**: 未充足スロットに依存するタスクの開始要求は SlotUnfilledRejected を raise し、タスク状態を変更せず拒否理由（未充足スロット名）を構造化ログに残す。型検証 NG の回答は AnswerTypeInvalid として充填せず、同一スロットを再照会する。エンジンによる推測充填要求は常に拒否（fail-close）。
- **境界動作**: 全スロット充足時は質問リストが空（照会 0 件で正常終了）。回答が部分的な場合は充足分のみ充填し残りは未充足のまま維持。同一スロットへの再回答は新値で更新し、旧値は証跡に残る。
- **再試行・再開・復旧**: 問診途中のクラッシュでも充填済みスロットは DB に確定済み。再開時は空き検出を再実行し、残りの未充足スロットのみ再照会する（申し送りなし）。
- **人間判断／escalation**: あり（問診への回答 = 事業前提の確定は常に人間 — BR-D1。回答以外の判断はなし）
- **副作用**: business_profiles UPDATE（profile_json の充填）／evidence INSERT（問診・回答・型検証結果）／構造化ログ（FN-704 — 開始拒否・型検証 NG）
- **冪等性**: 空き検出が冪等キー: 充填済みスロットは再照会されない。同一回答の再送は同値上書きで DB 差分を生まない。
- **証跡**: 問診レコードと回答の紐付け行（evidence）／回答の型検証結果ログ／未充足時の開始拒否ログ（構造化ログ）
- **使用テーブル・正本**: rw: business_profiles／w: evidence／r: tasks（依存タスクの開始前提判定）
- **外部依存**: 構造化回答 UI/API（人間への正規照会契約。Discord／将来 Web UI／任意クライアントから利用可能）
- **設定値**: なし ／ **固定値**: §4 スキーマの必須スロット定義（fill=H 指定 — 変更は要件改訂）
- **trace**: 上流 = BR-D1 REQ-016 REQ-037 ／ 下流 = AC-31-1 AC-31-2 AC-31-3 FN-301 FN-302 CMP-06 ／ スライス = S1

## FR-32 リサーチエンジン（幻覚抑止）

- **入力**: リサーチ充填（fill=R）指定スロットの充填要求（スロット名・型）／Web 検索結果（値・出典 URL・取得日時の組）
- **出力**: 出典 URL 付き draft（KPI 初期形・媒体標準指標・運用詳細）／拒否時: UnsourcedValueRejected（出典なし値）／StaleSourceRejected（鮮度切れ出典）
- **事前条件**: fill=R スロットの型定義がロード済み／Web 検索経路（接続レジストリ準拠）が利用可能／config.source_freshness_days が config に存在する
- **事後条件**: draft の全値が出典 URL へ trace できる／出典なしの値が draft に 1 件も存在しない／媒体構造調査には structure_checked 日付が付与されている
- **不変条件**: 出典 URL のない値は draft に書けない（記憶ベースの媒体仕様記述の禁止 — BR-D2）／draft は draft のまま正本にならない（正本昇格は人間承認経由）／検索取得は読み取り専用で外部書込みを行わない
- **状態遷移**: なし
- **正常動作**: fill=R スロットの充填要求 → Web 検索要求を external_operations(effect='read', correlation_key='read:<task_id>:<request_hash>:<request_sequence>') の prepared→sent→confirmed で記録し、external_operation_row_idと同じrequest_sequenceを持つ対応operation_logを派生 → 候補値を取得 → 各値に出典 URL・取得日時を紐付けて型検証 → 出典・鮮度検証を通過した値のみで draft を起草し、出典 URL 列と structure_checked 日付を含めて保存する。
- **拒否・異常動作**: 出典 URL を欠く値の draft 書込みは UnsourcedValueRejected を raise し、その値を破棄して拒否理由を構造化ログに残す。鮮度上限（config.source_freshness_days）超過の出典は StaleSourceRejected で drop（G-SRC-FRESH）。出典検証不能（URL 解決失敗等）も拒否側へ倒す（fail-close）。
- **境界動作**: 検索結果 0 件のスロットは draft に含めず未充足のまま残す（空 draft を正本化しない）。鮮度がちょうど上限日数の出典は有効（超過のみ拒否）。同一スロットへの複数出典は全出典を保持する。
- **再試行・再開・復旧**: 起草途中のクラッシュは draft 未確定のため再実行で最初から起草し直す（検索は再取得 — 出典日時は新しくなる）。同一task・operation・request_hashの再取得はrequest_sequenceを単調増加させて別external_operations行にし、保存済みdraftは残して新draftとして区別する。
- **人間判断／escalation**: あり（draft の採否 — リサーチ値の正本昇格は人間承認を経る。起草自体は全自動）
- **副作用**: draft の保存（出典 URL 列つき）／external_operations INSERT/UPDATE（Web 取得 1 要求 = effect='read' 1 行。同一request_hashの再取得はrequest_sequenceを増分）＋対応する operation_log INSERT（同じrequest_sequence必須）／構造化ログ（出典なし値・鮮度切れの拒否）
- **冪等性**: 同一スロット・同一出典 URL・同一値の再起草は draft 内で重複せず 1 件に正規化される。検索の再実行自体は安全（読み取り専用）。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: draft の出典 URL 列／structure_checked 日付／出典なし値の拒否ログ（構造化ログ）／operation_log 証跡（Web取得。external_operation_row_idでexternal_operations.idへ束縛し、payloadのrequest_sequenceが一致。provider external_operation_idは任意）
- **使用テーブル・正本**: r: config（source_freshness_days）／rw: external_operations（Web 取得要求）／w: evidence（external_operations に対応する取得証跡）／r: kpi_nodes（KPI 初期形の突合先）
- **外部依存**: Web 検索（接続レジストリ経由の読み取り専用経路）
- **設定値**: config.source_freshness_days（媒体構造調査の鮮度上限 — 暫定既定値 90 日） ／ **固定値**: fill=R スロットの定義（§4 — 変更は要件改訂）
- **trace**: 上流 = BR-D2 REQ-017 ／ 下流 = AC-32-1 AC-32-2 AC-32-3 FN-303 FN-304 CMP-06 ／ スライス = S1

## FR-33 設定管理（config 履歴保持）

- **入力**: 設定変更要求（key, value_json, value_type, reason, changed_by_agent_id）／設定参照要求（key — str）
- **出力**: 新 config 行（INSERT — supersedes_config_id で直前有効行を参照）／有効値（key ごとに changed_at 最大の行）／拒否時: ConfigAppendOnlyViolation／ConfigReasonMissing 例外
- **事前条件**: config テーブルと append-only 保護トリガが生成済み（DU-11 verify() green）／安全側既定値が初期 migration で seed 済み
- **事後条件**: 変更は新行 INSERT のみで反映され、旧行は不変のまま残っている／新行の reason が非空で記録されている／supersedes_config_id が直前の有効行を指している
- **不変条件**: config は append-only（UPDATE/DELETE は保護トリガが常時 ABORT — 変更は INSERT の履歴保持のみ）／reason 必須（reason のない変更行は存在しない）／既定値は保守的（安全側）に設定され、危険側変更も履歴として必ず残る／同一 key・同一 changed_at の行は存在しない（UNIQUE）
- **状態遷移**: なし
- **正常動作**: 変更要求を受領 → reason 非空・value_type と value_json の整合を検証 → 直前の有効行を解決して supersedes_config_id に設定し、新行を INSERT する。参照は key ごとに changed_at 最大の行を有効値として返す。
- **拒否・異常動作**: config への UPDATE/DELETE は保護トリガが RAISE(ABORT) で常時拒否（ConfigAppendOnlyViolation）。reason が空・欠落の変更要求は ConfigReasonMissing で INSERT 前に拒否。同一 key・同一 changed_at の INSERT は UNIQUE 制約で拒否。value_type 外の型は CHECK 制約で拒否（fail-close）。
- **境界動作**: 参照 key が config に不在の場合は安全側既定値表から保守的値を返し、既定値もなければ拒否側へ倒す（fail-open な暗黙値を返さない）。同一 key への同時変更は UNIQUE (key, changed_at) の直列化で片方のみ成立。
- **再試行・再開・復旧**: INSERT は単一 transaction のためクラッシュ時は中間状態が残らない。再実行は直前有効行を再解決して INSERT し直す。履歴チェーンは supersedes_config_id で常に復元可能。
- **人間判断／escalation**: あり（安全側数値の危険側変更 — 上限緩和等 — は人間承認を経る。参照・履歴解決は全自動）
- **副作用**: config INSERT（変更ごとに 1 行）／構造化ログ（拒否時 — append-only 違反・reason 欠落）
- **冪等性**: 同一 key・同一 changed_at の再送は UNIQUE 制約で重複せず拒否される。参照は pure（同一 DB 状態→同一有効値）。
- **証跡**: config の履歴行（旧行が不変のまま残る — それ自体が証跡）／変更 reason 列／構造化ログ（拒否行）
- **使用テーブル・正本**: rw: config（w は INSERT のみ — UPDATE/DELETE 不可）／r: agents（changed_by_agent_id の FK 先）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 安全側既定値の seed 表（spend_cap_monthly=5000 円/月・retry_limit 等 — 初期 migration で投入）／append-only 保護トリガ（config_no_update／config_no_delete）
- **trace**: 上流 = BR-D3 REQ-018 ／ 下流 = AC-33-1 AC-33-2 AC-33-3 AC-33-4 AC-33-5 AC-33-6 FN-305 CMP-06 ／ スライス = S0

## FR-34 事業非依存（business_profiles 分離）

- **入力**: 新プロファイル登録要求（profile_key, name, profile_json）／データアクセスのスコープ解決要求（business_profile_id — ストア層経由）
- **出力**: business_profiles 行（複数共存）／スコープ強制済みクエリ結果（要求 profile のデータのみ）／拒否時: CrossProfileAccessDenied／ProfileKeyConflict 例外
- **事前条件**: business_profiles と business_profile_id FK 付き業務テーブルが生成済み／アクセス要求に business_profile_id スコープが解決済みで渡る（ストア層一元化）
- **事後条件**: 登録後も既存プロファイルの行・参照データが不変である／クエリ結果に他プロファイルの行が 0 件である／越境アクセスの拒否が証跡に残っている
- **不変条件**: 事業固有値は business_profiles・config・充填スロットのみに存在する（コード・ワークフロー定義への焼き付け禁止 — BR-D4）／ブランド越境のデータ参照・書込みは構造的に不可能（BR-I1 — スコープ解決はストア層で一元化）／複数プロファイルの共存がスキーマとして常に許される（profile_key UNIQUE のみが識別制約）
- **状態遷移**: テーブル列: business_profiles.status: draft → active → archived（status CHECK — 別ブランド追加は型の再充填のみ）
- **正常動作**: 新プロファイルは profile_json の型検証後に business_profiles へ INSERT され、既存プロファイルと共存する。全データアクセスはストア層で business_profile_id スコープを強制され、要求プロファイルの行のみが返る・書かれる。
- **拒否・異常動作**: 他プロファイルに属する行への参照・書込み要求は CrossProfileAccessDenied を raise し、DB を変更せず拒否を証跡化する。profile_key 重複は UNIQUE 制約で ProfileKeyConflict。スコープ未指定のアクセスは deny-by-default で拒否（呼出側の自由 WHERE に依存しない）。
- **境界動作**: archived プロファイルは読取可・新規書込み不可。プロファイル 1 件のみでもスコープ強制は省略されない。削除は参照行がある限り FK ON DELETE RESTRICT で拒否。
- **再試行・再開・復旧**: 登録は単一 transaction でクラッシュ時に中間状態が残らない。再登録は profile_key の UNIQUE で重複検出。スコープ解決は無状態のため再実行安全。
- **人間判断／escalation**: あり（新事業プロファイルの充填内容の確定・追加/廃止の意思決定は人間。スコープ強制は全自動）
- **副作用**: business_profiles INSERT/UPDATE（status 遷移）／構造化ログ（越境拒否）
- **冪等性**: 同一 profile_key の再登録は UNIQUE で拒否（重複プロファイルは生まれない）。スコープ解決は pure（同一入力→同一スコープ）。
- **証跡**: business_profiles の複数行共存（SELECT で確認可能）／越境アクセスの拒否ログ（構造化ログ）／事業固有値のハードコード検出ゲート green
- **使用テーブル・正本**: rw: business_profiles／r: brand_plans・action_plans・kpi_nodes 等（business_profile_id FK スコープ列を持つ業務テーブル）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: business_profiles の status 遷移（draft/active/archived — DDL CHECK）
- **trace**: 上流 = BR-D4 BR-I1 REQ-019 REQ-046 ／ 下流 = AC-34-1 AC-34-2 AC-34-3 FN-306 CMP-05 CMP-06 ／ スライス = S1

## FR-41 接続レジストリ

- **入力**: 経路解決要求（service, operation — connectors 各層から）／レジストリ行（config `registry.<service>` の JSON 値 — 優先経路 MCP/ブラウザ/API・フォールバック経路・認証方式）／有償経路の例外宣言（config `registry.<service>.paid_exception` — 現状 Seedance のみ）
- **出力**: 解決済み経路（route_type: mcp/browser/api/wp_rest/wp_cli — 呼出元コネクタへ）／解決不能時: RouteNotRegistered / PaidRouteDenied 例外／秘匿化済み構造化ログ（拒否・フォールバック発動時）
- **事前条件**: config にレジストリ行が投入済み（tech-stack §5 の初期表が seed）／経路選定ロジックがレジストリ参照のみで動く（コード内に service→経路の分岐が存在しない）／有償経路の宣言には spend_ledger 記録経路（FR-73）が配線済み
- **事後条件**: 返却された経路はレジストリ行の宣言と一致している／有償 API 経路は例外宣言のあるサービスに限って返却されている／フォールバック発動・拒否は process logger の構造化ログに理由つきで残っている
- **不変条件**: 経路優先順は MCP → ブラウザ → 有償 API（明示例外のみ — BR-F1）で、レジストリ行の変更のみで切替可能／X のブラウザ書込み経路はレジストリに登録できない（BR-M-X-4 — 登録要求自体を拒否）／媒体追加はレジストリ行＋ワークフロー＋攻略地図の追加のみで完結し、外殻コードを変更しない（NFR-8）
- **状態遷移**: なし
- **正常動作**: 経路解決要求を受け、config のレジストリ行から (service) の優先経路を読み、認証方式を添えて経路を返す。第一経路が利用不能（コネクタからの失敗通知）ならフォールバック経路へ切替え、切替を process logger の秘匿化済み構造化ログに記録する。経路の追加・変更は config INSERT（履歴保持 — FR-33）のみで反映される。
- **拒否・異常動作**: 未登録 service は RouteNotRegistered を raise し秘匿化済み構造化拒否ログに記録。例外宣言のないサービスへの有償 API 経路解決は PaidRouteDenied で拒否。X への browser 書込み経路の登録・解決要求は ProhibitedMediaWrite で拒否（BR-M-X-4）。レジストリ行 JSON の破損・型不一致は解決不能として拒否側へ倒す（fail-close）。
- **境界動作**: フォールバック経路が未宣言で第一経路も不能な場合は経路なしとして呼出元タスクを escalated へ誘導（解決 API は RouteNotRegistered）。同一 service の複数レジストリ行は changed_at 最新の 1 行のみ有効。空レジストリ = 全 service 解決不能（安全側）。
- **再試行・再開・復旧**: 解決は無状態（config 読取のみ）で再実行は同一結果を返す。config 行更新後は次回解決から反映。クラッシュ後の再開に固有の中間状態はない。
- **人間判断／escalation**: なし（全自動。有償経路の例外宣言の追加自体は config 変更として人間 = PO 判断 — BR-F1）
- **副作用**: 秘匿化済み構造化ログ（拒否・フォールバック発動時）／なし（解決成功時は pure — 読取のみ）
- **冪等性**: 同一 (service, operation) の解決は同一 config 状態で同一経路を返す pure 判定。拒否ログは解決要求単位で 1 行。
- **証跡**: 秘匿化済み構造化ログ（拒否・フォールバック発動 — service・要求経路・理由）
- **使用テーブル・正本**: r: config（registry.* 行）／r: spend_ledger（有償経路の台帳配線検査）
- **外部依存**: なし
- **設定値**: config.registry.<service>（優先経路・フォールバック・認証方式の JSON）／config.registry.<service>.paid_exception（有償経路の明示例外宣言） ／ **固定値**: 経路優先順 MCP → ブラウザ → 有償 API（BR-F1 — 変更は要件改訂）／route_type 語彙（mcp/browser/api/wp_rest/wp_cli — playbooks DDL と共通）
- **trace**: 上流 = BR-F1 BR-F3 REQ-026 REQ-030 NFR-8 ／ 下流 = AC-41-1 AC-41-2 AC-41-3 AC-41-4 AC-41-5 AC-41-6 FN-401 FN-412 CMP-07 ／ スライス = S0

## FR-42 ブラウザ自動化基盤

- **入力**: ブラウザ操作要求（service・operation・対象 URL・payload — タスク実行層から）／攻略地図の現役版行（playbooks: version・procedure_json・selector_json・status — FR-43 と共有）／headed/headless 切替値（config.browser.headed — bool）／Rng/Clock（注入 — 操作間隔乱数と seed 記録用）
- **出力**: 操作結果（成功時: 取得値・スクショ参照 — 呼出元へ）／playbooks.last_success_at 更新（成功時）／実外部操作: external_operations行（effect・policy_category・rate_scope必須、prepared→sent）＋sent行をfinal化する対応operation_log証跡／拒否時: PlaybookMissing / RateLimitExceeded / ProhibitedMediaWrite / UrlDenied 例外
- **事前条件**: 対象 (service, operation, route_type=browser) の playbooks 行が status=active で存在する／URL 許可リスト（FR-23）が config に存在する／credential は暗号化ストアから実行時注入済み（FR-47 — SQLite/ログに平文なし）／書込み系は成立済みペアID・専用idempotency key・policy_categoryを保持し、(policy_category, service, operation, target_endpoint)がconfig.external_write_policyの明示行に一致する
- **事後条件**: 操作は playbooks の手順・セレクタどおりに実行され、成功時に last_success_at が更新されている／read/writeを問わず実外部操作はexternal_operations 1行（1操作=1行、effect/policy_category必須、writeのみcanonical rate_scope必須・readはNULL）をprepared→sentまで記録し、sent行への対応operation_log INSERTがtriggerでconfirmed/rejected/unknownへfinal化・evidence_id接続した後にだけ業務状態遷移している／書込み系の連続操作間隔は 1〜5 秒の一様乱数で、seed・生成値が構造化ログに記録されている（NFR-7）
- **不変条件**: X へのブラウザ書込みは常に拒否（BR-M-X-4 — バイパス経路なし）／書込み・公開系はcanonical lowercase rate_scope別のconfig.rate.<rate_scope>.daily_write_cap（必須）を超えず、service alias・大小文字差・shared serviceで別scopeへ逃がさない／操作間隔は固定値でなく範囲乱数（固定間隔は機械署名 — BR-F5）／許可リスト外URLへの遷移は発生しない（FR-23 deny-by-default）／content_publishはDocker WPだけ、review_syncは承認済みNotionだけ、approval_notificationはbinding済みの許可ApprovalTransportだけ、approved_paid_operationはPO承認済み有償操作だけ。readはexternal_read。その他は常時拒否
- **状態遷移**: テーブル列: external_operations.status: prepared→sent→confirmed/rejected/unknown（read/write の実外部操作ごと。external_operations.effect='read'/'write' — s0-contract §1）
- **正常動作**: 操作要求を受けplaybooksから手順を解決し、Playwrightをconfig.browser.headedに従い起動。実外部操作ごとにeffectを固定し、readはpolicy_category='external_read'・rate_scope=NULL・correlation_key='read:<task_id>:<request_hash>:<request_sequence>'、writeは閉集合content_publish/review_sync/approval_notification/approved_paid_operationのpolicy_category・canonical lowercase rate_scope・correlation_key=idempotency_keyを設定する。writeは(policy_category, service, operation, target_endpoint, rate_scope)のcategory別policyと必要なpair/approval/bindingをpreflight検証した後だけexternal_operationsをpreparedでコミットする。書込みだけRngで待機後送信しsentをコミットし、結果確定後も行がsentの間にoperation_logをINSERTしてtriggerでfinal化・evidence_id接続する。final化後にだけ業務状態遷移する。
- **拒否・異常動作**: playbooks行なし/status=broken、policy_category/rate_scope欠落・未知・非canonical、category偽装、categoryとservice/operation/endpoint/rate_scopeのpolicy不一致、必要pair/approval/binding欠落、日次上限超過、X又はnote等スコープ外媒体へのwrite、URL許可外はいずれもpreflightで拒否する。Notionをcontent_publishへ偽装、本番WP、unknown endpoint/serviceも同様。外部呼出・external_operations・operation_logは各0、process loggerへ事由コードだけを記録する（fail-close）。
- **境界動作**: 間隔乱数は範囲端1秒・5秒を含む一様分布。日次cap件目は許可しcap+1件目を拒否する（config.rate.<rate_scope>.daily_write_cap必須、Docker WPはrate_scope='wp'、UTC日境界はClock注入）。セレクタ不一致はFR-43へ渡し、セッション失効は送信前検知する。
- **再試行・再開・復旧**: 送信直後クラッシュはexternal_operations.statusで再開する。preparedは同一idempotency keyで再送可。sentのリモート照合自体を別external_operations(effect='read', policy_category='external_read', rate_scope=NULL)行＋operation_log（payloadにrate_scope:nullキー必須）として記録し、照合結果に基づく元writeのoperation_log INSERTでconfirmed又はunknownへfinal化する（再送しない — s0-contract §3.3）。乱数はログのseedから再現可能（NFR-2）。
- **人間判断／escalation**: なし（全自動。検知・警告兆候時の媒体停止判断は安全側自動調整＋escalated 経由で人間 — BR-F5）
- **副作用**: 外部サイトへのブラウザ操作（read/writeともexternal_operations経由のみ）／external_operations INSERT/UPDATE／operation_log INSERT（external_operations に対応する外部ブラウザ操作のみ）／秘匿化済み構造化拒否ログ（送信前拒否）／playbooks.last_success_at / consecutive_failures UPDATE／構造化ログ行（seed・生成間隔値）
- **冪等性**: 実外部操作は1要求=1 external_operations行。書込み系は操作単位のidempotency key（external_operations.idempotency_key UNIQUE）で二重実行を検出し、sent照合により再送しない。読取り系は同一(task_id, operation, request_hash)内の各poll/再取得にrequest_sequenceを1から単調増加させ、correlation_key='read:<task_id>:<request_hash>:<request_sequence>'で一意化するため、同一内容の反復readも別要求として追跡できる。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: operation_log行（external_operation_row_id・effect・policy_category・rate_scope・service・operation・correlation_key・request_hash・request_sequence・resultが外部行と同値。provider external_operation_idは任意）／screenshot evidence（操作確認）／構造化ログ（乱数 seed・間隔値 — NFR-7 再現用）
- **使用テーブル・正本**: rw: playbooks／rw: external_operations／w: evidence（外部操作証跡 = operation_log kind）／r: config（browser.headed・rate.*・url_allowlist）／w: evidence（screenshot）
- **外部依存**: Playwright（ブラウザ自動化）／対象媒体サイト（note/YouTube/stand.fm/KDP/ASP等はreadのみ。本FRでwriteが許可されるのは閉集合policyに根拠を持つDocker WP/Notion review sync/許可ApprovalTransport通知/PO承認済み有償操作だけ。X書込みは禁止）
- **設定値**: config.browser.headed（headed/headless 切替）／config.rate.wp.daily_write_cap（Docker WP content_publishの必須日次上限）／config.external_write_policy.<category>.allowed_services/endpoints（policy_category×service×operation×target_endpointの必須許可行。content_publishのDocker-onlyとapproved_paid_operationのPO承認は固定要件）／config.rate.write_interval_range（暫定既定 1〜5 秒一様） ／ **固定値**: 読取り系は乱数待機の対象外（NFR-7）／書込み間隔は一様分布（分布形は要件固定）
- **trace**: 上流 = BR-F2 BR-F5 BR-M-X-4 REQ-028 REQ-044 NFR-7 ／ 下流 = AC-42-1 AC-42-2 AC-42-3 FN-402 FN-403 FN-404 CMP-08 CMP-09 ／ スライス = S1

## FR-43 攻略地図の自己修復

- **入力**: 破損シグナル（セレクタ不一致・手順失敗 — FR-42 の失敗通知）／対象 playbooks 現役版行（id・version・procedure_json・selector_json・consecutive_failures）／起点 task と破損 fingerprint（決定的な repair task idempotency key の材料）／対象ページの現 DOM（読取り専用の再解析対象）
- **出力**: 成功時: 旧版を supersede する version+1 の playbooks 行（status=active）／失敗時: repair task と起点 task の escalated 遷移＋通知（FR-46 経路）／内部の検知・試行・結果を表す秘匿化済み構造化ログと、外部 DOM 読取りだけに対応する operation_log 行
- **事前条件**: 対象 playbooks 行が存在し status が active または broken である／破損シグナルが失敗の具体（不一致セレクタ・失敗ステップ）を含む／再解析はログイン済みセッションで読取りのみ可能／自動repair task発行にはconfig.playbook_repair_limit=1が必須（欠落・1以外は発行前にfail-close）
- **事後条件**: 同一破損イベントの playbook_repair task は決定的 idempotency_key により 1 行だけで、retry_count=0 のまま config.playbook_repair_limit=1 を超えない／成功時: 旧 broken 版が retired、新しい version+1 行が active・consecutive_failures=0 で INSERT され、created_by_task_id が repair task を指す／失敗時: 旧版は broken のまま新版 0 件で、repair task と起点 task が escalated となり通知済み
- **不変条件**: 再解析・再生成の過程で外部サイトへの書込みを行わない（読取りのみ）／自動修復の試行数は config.playbook_repair_limit（現行値 1）以下で、同一破損イベントの終端 repair task を再発行しない／破損中（status=broken）の地図を参照する書込み操作は開始されない
- **状態遷移**: テーブル列: playbooks.status: active→broken（破損検知）・broken→retired（修復成功時。新版 active 行を INSERT）／tasks: repair task は pending→in_progress→verifying→done（成功）、失敗時は repair task と起点 task が in_progress→escalated（event=escalate — BR-H3）
- **正常動作**: FR-42の失敗通知を受け、playbooksのactive→broken条件付き更新に勝った実行だけが同じtransaction内でconfig.playbook_repair_limitを検証する。値が正確に1の場合だけ、(playbook_id, 起点task_id, failure_fingerprint)をinput_jsonへ束縛したtask_type=playbook_repair子taskを決定的idempotency_key・attempt=1・retry_count=0でINSERTする。子taskは外部DOM読取りをexternal_operations(effect='read', request_sequence=1, correlation_key='read:<task_id>:<request_hash>:1')→external_operation_row_id・request_sequence一致のoperation_logに証跡化して候補地図を生成し、別principalの検証合格時に旧broken版をretired、新version+1版をactiveでINSERTしてdoneへ進む。内部の検知・候補生成・検証結果はprocess loggerへ記録する。
- **拒否・異常動作**: config.playbook_repair_limitが欠落又は1以外ならactive→brokenは保持するがrepair子taskを発行せず外部DOM readも行わず、起点taskだけをevent=escalateでescalatedへ遷移し新版をINSERTしない。値1で発行後の候補生成不能・検証不通過・対象要素不在は追加試行せず、旧版をbrokenのまま、新版0件としてrepair taskと起点taskをescalatedへ遷移しFR-46経路で通知する。ページ到達不能・認証失効も同様にfail-closeとする。
- **境界動作**: 同一現役版への並行破損通知は active→broken の条件付き更新に勝った 1 件だけが repair task を発行し、後続は同じ idempotency_key の非終端 task を参照して結果待ちする。status=retired は対象外で即 escalated。新版 active の再失敗は、別 playbook_id と別 failure_fingerprint に束縛された新しい破損イベントとしてのみ修復 task を 1 行発行できる。
- **再試行・再開・復旧**: 再生成中クラッシュ後は同じ非終端 playbook_repair task と external_operations 状態を再読込み、既存 task を再開する。プロセス再起動を新たな試行と数えず、終端の done/escalated task は同一破損イベントで再発行しない。escalated 後は元 task を終端のまま保持し、人が明示発行した新 task による新版登録だけを許す。
- **人間判断／escalation**: 再生成失敗時の対処（地図手動修正・媒体運用判断）は escalated 経由で人間（BR-H3）。それ以外は全自動
- **副作用**: playbooks UPDATE（旧版の status・失敗数）＋成功時の新版 INSERT／playbook_repair 子 task INSERT と状態遷移／external_operations(effect='read')／対応operation_log（外部DOM読取り1件だけ）／秘匿化済み構造化ログ（検知・試行・結果）／tasks の escalated 遷移（失敗時）／外部サイトへの読取りアクセス（書込みなし）
- **冪等性**: 破損イベントの正本は決定的 idempotency_key を持つ playbook_repair task 1 行であり、UNIQUE(idempotency_key) と attempt=1・retry_count=0 で二重試行を拒否する。新版は UNIQUE(service, operation, route_type, version) と UNIQUE(supersedes_playbook_id) で二重発行を拒否する。operation_log は外部 DOM 読取りの証跡であって修復試行数の正本にはしない。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: 秘匿化済み構造化ログ（破損検知: 不一致セレクタ・失敗ステップ）／playbook_repair task 行（破損イベント・試行上限・結果の永続正本）／旧版と supersedes_playbook_id で接続した新版 playbooks 行／operation_log 行（external_operation_row_id・correlation_key・request_hash・request_sequence=1つき外部DOM読取りのみ。provider external_operation_idは任意）／screenshot evidence（再解析時のページ状態）
- **使用テーブル・正本**: rw: playbooks（版行・現役状態）／rw: tasks（playbook_repair 子 task・escalated 遷移は状態機械 FR-11 経由）／rw: external_operations（外部 DOM 読取り）／w: evidence（外部 DOM 読取り証跡 = operation_log kind）／w: evidence（screenshot）
- **外部依存**: 対象媒体サイト（読取り専用の再解析）／Playwright（FR-42 基盤を利用）
- **設定値**: config.playbook_repair_limit（現行値 1。欠落は fail-close） ／ **固定値**: なし
- **trace**: 上流 = BR-F2 BR-H3 REQ-029 ／ 下流 = AC-43-1 AC-43-2 AC-43-3 FN-405 CMP-09 ／ スライス = S2

## FR-44 WP コネクタ

- **入力**: REST 書込み要求（投稿・メディア・下書き・公開 — WF-WP-2 から。成立済みペア ID・専用 idempotency key つき）／WP-CLI 構築要求（子テーマ・プラグイン配備・テーマ解析 — 構築タスクから）／接続先（接続レジストリ経由 — Application Password は暗号化ストアから実行時注入）
- **出力**: REST 成功時: WP draft ID / post ID / canonical URL / media ID（external_operations・evidence へ）／WP-CLI 成功時: 実行結果＋テーマ解析結果の playbooks 構造化保存（BR-G4）／拒否時: PairRequired / ProductionWriteDenied / ApprovalRequired 例外
- **事前条件**: 書込み系は pair_plan_quality に status=passed のペア行が存在する（FR-21 — 成立済みペア ID）／書込み先 endpoint がローカル Docker WP である（環境契約 §6 — 唯一の実 WP 書込み先）／公開操作は decision=approved の approvals 行（binding 3 項目一致）が存在する（FR-46）／操作ごとの専用idempotency keyを保持（下書き作成と公開は別key）／policy_category='content_publish'かつ(service='wp', operation, target_endpoint)がDocker WP固定policyに一致する
- **事後条件**: 外部書込み1件につきexternal_operations(effect='write', policy_category='content_publish', rate_scope='wp') 1行がprepared→sentまで遷移し、sent行への対応operation_log INSERT triggerでfinal化している／公開成功時published_url evidenceがoperation_log_evidence_idで先行operation_logへ束縛され、payloadのexternal_operation_row_idが同じlocal WP write行、provider IDは任意で、assets参照（canonical_url・wp_post_id）が登録されている／テーマ解析結果は playbooks（route_type=wp_cli）に構造化保存されている
- **不変条件**: 本番 WP・Docker 以外の WP への自動書込みは発生しない（設定検出時は実行拒否 — 環境契約 §6）／ペア ID なしの書込み呼出しは常に拒否（fail-close — requirements §1）／credential は SQLite/repo/ログ/evidence に平文で残らない（FR-47）／REST 書込みはバースト上限 30 req/分・公開 10 件/日以内（MR-WP-5 — config.rate.wp.*）
- **状態遷移**: テーブル列: external_operations.status: prepared→sent→confirmed/rejected/unknown（書込み操作ごと）／tasks: WF-WP-2 の in_progress→verifying 等は状態機械（FR-11）経由 — 本 FR は証跡化までを担う
- **正常動作**: 書込み要求のpair・endpoint・公開approvalと固定policyを検証し、external_operations(effect='write', policy_category='content_publish', rate_scope='wp', service='wp', operation, target_endpoint=Docker WP)をpreparedでコミット→REST送信→sentコミット→operation_log INSERT triggerでfinal化する。provider IDは任意。公開時はcanonical URLをassetsへ登録後、published_urlをoperation_log_evidence_id＋payload external_operation_row_idで先行operation_logへ束縛する。
- **拒否・異常動作**: pairなし、policy_category欠落/不一致、service/operation/endpoint policy欠落、Docker以外のWP、公開approvalなし/binding不一致はpreflight拒否し、外部送信・external_operations・operation_log各0でprocess loggerへ事由コードを記録。送信後WPエラーだけはsent行へoperation_logをINSERTしrejected化する。
- **境界動作**: レート上限（30 req/分）到達時はバースト待機し上限を超えない。下書きと公開は別 idempotency key の別 external_operations 行（1 操作 = 1 行）。同一 idempotency key の再要求は UNIQUE 制約で既存行に照合され二重送信しない。
- **再試行・再開・復旧**: sentのままクラッシュした最危険kill pointは、WP側照合自体を別external_operations(effect='read', policy_category='external_read', rate_scope=NULL)行＋operation_log（payload rate_scope:null）として記録する。成功確認後に元writeのoperation_log INSERTでconfirmed化し、照合不能は元writeをunknown化して再送せずescalateする（s0-contract §3.3・§8）。preparedは同一keyで再送可。
- **人間判断／escalation**: 公開の束縛承認（FR-46 経由）。unknown 照合不能時の対処は escalated 経由で人間。それ以外は全自動
- **副作用**: Docker WP への REST 書込み（投稿・メディア・公開）／WP-CLI 実行（構築系）／external_operations INSERT/UPDATE／operation_log / published_url evidence INSERT／assets INSERT（canonical_url・wp_media_id）／playbooks INSERT/UPDATE（テーマ解析）
- **冪等性**: 操作単位の idempotency key（external_operations.idempotency_key UNIQUE）で二重実行を検出（BR-I7）。下書きと公開は別 key。sent 照合により再送は発生しない。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: operation_log行（service=wp・external_operation_row_id・policy_category・rate_scope・correlation_key・request_hash・request_sequence。provider external_operation_idは任意）／published_url evidence（url・wp_post_id・asset_id・operation_log_evidence_id必須、payload external_operation_row_id必須一致、provider_operation_id任意）／screenshot evidence（公開確認 — WF-WP-2）
- **使用テーブル・正本**: rw: external_operations／w: evidence（外部操作証跡 = operation_log kind） / published_url（evidence）／w: assets／r: pair_plan_quality（ペア成立検証）／r: approvals（公開時）／rw: playbooks（テーマ解析）／r: config（rate.wp.*・接続レジストリ行）
- **外部依存**: ローカル Docker WP（wordpress + mariadb — 唯一の実書込み先）／WP REST API（Application Passwords）／WP-CLI
- **設定値**: config.rate.wp.burst_per_min（暫定既定 30 req/分）／config.rate.wp.publish_daily_cap（暫定既定 10 件/日）／config.external_write_policy.content_publish.allowed_services/endpoints（service=wp・Docker WP endpoint固定） ／ **固定値**: 下書き作成と公開は別 idempotency key の別行（s0-contract §1）／書込み許可 endpoint = ローカル Docker WP のみ（環境契約 §6）
- **trace**: 上流 = BR-G4 BR-I7 REQ-036 REQ-008 ／ 下流 = AC-44-1 AC-44-2 AC-44-3 FN-406 FN-407 CMP-10 ／ スライス = S1

## FR-45 Notion 同期

- **入力**: スプリント開始イベント（読取りトリガ — オーケストレータから）／レビュー成立イベント（書戻しトリガ — pair 成立後）／Notion 側計画ページ（接続レジストリ経由: MCP 優先／ブラウザ fallback）／書戻し対象の結果データ（sprints・learnings 由来の要約）
- **出力**: 読取り時: 計画データの SQLite 側 draft（sprints/action_plans への参照材料 — 判定には使わない）／書戻し時: Notion ページ更新＋external_operations/operation_log 証跡／障害時: NotionUnavailable 記録（同期タスクのみ失敗 — ループは継続）
- **事前条件**: 接続レジストリに Notion 行（MCP 優先・ブラウザ fallback）が存在する／credential は暗号化ストアから実行時注入（FR-47）／書戻しは操作単位のidempotency keyを保持する／config.external_write_policy.review_syncがNotion service/operation/target_endpointを明示し、書戻し対象へbindingしたapproved approvalが存在する
- **事後条件**: 読取り結果は SQLite に draft として保存され、ループ判定は SQLite のみで行われている／書戻し 1 件につき external_operations 1 行と operation_log 証跡が残っている／Notion 障害時も loop_runs / tasks の進行が Notion 応答に依存していない
- **不変条件**: Notion はループ判定・ゲート判定に関与しない（SQLite が唯一の正本 — FR-45）／同期は低頻度バッチ（3 req/秒・2,000 字分割を前提 — BR-M-NOTION-1）でレート超過しない／変更検知はポーリング（last_edited_time・分単位精度）でカーソルに余裕を持たせ取りこぼさない（BR-M-NOTION-2）
- **状態遷移**: テーブル列: external_operations.status: prepared→sent→confirmed/rejected/unknown（書戻し操作ごと）
- **正常動作**: Notion計画ページreadはpolicy_category='external_read'・rate_scope=NULL、結果要約書戻しはexternal_operations(effect='write', policy_category='review_sync', rate_scope='notion', service='notion', operation='sync_result', target_endpoint=config登録値)とする。書戻しは明示policyとbinding済みapproved approvalをpreflight検証した後だけprepared化し、各実要求をoperation_log INSERT triggerでfinal化する。
- **拒否・異常動作**: allow-list/config/approved approval/binding/credential/マスキングの欠落・不一致はpreflight拒否し外部呼出・external_operations・operation_log各0、process loggerへ事由コードを記録する。送信済み要求の応答不能・429だけはsent行とoperation_logをrejected/unknownへ確定し同期taskのみ失敗又は繰越す。
- **境界動作**: 2,000 字境界はブロック分割で送信（1 ブロック超過を作らない）。ポーリング精度が分単位のため境界更新はカーソル余裕で重複取得し、取得側の冪等 upsert で吸収。空の計画ページは draft なしとして正常終了。
- **再試行・再開・復旧**: 書戻し中クラッシュは external_operations の prepared/sent 照合で再開（sent 照合不能は unknown・再送なし）。読取りはカーソル位置から再実行安全。同期失敗は次回トリガで最初から再試行してよい（低頻度・冪等）。
- **人間判断／escalation**: なし（全自動。恒常的な Notion 障害の運用判断は escalated 経由で人間）
- **副作用**: Notion ページ読取り・書戻し（外部）／external_operations INSERT/UPDATE／operation_log INSERT／SQLite への計画 draft 保存
- **冪等性**: 書戻しは操作単位の idempotency key で二重実行を検出（BR-I7）。読取りはlast_edited_timeカーソル＋冪等upsertで重複取得を吸収し、同一request_hashの境界poll/再取得はrequest_sequenceを単調増加して各要求を区別する。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: operation_log 行（service=notion・external_operation_row_id・correlation_key・request_hash・request_sequence。対応external_operations.idを必須とし、provider external_operation_idは任意）／読取り draft の file_hash / measurement 系証跡（取得物の同定）
- **使用テーブル・正本**: rw: external_operations／w: evidence（外部操作証跡 = operation_log kind）（evidence）／r: sprints / learnings（書戻し元）／w: action_plans / sprints への draft 参照材料／r: config（registry.notion・rate.notion.*）
- **外部依存**: Notion（公式 MCP 優先／ブラウザ fallback — 接続レジストリ準拠）
- **設定値**: config.rate.notion.req_per_sec（暫定既定 3 req/秒）／config.sync.notion.cursor_margin_min（ポーリングカーソル余裕・分）／config.external_write_policy.review_sync.allowed_services/endpoints（Notion operation・endpointの必須許可行） ／ **固定値**: Notion 本文分割単位 2,000 字（BR-M-NOTION-1）／webhook はループ判定に使わない（ポーリング基本 — BR-M-NOTION-2）
- **trace**: 上流 = BR-M-NOTION-1 BR-M-NOTION-2 BR-A1 ／ 下流 = AC-45-1 AC-45-2 AC-45-3 FN-408 CMP-07 ／ スライス = S1

## FR-46 承認チャネル

- **入力**: 承認要求（対象 binding_subject・操作 binding_operation・時点 binding_at — 公開系タスクから）／承認応答（approved/rejected/expired/pending — 許可済み ApprovalTransport からの応答）／オートモード判定材料（config.auto_mode_criteria＋実績証跡 — 機械判定用）
- **出力**: approvals 行（初期channel=discord・binding 3 項目・decision・responder_ref）／approval evidence（kind=approval — decision=approved 時、approvals.evidence_id と相互整合）／拒否時: ApprovalBindingMismatch / NonRetryableFailure 例外と対応する task 遷移
- **事前条件**: 個人 Discord の許可済み承認者 user ID が構成済み（将来 Web UI / PWA 認証へ拡張可能、transport は mock 可）／承認要求は binding 3 項目（対象・操作・時点）を欠落なく明記している／config.approval_retry_limitが存在する／config.external_write_policy.approval_notificationが初期service='discord_app'・operation='approval_request'・endpointを明示し、通知payloadのbinding 3項目が完全である
- **事後条件**: 承認要求 1 件につき approvals 1 行が (task_id, binding 3 項目) UNIQUE で存在する／approved 時のみ後続の公開操作が binding 3 項目の完全一致照合を通過できる／decision と task 状態が対応している（approved→進行／rejected→failed／expired→再要求または escalated／pending→waiting）
- **不変条件**: pending の間、対象タスクは進行せず親 loop_run は waiting のまま（AC-46 系 — 先行公開経路なし）／binding 3 項目のいずれか 1 つでも不一致なら公開は通らない（部分一致許容なし）／承認応答の書換え・削除は不可（approvals は証跡 — decision 変更は新規要求で行う）
- **状態遷移**: tasks: in_progress→failed（non_retryable_failure — rejected）／in_progress→escalated（escalate — expired 上限到達）／tasks: verifying→done（verify_pass — 承認証跡完備が前提）／テーブル列: approvals.decision: pending / approved / rejected / expired
- **正常動作**: binding 3項目を明記した実通知だけをexternal_operations(effect='write', policy_category='approval_notification', rate_scope='discord', service='discord_app', operation='approval_request', target_endpoint=config登録値)として記録する。Discord interactionはVPS HTTPS endpointでraw body署名・timestamp/replay・application/guild/channel/user allow-list・approval ID・期限・bindingを検証し、合格時だけpending行をCAS確定する。inboundはexternal readではないためexternal_operations/operation_logを作らない。将来Web UIは認証契約を追加する将来スライスまで不許可。mock/dry-runは外部操作両テーブル0。
- **拒否・異常動作**: notification allow-list/config欠落、service/operation/endpoint不一致、binding欠落はpreflightで拒否し、外部呼出・external_operations・operation_log各0、process loggerへ事由コードを記録する。署名・鮮度・replay・identity・approval ID・binding・expiry検証に失敗したinteractionはdecision不変で拒否する。正当な人間rejectedだけをpending限定CASで確定しtaskをfailedへ倒す。inbound用operation_logは作らない。
- **境界動作**: expired は承認を再要求して待機継続し、再要求回数が config.approval_retry_limit に到達したら escalated へ（無限待機しない）。同一 (task, binding 3 項目) の重複要求は UNIQUE 制約で既存行に照合。binding_at と実公開時点の乖離は不一致として拒否。
- **再試行・再開・復旧**: クラッシュ後は approvals.decision から再開: pending は応答待ちを継続、approved は evidence 整合を確認して公開へ、rejected/expired は各遷移規則を適用。通知の再送は同一 binding の再要求として扱い二重承認を作らない。
- **人間判断／escalation**: 承認応答そのもの（approve/reject）が人間判断の正規経路（BR-H1 — 束縛承認）。オートモード移行後は基準充足の機械判定で承認を省略
- **副作用**: Discord App への初期通知送出（交換可能 transport、将来 Web UI / PWA、テストは mock 可）／external_operations INSERT/UPDATE＋対応operation_log INSERT（実通知writeだけ。inbound interactionは対象外）／approvals INSERT/UPDATE（decision）／evidence INSERT（kind=approval）／秘匿化済み構造化拒否ログ（照合拒否時）／tasks の状態遷移（状態機械 FR-11 経由）
- **冪等性**: 承認要求は (task_id, binding_subject, binding_operation, binding_at) UNIQUE で重複要求を検出。応答の重複受信は decision 確定済み行への no-op。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: approvals 行（binding 3 項目・decision・responder_ref・decided_at）／approval evidence（decision=approved・approvals.evidence_id と相互整合）／operation_log（実通知writeのexternal_operation_row_id・correlation_key・request_hash・request_sequence）とapproval evidence（Discord interaction ID・検証済みprincipal）／秘匿化済み構造化拒否ログ（binding 不一致の公開拒否）
- **使用テーブル・正本**: rw: approvals／rw: external_operations（承認通知の送出）／w: evidence（approval）／w: evidence（外部操作証跡 = operation_log kind）／rw: tasks（遷移は FR-11 経由）／r: config（approval_retry_limit・auto_mode_criteria）
- **外部依存**: ApprovalTransport（初期 Discord App、将来 Web UI / PWA — テストは mock）
- **設定値**: config.approval_retry_limit（expired 再要求の上限）／config.auto_mode_criteria（オートモード移行基準 — C）／config.external_write_policy.approval_notification.allowed_services/endpoints（初期 Discord App operation・endpointの必須許可行） ／ **固定値**: channel = discord（S0 DDL CHECK。web_uiは認証・CSRF・再認証・principal束縛のAC/TCを追加する将来要件まで不許可）／binding 照合は 3 項目完全一致（部分一致なし）
- **trace**: 上流 = BR-H1 BR-H2 REQ-038 ／ 下流 = AC-46-1 AC-46-2 AC-46-3 AC-46-4 FN-409 FN-410 CMP-11 ／ スライス = S0

## FR-47 秘匿情報

- **入力**: credential 投入（Application Password・API キー・ログインセッション — 初回は人が暗号化ストアへ）／秘匿値の取得要求（service 名 — コネクタ実行時注入用）／ログ・証跡へ書き出される全文字列（マスキング検査対象 — NFR-4）
- **出力**: 実行時注入される秘匿値（メモリ上のみ — 呼出コネクタへ）／取得不能時: SecretUnavailable 例外（操作は開始されない）／マスキング済みログ・証跡（平文 credential を含まない）
- **事前条件**: OS キーチェーンまたは暗号化ストアが利用可能である／テスト用と本番用 credential が別発行・別保管されている（環境契約 §6）／マスキング規則（既知 secret 値・パターン）がロード済み
- **事後条件**: リポジトリ・SQLite・ログ・evidence の全文検索で平文 credential 検出 0 件（AC-47）／秘匿値はメモリ内でのみ使用され、外部操作後に永続化されていない／テスト credential が本番 endpoint に、本番 credential が Docker/mock に使われていない
- **不変条件**: 平文 credential ゼロ（NFR-4 — SQLite/repo/ログ/evidence のいずれにも置かない）／evidence.external_operation_id 等の記録は秘匿情報を除いて行われる（s0-contract §1）／秘匿ストアを迂回して credential をコードや config に埋め込む経路が存在しない
- **状態遷移**: tasks: in_progress→escalated（credential再投入・失効/再発行が必要なSecretUnavailable/CredentialLeakDetected, event=escalate）／tasks: pending→in_progress（credential再投入後に明示発行したreplacement task, event=claim）
- **正常動作**: コネクタが接続時に service 名で秘匿値を要求すると、暗号化ストア（OS キーチェーン優先）から復号してメモリ上でのみ注入する。process log・外部操作証跡・その他 evidence への全書出しはマスキング層を通過し、既知 secret 値・credential パターンを伏字化してから永続化する。
- **拒否・異常動作**: 秘匿値の取得不能（未投入・復号失敗・ストア不能）は SecretUnavailable を raise し外部操作を開始しない（fail-close）。credential再投入が必要な場合は当該tasks.in_progressをevent=escalateでescalatedへ遷移する。書出し内容に平文credentialを検知した場合は永続化前に拒否・マスクし、CredentialLeakDetectedを秘匿化済み構造化検知ログへ記録して、当該taskをevent=escalateでescalatedへ遷移しcredential失効・再発行を要求する。credentialとテスト/本番endpointの組合せ不一致も送信前に拒否する（環境契約 §6）。
- **境界動作**: セッション失効・期限切れは取得時に検知し、再投入が必要なら escalated（credential 再投入は人の関与 — s0-contract §3.1 escalate ガード）。マスキングは部分一致（URL 埋込・JSON 内包）も対象。空ストア = 全接続不能（安全側）。
- **再試行・再開・復旧**: 秘匿ストアは SQLite 外のため DB 再開手順に依存しない。escalated は終端なのでcredential再投入後も元taskを変更・再開せず、人が元taskをparent/sourceとしてreplacement taskを明示発行し、新taskをpending→in_progress（event=claim）で開始する。マスキングは書出しごとの純検査で再実行安全。
- **人間判断／escalation**: 人間: credential の初回投入・失効時の再投入（環境契約 §6）。検査・マスキング・拒否は全自動
- **副作用**: OS キーチェーン／暗号化ストアの読取り／秘匿化済み構造化検知ログ（漏洩検知・取得不能時）／なし（正常注入は永続化を伴わない）
- **冪等性**: 取得・マスキングは pure（同一入力→同一結果）。漏洩検知ログは書出し操作単位で1行。再投入は上書きで冪等だが終端元taskを復活させず、replacement taskは元task IDを含む決定的idempotency keyで重複発行を拒否する。
- **証跡**: 秘匿化済み構造化ログ（SecretUnavailable・CredentialLeakDetected — 秘匿値そのものは含まない）／全文検索 0 件の検査結果（AC-47 の検証観測）
- **使用テーブル・正本**: r: config（マスキング規則の非秘匿設定）／rw: tasks（escalateとreplacement task発行）／w: state_transitions（escalate/claim）
- **外部依存**: OS キーチェーンまたは暗号化ストア（SQLite 外 — 鍵分離 BR-F4）
- **設定値**: config.secret.masking_patterns（credential パターンの非秘匿定義） ／ **固定値**: 秘匿値の保管先 = OS キーチェーン／暗号化ストアのみ（SQLite・repo・ログ禁止 — BR-F4）
- **trace**: 上流 = BR-F4 REQ-031 NFR-4 ／ 下流 = AC-47-1 AC-47-2 AC-47-3 AC-47-4 AC-47-5 AC-47-6 FN-411 CMP-07 ／ スライス = S0

## FR-51 レンダリングパイプライン

- **入力**: 制作タスク ID（int — tasks、T-PROD 系）／入力ソース（git ワークスペース内の HTML/SVG/原稿ファイル群 — commit で特定）／出力プロファイル（str — screenshot|pdf|manuscript、workflows の step 定義由来）／WP 接続情報（Docker WP のみ — 接続レジストリ経由）
- **出力**: レンダリング成果物（画像/PDF/原稿ファイル — WP メディアへアップロード）／assets への参照登録行（wp_media_id・canonical_url・content_hash）／evidence 行（kind=file_hash — 出力の SHA-256）／失敗時: RenderFailed 例外（段階・理由つき）
- **事前条件**: 入力ソースが git ワークスペースに commit 済み（未 commit の作業ツリーは入力にしない）／対象 task が実行中状態にある／WP コネクタの接続先が Docker WP である（環境契約 §6）
- **事後条件**: 出力ファイルの SHA-256 が evidence（kind=file_hash）に記録されている／WP アップロード成功時は assets に参照行が 1 件存在し content_hash が出力 hash と一致する／失敗時は assets・WP に部分成果物が残っていない
- **不変条件**: 同一 commit ＋同一プロファイル→同一出力 hash（決定性 — NFR-2。時刻・乱数は Clock/Rng 注入でレンダリングに混入させない）／コンテンツ実体は WP へ収束し SQLite には参照（hash・ID・URL）のみを置く（BR-G2）／外部書込み先は Docker WP のみ（本番 WP への書込みは常時拒否）
- **状態遷移**: なし
- **正常動作**: 出力生成・SHA-256算出後、固定policy一致をpreflight検証し、Docker WPメディアアップロードをexternal_operations(effect='write', policy_category='content_publish', service='wp', operation='upload_media', target_endpoint=Docker WP)とoperation_logで証跡化する。
- **拒否・異常動作**: 入力ソースが未 commit・commit 解決不能なら UnversionedSourceRejected、接続先が Docker WP 以外なら WpTargetDenied で送信前に拒否し、external_operations/operation_log を作らず process logger の構造化拒否 event に記録する。レンダリング途中失敗は RenderFailed を raise し、WP アップ済み断片があれば削除を別の外部操作として external_operations/operation_log に記録したうえで assets/evidence を書かない（fail-close）。
- **境界動作**: 空の入力ソース（対象ファイル 0 件）は RenderFailed で拒否。同一 commit＋同一プロファイルの再実行は同一 hash を得て assets の UNIQUE(canonical_url/wp_media_id) で重複登録されない。巨大出力はサイズ上限（config）超過で拒否。
- **再試行・再開・復旧**: assets/evidence 書込みは同一 transaction のためクラッシュで中間行が残らない。WP アップ後・登録前のクラッシュは、再実行時に content_hash 一致の既存メディアを照合して再アップせず登録のみ行う（冪等再開）。
- **人間判断／escalation**: なし（全自動。成果物の合否は FR-27 審査ゲートの領分）
- **副作用**: Docker WP メディアへのアップロード／assets INSERT／evidence INSERT（file_hash）／external_operations INSERT/UPDATE＋対応する operation_log INSERT（Docker WP のアップロード／補償削除だけ）／秘匿化済み構造化拒否ログ（送信前拒否）
- **冪等性**: 出力 hash と assets の UNIQUE 制約が冪等キー。同一入力の再実行は同一 hash に収束し、参照行・証跡は重複しない。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: evidence 行（kind=file_hash — file_path・file_hash・algorithm=SHA-256）／operation_log 行（WPアップロード／補償削除のexternal_operation_row_id。provider external_operation_idは任意）
- **使用テーブル・正本**: r: tasks／r: workflows（出力プロファイル）／w: assets／rw: external_operations（WP アップロード／補償削除）／w: evidence／r: config（サイズ上限・WP 接続参照）
- **外部依存**: ヘッドレスブラウザ（スクショ・PDF 化）／Docker WP（メディア API）／git（commit 解決）
- **設定値**: config.render_output_max_bytes／config.wp_target（Docker WP 接続参照） ／ **固定値**: hash アルゴリズム = SHA-256／出力プロファイル種別（screenshot|pdf|manuscript）
- **trace**: 上流 = BR-G1 BR-G2 NFR-2 REQ-041 ／ 下流 = AC-51-1 AC-51-2 AC-51-3 AC-51-4 AC-51-5 FN-501 FN-502 FN-503 CMP-12 ／ スライス = S0

## FR-52 デザイントークン適用

- **入力**: レンダリング要求（FR-51 パイプラインからの呼出 — 対象ソース参照つき）／デザイントークン集合（Claude Design / DesignSync 正本から取得 — JSON）／トークンキャッシュ（直近同期済み — ローカルストア、版数・hash つき）
- **出力**: トークン注入済みレンダリング入力（CSS 変数等へ展開）／適用記録（使用トークンの版数・hash — evidence payload に記録）／取得不能かつキャッシュなし: DesignTokenUnavailable 例外
- **事前条件**: 対象制作物がトークン適用対象（レンダリング経由）である／トークン正本への同期経路またはキャッシュのいずれかが構成済みである
- **事後条件**: レンダリング出力に適用されたトークンの版数・hash が証跡に残っている／正本取得成功時はキャッシュが取得内容で更新されている／トークン外の恣意的スタイル指定が注入されていない（BR-G3 禁止事項）
- **不変条件**: トークンは Claude Design 正本（またはその同期キャッシュ）からのみ取得し、複製・手書き定義を持たない／同一トークン版＋同一ソース→同一出力（決定性 — NFR-2。トークン版 hash を証跡化して非決定要素を固定）
- **状態遷移**: なし
- **正常動作**: DesignSync取得要求をexternal_operations(effect='read', correlation_key='read:<task_id>:<request_hash>:<request_sequence>')のprepared→sent→confirmedとexternal_operation_row_id・request_sequence一致の対応operation_logで証跡化 → 版数・hashを算出しキャッシュを更新 → レンダリング入力へトークンを注入（CSS変数・テーマ値展開）→ 適用トークンの版数・hashをレンダリング証跡payloadに記録する。
- **拒否・異常動作**: DesignSync へ送信済みの取得要求が失敗した場合は external_operations を rejected 又は unknown に確定し、対応する operation_log を記録する。取得不能かつキャッシュも存在しない場合は DesignTokenUnavailable を raise しレンダリングを実行しない。キャッシュ破損（hash 不一致・JSON 不正）とキャッシュなしの最終拒否は内部判定のため operation_log を作らず、process logger の秘匿化済み構造化拒否 event に記録する。
- **境界動作**: 正本取得不能でキャッシュありは直近同期済みキャッシュで継続し、キャッシュ利用（stale）フラグと版数を証跡に残す。トークン集合が空の応答は取得失敗と同等に扱う。
- **再試行・再開・復旧**: 取得はタイムアウト後に規定回数まで再試行し、同一request_hashの各実試行はrequest_sequenceを1から単調増加して別external_operations行・別operation_logへ記録する。失敗はキャッシュ経路へフォールバックし、キャッシュ更新はアトミック（temp 書込み→rename）で中間状態を残さない。
- **人間判断／escalation**: なし（デザインシステム自体の改訂承認は BR-G3 の PO 領分）
- **副作用**: トークンキャッシュ ファイル更新／external_operations INSERT/UPDATE＋対応する operation_log INSERT（DesignSync 取得要求だけ）／秘匿化済み構造化ログ（フォールバック・内部拒否）
- **冪等性**: 同一トークン版での再適用は同一出力。取得は read-only で何度実行しても正本を変更しない。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: レンダリング証跡 payload 内のトークン版数・hash・stale フラグ／operation_log（DesignSync取得のexternal_operation_row_id・correlation_key・request_hash・request_sequence。provider external_operation_idは任意）／秘匿化済み構造化ログ（フォールバック・内部拒否）
- **使用テーブル・正本**: rw: external_operations（DesignSync 取得要求）／w: evidence（external_operations に対応する operation_log）／r: config（DesignSync 接続参照・再試行回数）
- **外部依存**: Claude Design（DesignSync — トークン正本）
- **設定値**: config.designsync_source（正本参照）／config.designsync_fetch_retry_max／config.designsync_cache_path ／ **固定値**: キャッシュ検証 = SHA-256 hash 一致／トークン注入方式（CSS 変数展開）
- **trace**: 上流 = BR-G3 REQ-035 NFR-2 ／ 下流 = AC-52-1 AC-52-2 AC-52-3 FN-504 CMP-12 ／ スライス = S1

## FR-53 音声・動画・EPUB パイプライン

- **入力**: 台本・素材参照（git ワークスペース＋WP 資産参照 — commit・asset_id で特定）／パイプライン種別（str — voice|video|epub|3d）／実行プロファイル（VOICEVOX 話者・Remotion 比率プロファイル・pandoc 設定 — config/固定値）
- **出力**: 生成メディア（mp3/mp4/epub — WP メディアへアップし assets 参照登録）／実行記録（入力参照・ツール版数・コマンドライン・出力 hash — evidence payload）／失敗時: PipelineExecutionFailed 例外（段階つき）
- **事前条件**: 台本・素材参照が commit／asset_id で完全に特定できる（浮動参照なし）／対象ツール（VOICEVOX localhost・ffmpeg/Remotion・pandoc）が到達可能である
- **事後条件**: 入力（台本・素材参照）から出力までが再現可能なコード実行として記録されている（ツール版数・パラメータ・出力 hash）／生成物は WP 資産として登録され、元資産への parent_asset_id 参照を保持する（リパーパス系譜 — FR-55）
- **不変条件**: 同一入力＋同一ツール版→同一出力（決定性 — NFR-2。エンコーダ等の非決定要素は出力 hash を証跡化して固定し、乱数種・時刻は Clock/Rng 注入）／コンテンツ実体は WP 収束・SQLite は参照のみ（BR-G2）／外部書込みは Docker WP のみ
- **状態遷移**: なし
- **正常動作**: パイプライン出力のSHA-256算出後、固定policy一致をpreflight検証し、Docker WPアップロードをexternal_operations(effect='write', policy_category='content_publish', service='wp', operation='upload_media', target_endpoint=Docker WP)とoperation_logで証跡化する。
- **拒否・異常動作**: 入力参照が解決不能（存在しない asset_id・未 commit 台本）は UnversionedSourceRejected で拒否。ツール到達不能・実行失敗は PipelineExecutionFailed を raise し、部分出力を assets/WP に登録しない。実行記録を残せない場合も成果物を登録せず拒否する（記録なし成果物の禁止 — fail-close）。
- **境界動作**: 長尺入力は config の実行タイムアウト・サイズ上限で打ち切り拒否。VOICEVOX は localhost のみ許可（外部 TTS への送信は経路として存在しない）。同一入力の再実行は出力 hash 一致で assets 重複登録されない。
- **再試行・再開・復旧**: ツール実行は task 単位で最初から再実行（中間ファイルは temp 領域に置き、成功時のみ採用）。クラッシュ時は temp を破棄して再実行すれば同一出力に収束する。
- **人間判断／escalation**: なし（全自動。成果物の公開可否は審査・承認ゲートの領分）
- **副作用**: ツールプロセス実行（VOICEVOX/ffmpeg/Remotion/pandoc）／Docker WP メディアアップロード／assets INSERT／evidence INSERT／external_operations INSERT/UPDATE＋対応する operation_log INSERT（Docker WP アップロードだけ）
- **冪等性**: 同一入力・同一ツール版の再実行は同一 hash に収束し、assets/evidence の UNIQUE 制約で重複しない。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: evidence 行（kind=file_hash — 出力 hash）／実行記録 payload（入力参照・ツール版数・パラメータ）／operation_log 行（Docker WPアップロードのexternal_operation_row_id。provider external_operation_idは任意）
- **使用テーブル・正本**: r: tasks／r: assets（素材参照・parent 解決）／w: assets／rw: external_operations（Docker WP アップロード）／w: evidence／r: config
- **外部依存**: VOICEVOX（localhost）／Remotion / ffmpeg（NVENC）／pandoc／Blender ヘッドレス（3D — S3）／Docker WP
- **設定値**: config.pipeline_exec_timeout_sec／config.pipeline_output_max_bytes／config.voicevox_endpoint（localhost 固定値の参照） ／ **固定値**: VOICEVOX 接続先 = localhost のみ／hash アルゴリズム = SHA-256／動画比率別プロファイル定義
- **trace**: 上流 = BR-G1 BR-G2 NFR-2 ／ 下流 = AC-53-1 AC-53-2 AC-53-3 FN-505 FN-506 FN-507 FN-508 CMP-12 ／ スライス = S3+

## FR-54 版と証跡（commit hash 束縛）

- **入力**: 審査対象の成果物ソース（git ワークスペースのパス群）／対象 task ID（int — tasks、T-PROD/T-REVIEW 系）／審査 PASS 記録要求（reviewer・checked_items — FR-27 経路）
- **出力**: evidence 行（kind=commit_hash — repository・commit_hash・paths）／PASS 記録（kind=review_pass — commit_hash 列で成果物版に束縛）／hash 不一致時: CommitHashMismatch 例外
- **事前条件**: 成果物ソースが git 管理下にあり commit 済みである（REQ-032）／commit_hash 証跡の記録が PASS 記録より先行している
- **事後条件**: 審査に出た成果物が commit hash で一意に特定できる／PASS 記録の commit_hash 列が成果物の commit_hash 証跡と一致している／hash から成果物ソースを checkout で復元できる（AC-54 系）
- **不変条件**: 版管理外の成果物は審査・公開経路に乗らない（BR-G1 禁止事項）／PASS 後の改変は新 commit＝新 hash となり、旧 PASS は新版に流用できない（版すり替えの構造的排除）
- **状態遷移**: なし
- **正常動作**: 制作完了時にワークスペースの HEAD commit hash（40/64 桁）と対象 paths を evidence（kind=commit_hash）へ INSERT → 審査時は同 hash を review_pass 証跡の commit_hash 列・payload に記録し、PASS が特定版に束縛される。公開ゲート（FR-27 側）はこの束縛を検査する。
- **拒否・異常動作**: 未 commit の作業ツリー・dirty 状態での証跡化要求は UnversionedSourceRejected で拒否。PASS 記録時に指定 commit_hash が当該 task の commit_hash 証跡と一致しなければ CommitHashMismatch で拒否し秘匿化済み構造化拒否ログに記録（fail-close）。hash 桁数不正は DDL CHECK でも拒否される。
- **境界動作**: 同一 task で複数回 commit した場合は最新の commit_hash 証跡が審査対象版。40 桁（SHA-1）と 64 桁（SHA-256）の両 git hash を許容し、それ以外の長さは拒否。paths 空の証跡は拒否。
- **再試行・再開・復旧**: 証跡は append-only のため再実行は UNIQUE(task_id, kind, value) で重複 INSERT にならない。復元は evidence の repository・commit_hash から git checkout で決定的に再現する。
- **人間判断／escalation**: なし（審査 PASS の実施主体は FR-27 のペア審査 — 本 FR は束縛の機械保証のみ）
- **副作用**: evidence INSERT（commit_hash / review_pass）／構造化ログ出力（拒否時 — FN-704）
- **冪等性**: 同一 (task_id, kind, commit_hash) の再記録は UNIQUE 制約で 1 行に収束。判定（一致検査）は pure。
- **証跡**: evidence 行（kind=commit_hash）／evidence 行（kind=review_pass — commit_hash 束縛）／秘匿化済み構造化拒否ログ
- **使用テーブル・正本**: r: tasks／w: evidence／r: pair_plan_quality（審査経路整合の参照）
- **外部依存**: git（hash 取得・checkout 復元）
- **設定値**: なし ／ **固定値**: commit_hash 桁数 = 40 または 64（DDL CHECK と同値）／evidence kind = commit_hash / review_pass（s0-contract §2.1）
- **trace**: 上流 = BR-G1 BR-B3 REQ-032 ／ 下流 = AC-54-1 AC-54-2 AC-54-3 AC-54-4 AC-54-5 FN-511 CMP-12 ／ スライス = S0

## FR-55 資産収束・リパーパス追跡

- **入力**: 登録要求（asset_type・name・WP アップロード結果の wp_media_id・canonical_url・content_hash）／派生登録時: 元資産 ID（int — assets.parent_asset_id へ）／出所 task ID（int — assets.source_task_id へ）
- **出力**: assets 行（参照のみ — 実体は WP 側）／派生時: parent_asset_id で系譜接続された assets 行／実体格納の試行: ContentBodyRejected 例外
- **事前条件**: コンテンツ実体が WP へアップロード済みで wp_media_id または canonical_url が得られている／派生登録時は parent の assets 行が存在する
- **事後条件**: assets 行は参照情報（ID・URL・hash・metadata）のみを保持し本文実体を含まない／派生資産から parent_asset_id を再帰的に辿って元資産（記事）へ到達できる（リパーパス系譜）
- **不変条件**: コンテンツ実体の正本は WP に一元化され SQLite は参照のみ（BR-G2 — 実体の DB 直接格納の禁止）／出自記録（parent 参照・source_task_id）のない派生資産は存在しない
- **状態遷移**: なし
- **正常動作**: WP アップロード完了後、wp_media_id・canonical_url・content_hash・metadata を assets へ INSERT。派生制作（記事→SNS/スライド/音声/動画/EPUB）では parent_asset_id に元資産を指定して INSERT し、系譜クエリ（再帰 CTE）で追跡可能にする。
- **拒否・異常動作**: 登録ペイロードに本文実体（本文テキスト・バイナリ・data URI 等、参照サイズ上限超のフィールド）が含まれる場合は ContentBodyRejected で拒否。WP 参照（wp_media_id/canonical_url）のいずれも欠く登録・存在しない parent_asset_id 指定は AssetReferenceInvalid で拒否し秘匿化済み構造化拒否ログに記録（fail-close）。
- **境界動作**: canonical_url・wp_media_id は UNIQUE で二重登録は制約違反として拒否。自己参照（parent = 自分）・循環系譜は登録時検査で拒否。parent なし（根 = オリジナル記事）は正常。
- **再試行・再開・復旧**: 登録は 1 INSERT = 1 transaction。再実行は UNIQUE(canonical_url/wp_media_id) で重複せず、既存行を返して冪等に完了する。WP 側と参照の不整合は content_hash 照合で検出し escalation（BR-H3）へ回す。
- **人間判断／escalation**: なし（全自動）
- **副作用**: assets INSERT／構造化ログ出力（拒否時 — FN-704）
- **冪等性**: UNIQUE(canonical_url)・UNIQUE(wp_media_id) が冪等キー。同一資産の再登録は行を増やさない。
- **証跡**: assets 行自体（参照＋系譜の正本）／秘匿化済み構造化拒否ログ／公開時は evidence（kind=published_url — asset_id 列で接続）
- **使用テーブル・正本**: rw: assets／r: tasks（source_task_id 整合）
- **外部依存**: Docker WP（実体の置き場 — 本 FR 自体は参照登録のみ）
- **設定値**: config.asset_metadata_max_bytes（参照サイズ上限 — 実体混入検知） ／ **固定値**: 系譜構造 = parent_asset_id による単方向ツリー（循環禁止）
- **trace**: 上流 = BR-G2 REQ-033 REQ-034 ／ 下流 = AC-55-1 AC-55-2 AC-55-3 AC-55-4 FN-512 CMP-12 ／ スライス = S0

## FR-61 KPI ツリー

- **入力**: KPI ノード定義（node_key・name・layer・medium・metric_type・aggregation_formula・parent_node_id — 登録要求）／対象 business_profile_id（int — business_profiles）／計測値の紐付け照会（node_key／layer／medium 条件 — 集計クエリ）
- **出力**: kpi_nodes 行（5 階層のいずれかに接地）／媒体横断集計クエリの結果セット（layer×medium 断面）／有料指標の登録要求: PaidMetricRejected 例外（FR-23 連携）
- **事前条件**: 対象 business_profile が存在する／parent_node_id 指定時は親ノードが同一 business_profile に存在する／ゼロ広告費ゲート（FR-23）の有料指標型定義がロード済みである
- **事後条件**: 登録ノードの layer が 5 階層（exposure/micro_cv/conversion/relationship/revenue）のいずれかである／同一 business_profile 内で node_key が一意である／全 measurements 行が kpi_node_id 経由で本ツリーのノードに接地している
- **不変条件**: 有料指標型（cac/roas/ad_spend）のノードは kpi_nodes に存在しない（FR-23 ＋ DDL CHECK の二重防御 — BR-C1）／階層は露出→マイクロ CV→転換→関係→収益の 5 層に閉じ、層外の値は存在しない／KPI ツリーは観測背骨であり、数値変化から戦略正本への自動書込みは行わない（BR-E1 禁止事項）
- **状態遷移**: テーブル列: kpi_nodes.status: active→archived（ノード退役。削除はしない — FK RESTRICT）
- **正常動作**: 登録要求の metric_type を FR-23 の有料指標定義と照合 → 非該当なら layer・medium・aggregation_formula を検証して kpi_nodes へ INSERT。集計は kpi_nodes×measurements の JOIN で媒体横断（layer 別・medium 別）に実行できる正規化を維持する。
- **拒否・異常動作**: 有料指標型は PaidMetricRejected で登録拒否（アプリ層 FR-23 ＋ DDL CHECK(metric_type NOT IN ...) の二重で fail-close）。layer が 5 階層外・node_key 重複・親不在／別 profile の親指定は KpiNodeInvalid で拒否し秘匿化済み構造化拒否ログに記録。
- **境界動作**: 根ノード（parent_node_id NULL）は正常。measurements から参照中のノードは FK RESTRICT で削除不能（archived 化のみ）。同一 node_key の再登録は UNIQUE(business_profile_id, node_key) で拒否。
- **再試行・再開・復旧**: 登録は 1 INSERT = 1 transaction で中間状態なし。再実行は UNIQUE 制約で重複せず拒否される（既存確認後の冪等応答可）。集計クエリは read-only で何度でも安全。
- **人間判断／escalation**: KPI ツリー初期形の承認（リサーチ充填後 — BR-E1。以後のノード登録・集計は全自動）
- **副作用**: kpi_nodes INSERT/UPDATE(status)／構造化ログ出力（拒否時 — FN-704）
- **冪等性**: UNIQUE(business_profile_id, node_key) が冪等キー。集計は pure（同一 DB 状態→同一結果）。
- **証跡**: 秘匿化済み構造化拒否ログ（有料指標拒否・定義不正拒否）／kpi_nodes 行（階層定義の正本）
- **使用テーブル・正本**: rw: kpi_nodes／r: business_profiles／r: measurements（集計）
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: 5 階層 enum（exposure/micro_cv/conversion/relationship/revenue — DDL CHECK と同値）／有料指標型の禁止リスト（cac/roas/ad_spend — FR-23 と共有）
- **trace**: 上流 = BR-E1 REQ-020 REQ-021 ／ 下流 = AC-61-1 AC-61-2 AC-61-3 AC-61-4 AC-61-5 AC-61-6 FN-601 FN-604 CMP-13 ／ スライス = S0

## FR-62 計測取り込みパイプライン

- **入力**: 取得物（正規 API 応答 または ブラウザエクスポートファイル — GA4/GSC は正規 API — ADR-006）／対象サービス種別（str — パーサ選択キー）／対象 T-MEAS task ID（int — tasks）／取得時スクショ（ブラウザ経路時 — file_path）
- **出力**: measurements 行（kpi_node_id・期間・値・evidence_id つき）／evidence 行（kind=measurement — source hash／kind=file_hash／kind=screenshot）／エラー隔離ファイル（パース失敗行 — 隔離先パスと件数）／パース全滅時: ImportSourceInvalid 例外
- **事前条件**: 取得経路が接続レジストリと ADR-006 に従って解決済みである／投入先の kpi_nodes 行が存在する（未登録ノードへの投入はしない）／取得物ファイルが読取可能で SHA-256 を算出できる
- **事後条件**: 取得物の SHA-256 が evidence（kind=measurement の value／file_hash）として投入前に記録されている／正常行のみが measurements に存在し、失敗行は隔離先に件数つきで残っている／全 measurements 行の evidence_id が取得証跡へ FK 接続している
- **不変条件**: 証跡（hash・ブラウザ経路時はスクショ）なしの計測値は measurements に存在しない（BR-E2 禁止事項）／投入は冪等 — 同一エクスポートの再取込で行が重複しない／手動入力値を実測として投入する経路が存在しない
- **状態遷移**: なし
- **正常動作**: 取得要求（GA4/GSCは正規Data API、他はブラウザエクスポート）をexternal_operations(effect='read', correlation_key='read:<task_id>:<request_hash>:<request_sequence>')のprepared→sent→confirmedとexternal_operation_row_id・request_sequence一致の対応operation_logで証跡化 → 取得物のSHA-256算出とevidence（measurement: source・file_hash・period・row_count）INSERT → サービス別パーサで行解釈 → kpi_node解決 → measurementsへ一括INSERT（1取込=1 transaction）。ブラウザ経路では取得画面スクショもevidence化する。
- **拒否・異常動作**: パース失敗行はエラー隔離（隔離ファイル＋件数記録）し、正常行のみ投入する（部分投入許容）。全行失敗・ファイル破損・hash 算出不能は ImportSourceInvalid で全体拒否。未登録 kpi_node 宛の行・有料指標由来の行は投入せず隔離し秘匿化済み構造化拒否ログに記録（fail-close）。
- **境界動作**: 空エクスポート（データ 0 行）は measurements 差分なしで正常終了し、取得証跡のみ残る。同一 (kpi_node_id, period, dimensions) の重複行は UNIQUE 制約で 2 行目以降を投入しない。期間逆転（period_end < period_start）行は隔離。
- **再試行・再開・復旧**: 投入 transaction 失敗は全行 rollback（部分コミットなし）。同一task・operation・request_hashで外部取得を反復する場合はrequest_sequenceを単調増加して別要求として記録し、同一source hashのevidence UNIQUE(task_id, kind, value)とmeasurementsのUNIQUEで業務差分は冪等に収束する。API阻害時はブラウザエクスポートへ一時フォールバックし、同一evidence契約に収束させる。
- **人間判断／escalation**: なし（取得失敗の escalation は BR-H3 経由）
- **副作用**: measurements INSERT／evidence INSERT（measurement/file_hash/screenshot）／隔離ファイル生成／external_operations INSERT/UPDATE＋対応する operation_log INSERT（外部取得要求だけ）／外部 read（GA4 Data API・ブラウザ）
- **冪等性**: source hash（evidence UNIQUE）と measurements の UNIQUE(kpi_node_id, period_start, period_end, dimensions_json) の二重冪等キー。同一エクスポートの再投入は差分ゼロ。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: evidence 行（kind=measurement — source・file_hash・period・row_count）／evidence 行（kind=file_hash／kind=screenshot — ブラウザ経路）／operation_log 行（外部取得のexternal_operation_row_id・correlation_key・request_hash・request_sequence。provider external_operation_idは任意）／秘匿化済み構造化ログ（隔離・拒否）
- **使用テーブル・正本**: w: measurements／r: kpi_nodes／r: tasks／rw: external_operations（外部取得要求）／w: evidence／w: evidence（外部操作証跡 = operation_log kind）／r: playbooks（ブラウザ経路手順）／r: config
- **外部依存**: GA4 / GSC 正規 API（read-only — ADR-006）／ブラウザエクスポート（フォールバック経路）
- **設定値**: config.import_quarantine_dir（隔離先）／config.ga4_property_ref（接続参照 — credential は秘匿ストア） ／ **固定値**: hash アルゴリズム = SHA-256／1 取込 = 1 transaction（部分コミット禁止）
- **trace**: 上流 = BR-E2 REQ-022 REQ-023 ／ 下流 = AC-62-1 AC-62-2 AC-62-3 AC-62-4 AC-62-5 AC-62-6 AC-62-7 FN-602 FN-603 CMP-13 ／ スライス = S0

## FR-63 ダッシュボード生成

- **入力**: SQLite 現在状態（kpi_nodes・measurements ほか — read-only 参照）／生成要求（対象期間・出力先パス — 計測投入後の生成ステップ／PO 閲覧要求）／出力形式（html 主／xlsx 従）
- **出力**: 自己完結 HTML ファイル（CSS/JS インライン・外部 CDN 依存なし）／evidence 行（kind=dashboard — file_path・file_hash・period_end）／xlsx エクスポートファイル（従）／外部参照検出時: ExternalReferenceDetected 例外
- **事前条件**: DB マイグレーション適用済みで参照テーブルが読める／出力先ディレクトリが書込可能である
- **事後条件**: 生成 HTML が外部リソース参照（CDN・外部 URL の script/link/img）を含まない／生成物の SHA-256 が evidence（kind=dashboard）に記録されている／DB の業務テーブルが生成前後で不変（read-only 生成）
- **不変条件**: 生成は決定的 — 同一 DB 状態→同一出力 hash（BR-E3。生成時刻は Clock 注入し出力へ埋め込む場合も入力として固定）／生成物に認証情報・secret を含めない（BR-E3 制約）／手動集計を経由しない（SQLite からの自動生成のみ）
- **状態遷移**: なし
- **正常動作**: SQLite から layer×medium×期間の集計を read-only クエリで取得 → テンプレートへ展開し CSS/JS を全インライン化した自己完結 HTML を生成 → 出力の SHA-256 を算出し evidence（kind=dashboard）へ INSERT。xlsx は同一クエリ結果から従として出力する。
- **拒否・異常動作**: 生成後の自己検査で外部リソース参照を検出したら ExternalReferenceDetected で成果物を破棄し証跡化しない。secret パターン（credential 文字列）の混入検出も同様に破棄・拒否し秘匿化済み構造化拒否ログに記録（fail-close）。DB 読取不能は DashboardGenerationFailed で拒否。
- **境界動作**: measurements が 0 件でも空ダッシュボード（データなし表示）を決定的に生成する。同一 DB 状態での再生成は同一 hash となり evidence の UNIQUE(task_id, kind, value) で証跡が重複しない。巨大 DB は生成タイムアウト（config）で打ち切り拒否。
- **再試行・再開・復旧**: 生成は temp へ書き出し成功時に rename するため中間生成物が残らない。クラッシュ後は再実行のみで復旧（DB は read-only のため汚染なし）。
- **人間判断／escalation**: なし（閲覧のみ — PO が AI を介さず現況把握する手段の提供）
- **副作用**: HTML/xlsx ファイル生成／evidence INSERT（dashboard）／構造化ログ出力（拒否時 — FN-704）
- **冪等性**: 同一 DB 状態→同一出力 hash（pure な変換）。証跡は hash を value とする UNIQUE で重複しない。
- **証跡**: evidence 行（kind=dashboard — file_path・file_hash・period_end）／秘匿化済み構造化実行・拒否ログ
- **使用テーブル・正本**: r: kpi_nodes／r: measurements／r: pair_kpi_measure／r: sprints／w: evidence／r: config
- **外部依存**: なし
- **設定値**: config.dashboard_output_dir／config.dashboard_gen_timeout_sec ／ **固定値**: 自己完結制約（外部 CDN・外部 URL 参照の禁止）／hash アルゴリズム = SHA-256／HTML 主・xlsx 従の序列
- **trace**: 上流 = BR-E3 REQ-024 REQ-025 NFR-2 ／ 下流 = AC-63-1 AC-63-2 AC-63-3 FN-605 FN-606 CMP-13 ／ スライス = S1

## FR-71 主要テーブル（DB スキーマ生成）

- **入力**: DDL 正本（s0-contract §2 — 業務 23＋インフラ 2 の 25 テーブル）／生成対象 SQLite ファイルパス（str）
- **出力**: 25 テーブル＋append-only 保護トリガ＋FK 制約の生成済み SQLite DB／検証結果（DU-11 verify() — pass/fail）／拒否時: SchemaVerificationFailed 例外
- **事前条件**: migration ファイル群（NNNN_description.sql）が存在する／対象 SQLite が空または既知の schema_version を持つ
- **事後条件**: 25 テーブルすべてが DDL 正本と相当である（DDL 相当性検証 PASS）／PRAGMA foreign_key_check・integrity_check が違反 0 件／append-only トリガ（config・evidence・state_transitions）が有効である
- **不変条件**: append-only テーブルへの UPDATE/DELETE は保護トリガが常時 ABORT／FK はすべて ON DELETE RESTRICT（暗黙のカスケード削除は存在しない）／接続開始時に WAL・busy_timeout（config.sqlite_busy_timeout_ms）が設定される
- **状態遷移**: なし
- **正常動作**: 空の SQLite へ migration を順次適用して 23 業務テーブル＋インフラ 2 テーブル（schema_version・state_transitions）・保護トリガ・index を生成 → DU-11 verify() で DDL 相当性・FK 有効性・初期 workflow seed を検証し、PASS で使用開始を許可する。
- **拒否・異常動作**: verify() 不合格（テーブル欠落・DDL 不一致・FK 無効・integrity 違反）は SchemaVerificationFailed を raise し、その DB の使用開始を拒否する（fail-close — 不完全スキーマ上で業務書込みを開始しない）。保護トリガ欠落も同様に拒否。
- **境界動作**: 既に全 migration 適用済みの DB への再適用は no-op（schema_version 照合でスキップ）。空パス・アクセス不能パスは生成前に拒否。SQLITE_BUSY は busy_timeout 内待機→タイムアウトで retryable_failure。
- **再試行・再開・復旧**: migration は transaction 内適用のためクラッシュ時は当該 migration ごと巻き戻る。再開は schema_version の最終行から続行し、適用済み分を再適用しない。
- **人間判断／escalation**: なし（全自動。本番 DB への昇格実施の確認のみ FR-72 経由で人間）
- **副作用**: CREATE TABLE/TRIGGER/INDEX（25 テーブル＋保護トリガ）／schema_version INSERT（適用記録）
- **冪等性**: 適用済み migration は schema_version 照合で再適用されない（version が冪等キー）。verify() は読み取り専用で何度でも安全。
- **証跡**: schema_version 行（version・migration 名・checksum・適用者・時刻）／verify() の検証結果ログ（構造化ログ）
- **使用テーブル・正本**: w: schema_version／r: config（sqlite_busy_timeout_ms）／参照: DDL 25 テーブル全体（s0-contract §2 が正準 — 個別列挙は正本の二重化になるため参照）
- **外部依存**: なし
- **設定値**: config.sqlite_busy_timeout_ms（接続時 PRAGMA） ／ **固定値**: DDL 正本（s0-contract §2 — 変更は migration＋要件改訂のみ）／append-only 対象テーブルの集合（config・evidence・state_transitions）
- **trace**: 上流 = BR-A3 BR-B3 REQ-004 ／ 下流 = AC-71-1 AC-71-2 AC-71-3 AC-71-4 FN-701 FN-703 CMP-04 CMP-05 ／ スライス = S0

## FR-72 マイグレーション（前方参照のみの昇格）

- **入力**: 連番 migration ファイル（NNNN_description.sql — 不変）／昇格対象 DB（現 schema_version 付き）／適用者（applied_by — str）
- **出力**: 昇格済み DB（新 schema_version 行つき）／DU-11 verify() の検証結果／拒否時: MigrationChecksumMismatch／MigrationVerifyFailed 例外
- **事前条件**: 変更が expand/backfill/contract のいずれかとして設計済み／適用前 SQLite backup が作成済み／migration 内容の SHA-256 が算出済み
- **事後条件**: schema_version に version・migration 名・checksum・適用者・時刻が INSERT されている／PRAGMA foreign_key_check・integrity_check が違反 0 件／旧形式 reader が壊れていない（前方参照のみ — 既存の列・値・意味を破壊しない）
- **不変条件**: 昇格は前方参照のみ（rename・意味変更・破壊的変更の禁止 — 新名は expand で追加し旧名は read 互換維持）／適用済み migration ファイルは不変（checksum で改竄検知）／失敗した migration は同じ version を書換えず次 version で修正する
- **状態遷移**: なし
- **正常動作**: expand→backfill→contract の順で設計された migration を transaction 内で適用 → PRAGMA foreign_key_check・integrity_check・行数/hash 比較 → schema_version へ INSERT → DU-11 verify()（FK 有効性・integrity・25 テーブル存在・TLP 孤児検査 = packet なし終端 lower run 0 件）と回帰テストを実行して昇格を確定する。
- **拒否・異常動作**: 同 version が schema_version に既存、または checksum 不一致なら MigrationChecksumMismatch で適用前に停止する。適用後の verify()・回帰テスト失敗は MigrationVerifyFailed とし、backup から復元して昇格を取り消す（fail-close — 壊れた版で運転を続けない）。
- **境界動作**: version 飛び（欠番）は適用順検証で拒否。空 DB への適用は全 migration の一括初期生成（FR-71）。backfill は再開可能・冪等な明示的 task として実行し、巨大更新を暗黙の DDL に混ぜない。
- **再試行・再開・復旧**: transaction 内適用のためクラッシュは当該 migration ごと巻き戻り、schema_version 未記録なら再適用可能。verify() 失敗時は backup 復元が復旧点。backfill は冪等のため中断後の再実行が安全。
- **人間判断／escalation**: 人間: 本番昇格は結果を確認して実施（s0-contract §5.2）。開発 DB への適用・検証は全自動
- **副作用**: DDL 変更（expand/contract）／schema_version INSERT／backup ファイル作成／evidence INSERT（backfill の件数・hash・失敗）
- **冪等性**: version が冪等キー: 適用済み version は再適用されない。backfill は冪等設計を必須とし再実行で二重更新しない。
- **証跡**: schema_version 行（checksum_sha256 含む）／backfill の evidence 行（件数・hash・失敗）／verify()・回帰テストの結果ログ
- **使用テーブル・正本**: rw: schema_version／r: tactical_learning_packets・loop_runs（TLP 孤児検査）／参照: 全業務テーブル（migration の適用対象 — s0-contract §2 が正準）／rw: schema_version
- **外部依存**: なし
- **設定値**: なし ／ **固定値**: migration ファイル命名規約（NNNN_description.sql）／昇格 3 段階（expand/backfill/contract）と rename 禁止（s0-contract §5）
- **trace**: 上流 = NFR-3 charter v0.4 §3 横断原則（HELIX 同様、壊す変更をしない） ／ 下流 = AC-72-1 AC-72-2 AC-72-3 AC-72-4 AC-72-5 FN-702 CMP-05 ／ スライス = S0

## FR-73 例外支出台帳（spend_ledger）

- **入力**: charge記録要求（entry_type='charge', external_operation_row_id, amount_minor>0, currency='JPY', purpose, approval_id, occurred_at。service/task_idは外部操作行から取得）／reversal記録要求（entry_type='reversal', reverses_spend_ledger_id, amount_minor>0, currency='JPY', purpose, approval_id, occurred_at。task_type='spend_correction'・parent_task_id=元charge.task_id・input_json.original_spend_ledger_id=元charge.idの別taskへ束縛）／月間累計の照会要求（対象月）
- **出力**: spend_ledger仕訳行（entry_type=charge|reversal。例外利用1件=charge 1行、取消しは元chargeに対するreversal最大1行）／月間累計額（NFR-6 の上限判定入力）／拒否時: SpendRecordIncomplete／DuplicateSpendEntry 例外／設計境界: S1詳細設計未着手（専用spend ledger component/DUへ再降下必須。既存CMP-13/DU-23は計測専用で代用しない）
- **事前条件**: chargeはexternal_operation_row_idが指すexternal_operations行がexecution_mode='actual'・effect='write'・policy_category='approved_paid_operation'・status='confirmed'で、対応operation_logが確定済み／chargeのservice/task_idがexternal_operations行と一致し、approval_idは同じtask・操作へ束縛済み／reversalはreverses_spend_ledger_idが未取消しのentry_type='charge'行を指し、同一loop_runの別task（task_type='spend_correction'・parent_task_id=元charge.task_id・input_json.original_spend_ledger_id=元charge.id）とそのdecision=approved approvalへ束縛済み
- **事後条件**: Seedance等のconfirmed approved_paid_operationが全件entry_type='charge'のspend_ledgerに存在する（記録なしの有償操作0件）／全仕訳でamount_minor>0・currency='JPY'が保証され、無料・amount=0・手動charge・FX通貨はspend_ledgerへ混入しない／月間純額がSUM(CASE WHEN entry_type='charge' THEN amount_minor ELSE -amount_minor END)のSELECTだけで算出できる
- **不変条件**: confirmed有償actual write（policy_category='approved_paid_operation'）とcharge行はexternal_operation_row_idで双方向exactly-one（台帳なし支出・孤児chargeとも0 — BR-F1）／chargeだけexternal_operation_row_id NOT NULL UNIQUE・reverses_spend_ledger_id NULL、reversalだけexternal_operation_row_id NULL・reverses_spend_ledger_id NOT NULL UNIQUEで元chargeを指す。provider external_operation_idは任意の補助属性にすぎない／reversalは元chargeとamount_minor/service/currencyが完全一致し、1 chargeにつき最大1行。台帳行のUPDATE/DELETEは禁止し、訂正はDBが元chargeへ構造束縛を検証した別approved spend_correction taskによるreversal追加だけで行う
- **状態遷移**: なし
- **正常動作**: chargeは有償APIのexternal_operations行がactual write・policy_category='approved_paid_operation'としてoperation_log triggerでconfirmed化した時だけ、その内部idをexternal_operation_row_idへNOT NULLでINSERTする。reversalはtask_type='spend_correction'・parent_task_id=元charge.task_id・input_json.original_spend_ledger_id=元charge.idを満たす別approved taskから未取消しchargeを参照し、元と同額・同service・JPYでINSERTする。provider IDは同一性に使わない。月間純額はUTC半開区間に対しSUM(CASE WHEN entry_type='charge' THEN amount_minor ELSE -amount_minor END)で集計する。
- **拒否・異常動作**: chargeのexternal_operation_row_id/amount/purpose/approval欠落、参照外部行不在、actual/write/approved_paid_operation/confirmed不一致、task/service不一致、reversalの元charge不在・既取消し・同額/同service/JPY不一致・correction task/approval欠落はINSERT前拒否。同一external_operation_row_id又はreverses_spend_ledger_idの再INSERTはUNIQUEでDuplicateSpendEntry。amount_minor<=0、currency!='JPY'、FX、無料・手動chargeを拒否し、台帳記録失敗の有償操作は成功扱いにしない。UPDATE/DELETEも常時拒否する。
- **境界動作**: amount_minor=0の無料利用と手動分類はspend_ledgerへINSERTせず、process usage又は別の手動会計分類へ記録する。reversalは元chargeと同額全額取消しだけで部分取消し不可。月跨ぎcharge/reversalは各occurred_atのUTC月に符号付き計上する。provider IDがNULLでも内部row IDで一意性を保つ。
- **再試行・再開・復旧**: charge前クラッシュ時は元writeのsent状態を別の実外部read行＋operation_logで照合し、元writeをoperation_log triggerでconfirmed化した後にexternal_operation_row_idで台帳記録を再開する。chargeは内部row ID UNIQUE、reversalはreverses_spend_ledger_id UNIQUEで各1行に収束し、provider ID欠落時も挙動は変わらない。
- **人間判断／escalation**: あり（例外支出の事前承認 = approval_id 参照。記録・集計は全自動）
- **副作用**: spend_ledger INSERT（charge又はreversal。UPDATE/DELETEなし）
- **冪等性**: chargeはspend_ledger.external_operation_row_id UNIQUE、reversalはreverses_spend_ledger_id UNIQUEを各冪等キーとする。同一actual writeの再記録と同一chargeの再取消しは各1行へ収束し、集計はpure（同一台帳→同一純額）。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **証跡**: spend_ledger行そのもの（entry_type・chargeのexternal_operation_row_id又はreversalのreverses_spend_ledger_id・サービス・正額・用途・タスク/approval参照）／operation_log証跡（同じexternal_operations.idへexternal_operation_row_idで束縛。provider external_operation_idは任意）
- **使用テーブル・正本**: w: spend_ledger／r: tasks（task_id FK）／r: approvals（approval_id FK）／r: external_operations（操作確定の照合）／r: config（spend_cap_monthly — 上限判定は NFR-6）
- **外部依存**: 有償 API サービス（Seedance 等 — 支出の発生源。台帳自体は外部呼出しなし）
- **設定値**: config.spend_cap_monthly（C・暫定既定値 5,000 円/月 — 上限判定は NFR-6 側） ／ **固定値**: entry_type = charge | reversal（閉集合）／currency = JPYのみ（FX換算規則未定義のため他通貨fail-close）／amount_minor > 0（符号はentry_typeから導出）
- **trace**: 上流 = BR-F1 REQ-027 NFR-6 ／ 下流 = AC-73-1 AC-73-2 AC-73-3 ／ スライス = S1
