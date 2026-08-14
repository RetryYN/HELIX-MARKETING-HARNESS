---
artifact_id: AUTH-REQUIREMENTS-GATES
lifecycle_status: draft
slice: cross
---

# 要件整合ゲート台帳 v0.2

> status: **active**（2026-08-01 分割改訂）。実体は [tools/gates/](../../tools/gates/) の工程別モジュール、
> 入口は `tools/gates/run_all.py`（[scripts/validate_requirements.py](../../scripts/validate_requirements.py) は互換ラッパー）。
> CI（Docs CI / requirements-gates ジョブ）で push/PR ごとに fail-close 実行。1 件でも FAIL = CI 赤。
> ゲートの追加・変更はモジュールと本台帳を同時に更新すること（G-WIRING が検査）。
> 件数の正本は [baseline.json](baselines/baseline.json) の `gate_count`（散文に件数を書かない）。

## モジュール構成（PO 指示 §7）

| モジュール | 責務 |
|---|---|
| `common.py` | パス正本・結果レジストリ・最小 JSON Schema 検証器・遅延ロード context |
| `authority.py` | artifact manifest・物理構造・正本確定・旧体系隔離・現在地の一意性 |
| `requirements.py` | 分母・ID 一意性・構造化契約・AC 極性・上流戦略ループ |
| `traceability.py` | AC↔TC 双方向・全区間 trace・粒度ゲートの mutation 自己検査 |
| `architecture.py` | DDL 同期／適用・状態機械の決定性・戦略正本の DB 強制・CMP/ITC 台帳・設計書実体 |
| `detailed_design.py` | DU 台帳・API 実装契約・DbC・エラー型・DB 参照・API 単位 UT・空洞禁止 |
| `test_pairing.py` | 文書ペア・テストファイル対応・S0.1 着手の自動検出・skip/coverage の逃げ道封じ（静的 AST） |
| `test_reality.py` | pytest 実行結果（outcome）の取り込み・動的 skip の検出・間接束縛の着手検出・対象 UT の nodeid 単位突合 |
| `worksets.py` | S0.1 依存 Workset（実装レーン）の分割・依存導出・スコープ一致・Workset 単位の着手強制とラチェット |
| `semantic_refs.py` | 構造化参照（table/column/state/event/kind/error/api）の実在検査、状態遷移4タプルの正準照合とFR/SR/NFR→AC→TCC被覆 |
| `requirement_discovery.py` | coverage 開始点以後の要件発見 event の schema、append-only prefix、契約変更 coverage、lifecycle、承認、secret／mutation 境界 |
| `review_binding.py` | レビュー成果物の対象コミット・digest・後続レビュー束縛 |
| `template_alignment.py` | HELIX-HARNESS 固定コミットの read-only 対応表、Python-native 開発環境、L2 5 点セットの整合 |
| `baseline.py` | デグレ検出（ラチェット）・件数表記の同期・ゲート配線と分割規律 |
| `run_all.py` | 実行順序・終了コード・`--update-baseline` |

## authority — 権威層（PO 指示 §1〜§4）

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-REQ-AUTHORITY | 既存9正本、IRの非二重正本、refinement単位承認、manifestのL0〜L6一括`revalidation_required`、revising中の実装禁止、frozen revision限定cutoverを検査する | charterを含む旧confirmed成果物の誤実装、生成IRの正本化、一括承認、未凍結要求の実装入力化 |
| G-REQ-COMPATIBILITY-AUTHORITY | 古い`functional/requirements.json`をread-only revalidation viewに固定し、契約正本又は実装入力として扱わせない | 同一FR IDを別slice・trace・責務で二重正本化 |
| G-AUTHORITY-MANIFEST | artifact-manifest.json が schema 適合（必須 18 項目・追加禁止）で 1 件以上を登録 | 権威正本の不在・野良フィールド |
| G-MANIFEST-UNIQUE | artifact ID が一意で、同一 canonical_path を複数 artifact が主張しない | 正本の多重主張（どれが正か決まらない） |
| G-MANIFEST-PATHS | canonical_path／view_path／previous_paths が実在**かつ git 管理下**で、view は `views/` 配下、旧パスは残存しない | 幽霊参照・移行漏れ・生成物の混在 |
| G-MANIFEST-PAIR | pair_artifact_id が実在し双方向に対称 | 片肺ペア（HELIX pair gate 違反） |
| G-MANIFEST-RELATION | supersedes（完全置換）の対象が authority_status=superseded／archived であり、supersedes／extends_artifact_ids／depends_on_artifact_ids の参照先が実在し、自己参照・同一参照の二重宣言・循環参照がない | 現役成果物を置換扱いにした継承の偽装・存在しない旧 ID への幽霊参照 |
| G-MANIFEST-DOMAIN | domain が小文字 kebab-case の**業務領域**で、slice 名（S0 等）・階層名（L4 等）・自身の slice 値と一致しない | 分類軸の混同（いつ作るか／どの工程か／何の領域か が 1 フィールドに潰れる） |
| G-MANIFEST-STATUS | lifecycle_status=confirmed の artifact は内容束縛 digest を持ち、その digest が approvals.md に実在（Markdown は frontmatter を**含む全文**の digest — ゲートが正本として読む slice／traces を承認束縛の外へ出さない） | 内容に束縛されない confirmed 僭称 |
| G-MANIFEST-DIGEST | review_digest が現内容とレビュー成果物の両方に一致 | レビュー済みを名乗るすり替え |
| G-MANIFEST-COVERAGE | 現役階層（L0〜L6）の全成果物が manifest に登録済み | 未登録成果物の confirmed 化（権威の外での正本化） |
| G-MANIFEST-ARCHIVE | archive／superseded を現役 artifact の canonical にできない | 凍結物の実装入力化 |
| G-LAYER-PLACEMENT | docs 直下は 00-authority／L0〜L6／archive のみ（旧階層・野良ファイルの残存なし） | 工程階層の崩壊 |
| G-VIEWS-GENERATED | `views/` は生成 MD のみ（GENERATED 宣言必須）、生成物が views 外に出ない | 手編集ビュー・正本と生成物の混在 |
| G-CANONICAL-FORMAT | authority_format が canonical の形式と一致し、canonical Markdown は人間承認正本型（charter／policy／adr／audit-record／design-doc／requirement-doc／test-design）に限られ、生成 MD の canonical 混入・canonical と view の二枚看板・未登録の生成 MD・GENERATED 宣言のない登録済み view がない | JSON 正本を持つ成果物の MD 正本化（どちらが正本か決まらない） |
| G-STATUS-CONSISTENCY | authority_status（現役位置）、lifecycle_status（内容成熟度）、applicability_status（現要求への適用可否）、implementation_inputを分離する。revising中のL0〜L6はrevalidation_required又はproposal_only、全artifactのimplementation_input=falseを強制し、confirmed のみ approval_digest を持ち、markdown正本のfrontmatter・本文status行がmanifestと一致する | 旧confirmed又は未承認candidateを現要求・設計・実装入力として誤用、draft文書のconfirmed相当扱い、statusの意味衝突 |
| G-SLICE-PLACEMENT | L6 機能設計の物理ディレクトリ・manifest.slice・frontmatter.slice・traces 先 FR／SR のスライスが一致し、本文の要求参照が実在し、後続スライスへの言及が forward_refs に過不足なく宣言され（コードフェンス内は走査対象外）、S0 の DU が後続スライスの機能設計を入力にせず、機能設計 frontmatter の `dus` が du-contracts の feature_design と**双方向**一致し、S0 の DU については当該文書の本文が その DU か AC を実際に扱う（S1 以降の DU は⑤改訂で採番し直す段階のため内容突合の対象外） | 本文と配置のスライス不一致・S0 への S1 実装の混入 |
| G-CANONICAL-UNIQUE | 現役階層に内容が同一のファイルが 2 箇所以上存在しない | 同一正本の二重配置 |
| G-ARCHIVE-ISOLATION | 現役導線（README/CLAUDE/AGENTS/CI/スクリプト/現役 MD リンク/現役 JSON 値）が archive・superseded を入力として参照しない | 旧体系の復活・二重正本 |
| G-CONFIRM | status: confirmed を名乗る文書が approvals.md に承認行を持つ | freeze 偽装 |
| G-CONFIRM-DIGEST | confirmed 文書の現内容 sha256[:12] が同一 (対象, 版, confirmed) の承認行に存在 | 内容に束縛されない空承認 |
| G-CANON-CONFIRMED | 契約 JSON 正本 9 本（BR/FR/SR/NFR/AC/TC/CMP/DU ＋ implementation-units）が confirmed＋approved_at／authority／approval_digest を持ち、digest が正準化内容と一致し approvals 行が実在 | 正本の status 僭称 |
| G-LEGACY-ARCHIVED | 旧正本（ac.json／verification.json／utest.json）が archive のみに存在し現役階層から消失 | 旧 AC/TC/UT 体系の二重正本化 |
| G-CURRENT-STATE-SINGLE | README／CLAUDE.md の現在地が正本行ごとに一意、他経路の確定表現が存在しない | 現在地の分裂・未決事項の確定表現 |

## requirements — 要求・要件層

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-JSON | 現役階層の全 JSON が構文的に妥当 | 壊れた正本 |
| G-CNT-BR/REQ/FR/NFR/FN/BRM/MR/WF | BR/REQ/FR は JSON 件数 = MD 件数、固定設計集合は各正本分母と一致（縮小は baseline ratchet が拒否） | MD↔JSON の同期漏れ・分母のサイレント変更 |
| G-CNT-CONTRACT | AC/TCC は承認済み最小分母以上、API/API_UT は設計正本分母と一致し、縮小は baseline ratchet が拒否 | 分母のサイレント縮小・新規要件追加の阻害 |
| G-HISTORICAL-COUNTS | 旧 AC/TC/UT 分母が baseline の historical_counts のみに存在し、現役分母・現役文書に混入しない | 旧体系の分母復活 |
| G-UNIQ-* | BR/REQ/FR・NFR/FN の ID 重複ゼロ | ID 衝突 |
| G-SUBSTANCE | 全エンティティに 8 文字以上の本文実体を要求し、媒体要求の規範 `items[].text` にある既知の判定不能量・失効確認済み仕様と同一媒体内のstructure分岐を拒否 | 空・スタブ本文の完了僭称・AC化不能な頻度表現・外部仕様の陳腐化・媒体内二重仕様 |
| G-SRC-FRESH | br-media 各媒体の structure_checked が 90 日以内 | 出典腐敗 |
| G-POC-EXIT | PoC が出口 2 軸 schema に適合、confirmed には promotion_strategy 必須 | PoC の独り歩き |
| G-REQ-CONTRACT | BR 構造化契約が schema 適合で現役 BR 全件・12 要求群を被覆し、REQ 参照が実在し、生成ビューが同期 | 1 行要求の温存・手編集ビューの乖離 |
| G-FRSR-CONTRACT | 現役 FR／SR 全件に 18 観点の実行契約が schema 適合で存在し、tables／state_transitions が DDL・遷移正本と一致 | 責務 1 行要件の温存・正本との乖離 |
| G-NFR-MEASURABLE | 全 NFR11 に計測契約と `verification_aspects` を要求し、NFR→AC→TCC の実在ID接続に加えて意味単位集合の完全一致を強制する。`SQL:`タグ付き契約SQLはnamed bindを与え、空SQLiteへ正準DDLを適用した上でprepareして表・列・構文・placeholderを検査する | 測定方法のない閾値・IDだけ接続した意味上の片肺・実在しない表/列や擬似placeholderを含む検証手順 |
| G-AC-COVERAGE | AC 検証契約が schema 適合・ID 一意・target 実在で、S0 の全 FR/SR に AC ≥1 | AC なし実装対象 |
| G-AC-POLARITY | S0 の各 FR/SR が正常／拒否／境界復旧の 3 極性を AC か理由付き N/A で被覆 | 正常系だけの受入 |
| G-HUMAN-JUDGE | 全 FR/SR 契約に人間判断点の明示 | 人間判断点の暗黙化 |
| G-INVARIANT-TRACE | S0 の各不変条件が invariant_ac_map で固有の負方向 AC に対応（使い回し禁止） | 破られても検出されない不変条件 |
| G-GWT | AC 契約全件に非空の Given/When/Then | 機械検証できない AC |
| G-TC-REJECT | fail-close 拒否系 TC が 7 件以上 | 拒否経路の検証欠落 |
| G-TC-SLICE | 全 TC が既知スライス語彙（S0/S1/S2/S3+）に属し、S0 の TC が実在して AC を参照 | スライス外の宙吊り TC |
| G-WF-CONTRACT | WF 実行契約の対象が WF 台帳に実在し、全件に step 定義がある | 実行契約なき WF・幽霊 WF |
| G-ENV-CONTRACT | 環境契約が Docker WP を唯一の実書込み先とし、本番 WP・GA4 の書込み禁止を宣言 | 本番への誤書込み経路 |
| G-STRAT-BRIEF | brief 契約が完全で DDL が下位 run に brief id/digest 保持を強制、開始ガードが有効 brief を要求 | brief なしの下流開始 |
| G-STRAT-TRACE | run→brief→choice→VH→SEG→evidence の trace 必須＋trace 欠落 fixture 拒否＋変異 schema の検出自己検査 | 宙に浮いた戦術 |
| G-SEGMENT-CONTEXT | 状況ベースセグメント（時間・空間・制約・進行状態・代替行動）必須、人口統計のみ fixture を拒否 | ペルソナ型セグメントの正本化 |
| G-OBS-INTERPRETATION | 観測事実と解釈の分離、learning/failure packet 二分、failure への因果解釈捏造を拒否 | 観測と AI 解釈の混濁 |
| G-LEARNING-TRACE | 全 TLP が run・brief digest・evidence へ接続し UNIQUE＋整合トリガが DDL に実在、未接続 fixture を拒否 | 接続のない学習 |
| G-NO-DIRECT-STRATEGY-MUTATION | 上流正本への UPDATE/DELETE を実 DML で拒否実証＋直接更新禁止の宣言 | 下流からの戦略正本書換え |
| G-REVISION-EVIDENCE | revision の根拠／反証/信頼度／対象版必須、単一・重複根拠の accepted を拒否、新版必須 | KPI 値の直接戦略変換 |
| G-STRATEGY-VERSION | 全上流モデルが version 必須＋supersedes_id 定義（変異検出自己検査込み）、DDL append-only を実 DML で実証 | 上流正本の上書き |
| G-MEDIA-ROLE | 役割台帳 12 語彙以上＋brief の役割/認識変化必須＋台帳外役割 fixture を拒否 | 媒体名の役割僭称 |
| G-CONTENT-VALUE-DEFINITION | コンテンツ企画 5 宣言契約＋宣言欠落 fixture を拒否 | 認識変化を宣言しない量産 |
| G-STRAT-PAIR | SR19／SCM10／AC-SR6 の双方向カバー＋戦略 4 文書の相互 pair＋全戦略ゲートに拒否系 STC | 片肺の戦略層 |

## architecture — 構造・DB 層

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-DDL-SYNC | ddl.sql が s0-contract の DDL ブロックと一致 | 正準 DDL の二重化 |
| G-DDL-APPLY | DDL が空 SQLite へ適用でき FK/integrity が通り、テーブル 25・トリガ 39。実 external read/write と operation_log の双方向1:1、prepared→sent→final、final不変、mock/dry-run/pre-call行0、published_urlのローカル行束縛、有償操作とchargeの原子化を実DML mutationで検証 | 実行不能なスキーマ・孤児/重複外部証跡・結果改竄・非原子finalize・台帳外支出 |
| G-DESIGN-PHYSICAL-COUNT | 現役文書・契約 JSON・テスト関数名が主張する物理数（テーブル総数・トリガ本数）が**実 DDL から導出した数**と一致し、部分集合の本数を数値で書いていない（監査記録・承認ログ・Workset の UT rename 履歴は当時の事実を保存する履歴なので対象外） | 設計文書の物理数が実スキーマから乖離（11／14 本のような化石表記の温存） |
| G-PLAYBOOK-VERSION | playbook修復を実DMLで検査し、破損版ごとにrepair task 1件、attempt=1/retry=0、版の連続系譜、successor INSERT失敗時のatomic rollback、旧版内容・retired版・削除の拒否を確認 | 再起動や並行通知での多重修復・攻略地図の上書き・現役版消失 |
| G-TASK-TYPE-REGISTRY | DDL が意味分岐に用いる内部 `task_type` 集合と L1 `task-types.json` の `internal=true` 語彙を完全一致で照合 | 未登録・誤記・失効した内部task typeによる要件とDB制約の分離 |
| G-EVK | evidence kind 10 種が JSON 契約と DDL CHECK で同一集合 | 証跡語彙の乖離 |
| G-TRN-ENT / G-TRN-ST | 遷移 entity が loop_runs/tasks、from/to が DDL enum 内 | 実装不能な状態機械 |
| G-TRN-UNIQ/REACH/TERM/GUARD | (entity, from, event) 一意・全状態の到達可能性・終端からの遷移不在・全遷移に非空ガード | 非決定的な状態機械 |
| G-S0-CNT / G-S0-SET | S0 の fn_ids が 25 件・重複なし・function-list の slice=S0 と一致 | スコープのサイレント増減 |
| G-TRC-BR | trace が現役 BR 全件をカバー | トレース断絶 |
| G-BRIEF-TRANSITION | brief の status 遷移を実 DML で検査（draft→active／active→superseded・retired のみ通過、superseded/retired からの復帰・draft 逆行は ABORT） | 戦略正本の状態逆行（PO 指示 §5） |
| G-BRIEF-VALID-UNTIL | valid_until の延長（後ろ倒し・NULL 化）を拒否し短縮のみ許可 | 有効期限の無制限延長（新版発行の回避） |
| G-TLP-JSON-PREDICATE | TLP の空配列判定が `json_array_length()`（文字列比較の不在＋空白入り空配列の実 DML 実証） | 文字列比較による誤判定（PO 指示 §5） |
| G-CMP-CNT/UNIQ/FN | CMP 台帳が 13・ID 重複ゼロ・S0 25 FN を重複なく完全被覆 | 設計漏れ・二重責務 |
| G-ITC-CNT/UNIQ/CMP/REJ/UPD | ITC 16・ID 重複ゼロ・全 CMP 双方向カバー・拒否系 ≥7・全件 S0.x 割当 | 片肺（総合テスト対のない設計） |
| G-CMP-INTERFACE | 全 CMP/SCM 23 に 11 観点の設計契約が schema 適合で存在し、参照する独立設計書が実在 | interface なきコンポーネント |
| G-DESIGN-SUBSTANCE | 独立設計書 6 本と機能別設計 11 本が実体（≥50 行・≥3 節・trace） | 参照だけ存在する空設計書 |
| G-BASIC-DESIGN-EXIST | 基本設計②がヘッダに pair 宣言を持つ | ペア宣言の欠落 |
| G-MIGRATION-RULES | migration 規則が expand/backfill/contract/rename 禁止を実体つきで定義し昇格手順を持つ | 破壊的移行の温存 |

## detailed_design — 詳細設計層

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-DU-CNT/UNIQ/CMP/FN | DU 台帳が 23・重複ゼロ・全 CMP を被覆・S0 25 FN を重複なく完全被覆 | モジュール分解の漏れ |
| G-DU-API | 全 DU に実装契約（公開 API 署名・DTO・状態遷移・tx 境界・冪等性・競合制御）が schema 適合で存在し module が台帳と一致 | API なき DU |
| G-DU-DBC | 全公開 API に precondition／postcondition | 契約なき API |
| G-DU-ERROR | 全 API の raises 型がエラー分類正本に掲載 | 台帳外エラー型の発明 |
| G-DU-DATA | 全 DU の DB read/write が DDL の実在テーブルのみ | 存在しないテーブルへの設計参照 |
| G-L6-IMPLEMENTATION-TRACE | S0 L6 機能設計の責務（第 9 正本 `docs/L6-feature-design/S0/implementation-units.json`）が専用 schema（追加プロパティ禁止）に適合し、`api_ref`（API 安定 ID **1 件**・配列禁止）と `clause_refs`（当該 API の契約節 ID）で**構造接続**している。`ac_refs` の AC が `verifies_clause_refs` で、`ut_refs` の UT が`apis[].ut[].clause_refs` で、**同じ契約節**を参照していることを双方向に要求し、文書の trace 先や DU が同じだけではPASS にしない。API 名・テスト名・日本語語彙の部分一致は接続の根拠にしない（語彙一致検査は廃止）。同一 API の契約節を複数責務が重複主張することを禁止し、S0 文書が担う DU は全 API・全（契約節を検証する）AC が責務へ接続していることを要求する。さらに**全 API 契約節**が AC 被覆か理由付き `na_reason` のいずれかを持ち、AC 側も契約節を検証しない場合は`clause_na_reason` を要求する（被覆と理由は排他）。「準用」等の借用表現による trace 代替は L6 全体で拒否する。さらに `na_reason` は閉じた分類語彙（`呼出側義務:`／`配線時保証:`／`他 API で検証:`／`受入基準未設定:`）で始まることを要求し、AC が 1 節も検証していない API は `docs/L6-feature-design/S0/uncovered-apis.json` へ**明示登録**され（登録集合と実態が厳密一致）、解消時も `resolved_items` の append-only 履歴から導出した API 集合について、exactly-one AC の `api_observation_assertions`（API固有fixture／action／observation／assert）を要求する。action は当該公開API名を含み、節IDだけの追記・別API assertionのコピー・解消履歴の件数不一致を拒否する。その件数・AC 被覆節数・実装単位数は baseline のラチェットで保護する。さらに各 API は `verification_level`（acceptance／unit／integration）を持ち、内部（unit・integration）は `internal_reason` と閉じた `internal_reason_code`（startup-wiring／read-only-accessor／internal-delegation）が必須で、**postcondition・raises の全契約節がUT の `clause_refs` へ直接接続**していなければならない。acceptance から内部分類への格下げは baseline のラチェットが拒否する。`na_reason` の閉じた語彙は `呼出側義務:`／`配線時保証:`／`他 API で検証:`／`単体検証:`／`受入基準未設定:` で、`単体検証:` は当該節が UT の `clause_refs` に実在する場合だけ名乗れ、UT が検証している節に `受入基準未設定:` を書けない。api_id・clause_id の一意性も検査する | 責務が API 契約節まで降りていない／節IDだけで意味被覆を名乗る／API固有観測が反証不能／契約節が誰にも検証されないまま残る |
| G-UNCOVERED-API-UPDATE | 未被覆 API 台帳 `docs/L6-feature-design/S0/uncovered-apis.json` の解消先が`resolution_update`（updates.json の更新語彙）で宣言され、DU 台帳の `fn_ids` → `updates.json` から**機械導出**した更新と一致する。slice（S0／S1／later ＝ いつ作るか）を解消先に書くこと、および `resolution_slice` の残存を拒否する。FN が複数更新に跨る／どの更新にも属さない DU も更新境界の不定として落とす | slice と update の混同で「どの更新で閉じるか」が決まらないまま設計クロージャーを名乗る |
| G-UPDATE-DESIGN-CLOSURE | 更新（updates.json の S0.1／S0.2／S0.3）ごとの設計状態`docs/L6-feature-design/S0/update-closure.json` を検査する。通常基準のclosedは未被覆API=0・全契約節被覆・実装単位実在を要求する。要求基準が`revising`の間は、旧confirmed設計の構造実態自体がclosedであることを保持しつつ、宣言は全更新`revalidation_required`、`implementation_authorized=false`、理由付きでなければならない。どちらのモードも`current_state_claim`とREADME/CLAUDEを1回ずつ一致させる | 旧構造被覆のPASSを新要求への設計完了・実装許可と誤認する |
| G-S0-DESIGN-COMPLETE | 通常基準ではS0.1／S0.2／S0.3の導出状態がすべてclosedであることを要求する。`requirements_baseline_status=revising`では設計完遂を意味せず、旧設計が`revalidation_required`、実装未許可、かつ旧構造被覆に新たな穴がないことだけをfail-close確認する | 改訂中モードのPASSを設計完遂や実装可能と誤認する |
| G-API-UT | **API 単位**で UT ≥1・api.ut ⊆ trace.ut・宙吊り UT ゼロ・参照テスト関数が実在・スタブは設計リンク（DU＋API 名）を宣言 | UT なき API・匿名スタブ |
| G-NO-HOLLOW-DESIGN | 全契約正本にプレースホルダ（TBD/TODO/仮置き等）が存在しない | 空洞設計の温存 |

## traceability — トレーサビリティ

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-TRACE-BIDIR | TC 検証契約が schema 適合で、全 AC と TC が双方向に接続（AC 無 TC・宙吊り・非対称 = 0） | 検証の届かない AC |
| G-CHAIN-BIDIR | BR→REQ→FR/SR→AC→TC を全件双方向突合。`design_status=requirements_defined` を明示した S1+ 要件だけ L3 で停止でき、それ以外は CMP→DU→API→UT まで必須。S0 の全 AC/TC は最低 1 DU へ割当 | 鎖の片方向化・既存要件の CMP/FN 削除による降下逃れ・要求定義と設計クロージャーの混同 |
| G-DESCENT-SELFTEST | 粒度ゲート群（polarity／DbC／DATA／BIDIR／CHAIN／invariant／API-UT）の**検出関数そのもの**へ変異データを投入し検出を毎回証明 | 名目だけの粒度ゲート |

## semantic_refs — 意味整合

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-SEMANTIC-REF | 全 FR/SR/AC/TC/CMP/DU の semantic_refs が正本語彙に実在し、宣言済み `transition_refs` の `(entity, from, event, to)` が transitions.json に実在。FR/SR/NFR の遷移集合 = 対応 AC の和集合、各 AC の遷移集合 = 対応 TCC の和集合 | entity を無視した event 誤用（tasks.fatal_failure 等）・要求→AC→TCC 間の遷移意味欠落／過剰 |
| G-COLUMN-REF | table_refs／column_refs が ddl.sql の実在テーブル・実在列 | 列名のドリフト |
| G-STATE-EVIDENCE-CONSISTENCY | FR/SR/AC/TCC の状態遷移拒否・成立は state_transitions で表現し、operation_log は `external_operations` と effect（read/write）・`external_operation_row_id`・request束縛を持つ実外部I/Oに限定。mock/dry-run/pre-call拒否、「DB変更なし」と拒否証跡INSERTの自己矛盾を拒否 | 証跡種別の混同・外部表参照だけの偽装・拒否契約の自己矛盾 |

## test_pairing — ペアと test-first の実体化（PO 指示 §6）

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-PAIR-HDR | ①要件定義側 5 文書のヘッダに pair 行、③検証設計側にも対象列挙（対称） | 片方向ペア |
| G-PAIR-MANIFEST | ②↔④・⑤↔⑥ のペアが manifest（pair_artifact_id）と文書ヘッダの両方で双方向 | ペアの正本が二重化・非対称 |
| G-UT-FILE-UNIQ | DU↔テストファイルが 1 対 1・衝突なし | テストファイル混線 |
| G-UT-FILE-EXIST | du-contracts／STC-I（S0.1）が宣言する test_file が実在 | 宣言だけのテストファイル |
| G-IMPL-START-DETECT | S0.1 着手の**自動検出**（src/helix への実装追加・S0.1 PLAN の in_progress・DU-01〜12 の API 実装）と宣言（skip-budget）が一致。実装の有無は AST 判定（`__init__.py`・条件付き def・lambda 代入も実装とみなす） | 宣言を false のままにした着手（手動フラグ依存の逃げ） |
| G-UT-NO-ESCAPE | 着手後は対象 UT に skip／xfail／NotImplementedError／空 assert を残せない。AST 判定（module-level skip・`pytestmark`・関数内 `pytest.skip()`／`xfail()`・別名 import／モジュール再代入／`getattr` 経由の呼出し・定数 assert）。skip 判定は import 解決＋別名代入の固定点でフレームワーク起点の完全パスへ解決し、pytest／unittest 由来に限定する。**空 assert = 検証行為ゼロ**であり、`pytest.raises`／`pytest.warns`／`assert_*` メソッド／`pytest.fail()` は検証行為として通す（計上は到達しうる文のみ — 入れ子関数内・`if False:` 配下は数えない）。別名は star import・タプル／注釈付き／セイウチ代入・多段再代入まで固定点で解決する。残る限界は `__import__`／`importlib` の動的 import のみで、着手後の coverage 下限 80% と `scripts/check_skip_budget.py` の実測 skipped 件数ラチェットを backstop とする。**動的 import の限界は test_reality の実行時ゲート（G-UT-DYNAMIC-SKIP／G-UT-PER-TEST-OUTCOME）が実行結果で塞ぐ**（本ゲートは静的側の検査として残す — 二重化であって代替ではない） | skip を red と称する test-first の形骸化／逆に正当な拒否テストを落とす偽陽性 |
| G-COVERAGE-RATCHET | coverage 下限が着手後 80% 以上・親コミット比で低下しない。比較元は `committed_baseline()`（親コミットの baseline・旧パス遡及）に一本化し、親を解決できない場合は fail-close | 網羅率の静かな引き下げ／比較元不能を素通りさせる fail-open |
| G-PLAN-S0 | S0.1 PLAN が実在し status 語彙・対象 DU（01〜12）が正しく、`preconditions[]` の各要素が object・`description` 40 字以上・`status=met` は実在ゲート ID（本番モジュールが emit する ID 集合への完全一致）か実在 commit SHA の `met_by` 必須。**PO 指定の 4 前提条件（`runtime-ut-outcome-gate`／`dynamic-import-skip-detection`／`impl-start-detect-indirect-binding`／`per-ut-executed-and-passed`）は必ず存在し、`met` にできるのは対応する専用ゲート（G-UT-RUNTIME-OUTCOME／G-UT-DYNAMIC-SKIP／G-IMPL-START-BINDING／G-UT-PER-TEST-OUTCOME）を本番が emit した場合だけ**（無関係な既存ゲート ID・任意の commit SHA では met にできない）。`status` が `planned` 以外（in_progress／done）と着手の自動検出は、前提条件が全て `met` でない限り落ちる（`planned → done` 直行も塞ぐ）。`done` は対象 DU の API が実装済みであることを併せて要求する（実装ゼロの完了宣言を拒否） | 着手前提条件の忘却／前提未充足のままの着手／preconditions の削除・骨抜き |
| G-S0-TEST-REALITY | 着手後に skip を残したまま green を名乗れない（G-UT-NO-ESCAPE と連動） | 実 red→green の回避 |

## test_reality — 実行時テスト実体（S0.1 着手前提条件 4 件）

> 入力は `scripts/collect_test_outcome.py` が `pytest --junitxml` から正規化した
> `reports/test-outcome.json`（HEAD へ束縛・CI 成果物 `pytest-outcome` として保存）。
> AST 検査が原理的に判定できない「実際に実行されたか」を実測で補う層であり、
> test_pairing の静的ゲートを**置き換えない**（二重化）。

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-UT-RUNTIME-OUTCOME | pytest の実行結果が CI 成果物として生成され、ゲートの入力になっている。レポートは schema（`helix.test-outcome/v1`）・生成元（固定パス `reports/junit.xml` の実在と sha256 一致）・**HEAD への commit 束縛**・nodeid の非重複・outcome 語彙を満たし、さらに**収集スクリプトを同じ junit で再実行した結果と nodeid→outcome・totals が完全一致**する（手書き JSON を拒否）。`reports/` は git 追跡下に置けない（レポートの有無に関係なく検査）。CI 配線は YAML を構造解析し、同一 job の**実行されるコマンド列**が `pytest --junitxml` → 収集 → `run_all.py` の順であること（コメント・`echo`・`if: false` は配線と認めない）、python-ci は両ファイルを `if-no-files-found: error` で upload することを要求する。`xfail_strict = true`（TOML 解析で真偽値まで検査）と、S0.1 着手後のレポート存在も必須 | 別コミットの outcome の貼り付け・手書きレポート・成果物の commit による固定化・収集を CI から外して実行時ゲートを空にする逃げ・xpass の passed 誤認 |
| G-UT-DYNAMIC-SKIP | 対象 UT の skip／xfail／xpass を**実行結果**で検出する（`__import__`／`importlib` 経由の動的 skip・実行時条件による skip を含む）。AST 側（G-UT-NO-ESCAPE）が検出していない skip は「静的に不可視」として別枠で報告する。着手後は 1 件も残せない（未着手は猶予するが実測件数を常に出力する）。収集自体からの除外（outcome に現れない）は G-UT-PER-TEST-OUTCOME の欠落判定が担う | 静的検査を素通りする skip で test-first を形骸化する |
| G-IMPL-START-BINDING | `def` を書かない**間接束縛**による S0.1 実装着手を検出する（`functools.partial`／`partialmethod`・デコレータ適用の代入・別名代入・import の再エクスポート・属性代入・添字（レジストリ）登録・`globals()` 注入・辞書一括登録・2 引数の登録関数・`setattr(obj, "name", impl)`）。実装を指す名前は固定点で伝播し、多段束縛（`tmp = partial(real)` → `<API> = tmp`）も辿る。シグナルにするのは **DU-01〜12 の API 名への束縛**だけで（非 API の内部別名は偽陽性として除外）、`impl_start_signals` へ合流して skip 上限・coverage 下限・G-UT-NO-ESCAPE のラチェットを同時に発火させる | 関数定義を書かない実装でラチェットと着手検出を回避する |
| G-UT-PER-TEST-OUTCOME | du-contracts の `apis[].ut` が指す対象 UT が **nodeid 単位で** executed かつ passed であることを outcome レポートと突合する（パラメータ化は基底 nodeid へ最悪値優先で畳む）。レポートに現れない nodeid は「未実行・改名・収集除外」として違反にする。集計 pass 件数・別テストの通過では代替できない。着手後に強制 | 「全体は green」で対象 UT の未実行・失敗を覆い隠す |

## worksets — S0.1 依存 Workset（実装レーン）

> 正本は `docs/L6-feature-design/S0/s0.1-worksets.json`（schema = 同ディレクトリの
> `s0.1-workset.schema.json`・追加プロパティ禁止）。S0.1（DU-01〜12）を依存方向に沿って
> **WS-S0.1-A 基盤 → WS-S0.1-B ゲートと WF 定義 → WS-S0.1-C カーネル**の 3 つへ分割し、
> 着手・完了・ラチェットを Workset 単位で判定する。従来の「最初の実装追加で S0.1 対象 UT
> 全 127 件を一斉に強制」する all-or-nothing は廃止し、**着手済み（in_progress／done）
> Workset だけ**へ強制する（未着手 Workset のスタブは猶予）。
> **Workset は PR の単位ではない**。A／B／C は実装順・依存閉包・統合完了（Workset ITC）を
> 管理する上位レーンであり、1 レーンは複数の実装 PR に分かれてよい。
> 正本が無い・壊れている・DU-01〜12 を過不足なく覆っていない場合は強制範囲を
> **S0.1 全 DU** へ倒す（正本を消せば強制が消える fail-open を作らない）。

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-WORKSET-SCHEMA | Workset 正本が schema 準拠（`workset_id`／`status`／`du_ids`／`api_ids`／`ut_nodeids`／`itc_ids`／`modules`／`depends_on`／`coverage_floor`／`red_receipt`）で、DU-01〜12 を**重複なく過不足なく**分割し（重複なき完全分割）、`status` は planned／in_progress／done の 3 値、`coverage_floor` は 80 以上、`done` は `red_receipt` を持つ | 分割の穴・DU の二重計上・証跡なしの完了宣言 |
| G-WORKSET-DEPENDENCY | `depends_on` が du-contracts の `depends_on_apis` から機械導出した Workset 間依存と**完全一致**し、Workset 依存グラフが非循環で、DU 単位の相互依存（SCC）が Workset を跨がない。原案の A→B→C と実契約が食い違う場合は**契約側が正本** | 宣言だけの依存順・循環した分割・分断された相互依存 |
| G-WORKSET-SCOPE | `api_ids`／`ut_nodeids`／`itc_ids`／`modules` が DU／API／UT／ITC 正本からの導出と完全一致する（手入力での加除を拒否）。ITC は cmp→DU→Workset で写像し依存順で最後に成立する Workset へ 1 回だけ割り当てる。さらに**着手済み Workset に属さないモジュールへ製品実装が無い**ことを要求する | 台帳の手書きによるスコープ僭称・他 Workset の製品コード混入 |
| G-WORKSET-TEST-REALITY | 着手済み Workset **だけ**に、対象 UT の skip／xfail／NotImplementedError／空 assert = 0（AST）・対象 UT が nodeid 単位で executed かつ passed（実行結果）・依存 Workset が done・`done` の `red_receipt`（40 桁 SHA の red_commit が HEAD の祖先・nodeids が Workset 内・green_commit も祖先）を強制する | 依存を飛ばした着手・skip を残した完了・実在しない red→green の主張 |
| G-WORKSET-COVERAGE | coverage 80% を `helix` 全体ではなく **active＋done Workset の対象モジュール集合**へ適用し、その解決（`tools/coverage_scope.py`）と下限（`tools/coverage_floor.py`）の結果が CI の pytest へ実際に引き渡されていることを YAML＋argv 構造で検査する | 未着手 Workset の空モジュールで分母を薄める／逆に達成不能な下限で着手を塞ぐ |
| G-WORKSET-RATCHET | 親コミット比で Workset の削除・`du_ids`／`api_ids`／`ut_nodeids`／`itc_ids`／`depends_on` の縮小・status 後退（done→in_progress／planned）・`coverage_floor` 低下・記録済み `red_receipt.red_commit` の改変が無い。DDL物理数同期のnodeid改名は `ut_nodeid_renames` に明示した同一Workset／同一file／数字以外同一の1対1だけを認め、rename台帳自体は縮小・改変不可。`done` へ進めた Workset は、その Workset の UT 件数以上を `tests/skip-budget.json` の `max_skipped` から減らす | 完了の後退・UT改名を使った縮小偽装・依存の緩和・skip 上限を据え置いたままの完了宣言 |

## review_binding — レビュー束縛

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-REVIEW-BINDING | レビュー成果物が schema 適合し、(a) target_commit が実在 (b) `target_tree` が**必須**で `git rev-parse <target_commit>^{tree}` と厳密一致（キー欠落で検査ごとスキップさせない）（`git log --all` の到達可能性走査は使わない — ref 到達性・clone 深度に依存しないため。dangling tree と別コミットのツリーへの掏替えを同時に落とす） (c) 記録 digest が target_commit／target_tree の内容と一致 (d) Go 判定の現内容が未改変、または `supersedes_review` で引き継ぐ後続 Go レビューが存在。レビュー成果物が未コミットの間だけ (b) を猶予し、猶予はゲート出力へ「CIで未検証」と明示する。旧パスは manifest の previous_paths で解決する | コミットメッセージだけの Go 記録・レビュー後のすり替え・clone 先で解決できないツリーへの束縛 |
| G-REVIEW-SEPARATION | レビュー成果物の主体分離を**証跡の出所ごと**に宣言させる（`separation_status` は`unverified`／`self_attested`／`ci_attested` の 3 値）。`self_attested` は `author_principal`≠`reviewer_principal`・`author_execution_id`≠`reviewer_execution_id`・`review_log_digest` が **git 追跡下**の実在ログ（`review_log_path`）のsha256[:16] と一致・そのログの `session_meta` レコードが `reviewer_execution_id` を、`turn_context` レコードが `model` を型付きで申告している（本文の部分文字列一致は根拠にしない）、をすべて満たすときに名乗れる。ただしそのログは**レビュー実行者自身が生成したローカル成果物**であり第三者署名ではないため、`self_attested` と `unverified` は「第三者検証」を主張できない。`ci_attested` は、CI が生成してリポジトリへ commit した attestation `docs/00-authority/reviews/attestations/<review_id>.json`（git 追跡下）が実在し、`ci_log_digest` がその sha256 と一致し、attestation の repository／run_id／head_sha／target_tree／workflow／artifact_name／artifact_digest がレビュー宣言（`ci_run_url`・`target_commit`・`target_tree`・`ci_workflow`・`ci_artifact_name`）および **実行ログの実体**と一致する場合に限る（run ID と URL の形だけでは成立しない）。さらに第三者性はローカル生成のファイル一式では作れないため、署名検証鍵 `docs/00-authority/reviews/attestations/trusted-keys.json` が配備されるまで `ci_attested` は**成立しない**（self_attested が上限 — fail-close）。証跡を取得できないレビューは `unverified` とし、分離を主張する欄を空にする（PO 判断へ送る） | 自己レビューを独立レビューと僭称する／ローカル生成ログを第三者検証と称する |

## requirement_discovery — 前向き要件発見証跡

> 正本は `docs/00-authority/development/requirement-discovery-events.json`（schema =
> `requirement-discovery-event.schema.json`）。これは `coverage_start_commit` 以後だけを記録する
> append-only の監査証跡であり、既存 BR／REQ／FR／NFR／AC／TC 契約 JSON や製品 runtime の代替ではない。

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-DISCOVERY-SCHEMA | root／event／reference の strict schema、stable ID、連番、UTC 時刻、event type、型別 payload、coverage 開始点以後の時刻を検査する。台帳 status は `adapted`、既存履歴は `preexisting-not-backfilled` とする | 既存履歴の捏造・曖昧な event・空 ledger の adopted 僭称 |
| G-DISCOVERY-PREFIX | 初回導入後は親コミット（又は最後に追跡された版）の events が現行 events の完全 prefix であり、root の schema version／authority／lifecycle status／historical policy／coverage start commit が不変であることを要求する | event の改変・削除・並替え・coverage 開始点の前方付替え |
| G-DISCOVERY-COVERAGE | `coverage_start_commit` から作業ツリーまでのBR／媒体BR／REQ／requirements compatibility view／FR／SR／NFR／媒体MR／FN／AC／TC／CMP／DU／L6 implementation-unit変更を検出し、対象artifactのspecification proposalと **accepted** decision、又は`deferred:`理由付きwithdrawalを要求する。rejectedは成立扱いにしない | 証跡なしの要求・設計入力変更、媒体/FNだけの無監査変更、保留理由のない撤回、却下を承認として扱う誤り |
| G-DISCOVERY-REFERENCE / G-DISCOVERY-LIFECYCLE | source／artifact は実在し、event 参照は先行 event に限る。subject は candidate から進み、質問・承認の順序と terminal event 後の追加を検査する。candidate は業務actor／受益者／workflow／scope in-out／制約・禁止／human judgement／外部副作用／完了証跡／target phaseを持ち、unknown dimension に対応する問いは question event と回答を経るまで specification proposal を拒否する | 孤児／未来参照・順序を飛ばした要件化・意味観点の未解決を設計で補完 |
| G-DISCOVERY-APPROVAL | approval decision の event actor／proposal author／approver を分離する。accepted は当時の artifact commit・manifest・receipt snapshot を束縛し、artifact ごとの最新 accepted だけを現行 digest と照合する | 自己承認・履歴を現行 digest で誤判定・digest／receipt のすり替え |
| G-DISCOVERY-SAFETY / G-DISCOVERY-NO-CANONICAL-MUTATION | credential／secret／PII／raw 外部本文（reference 値、代表 token／email／電話／住所表記を含む）を拒否し、AST で ledger／契約 path alias、`Path("…")`、`ROOT / "…"`、module alias からの自動書込みを拒否する。動的 import／eval／反射は静的完全検出の保証外であり、実行権限を与えない | 秘密漏えい・監査台帳による正本の迂回更新 |

## requirement_engine — HELIX 要件確定admission

> 既存9契約JSONをsource authorityとして扱い、IRは決定的に再生成できる非権威projectionとする。
> ID・件数の一致だけでは意味整合とみなさない。意味閉包が赤の間は要求を設計・実装入力へ切り替えない。

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-REQ-IR-PROJECTION | 9契約JSON＋refinement registryをstable ID keyedに正規化し、`requirements`／`system_contracts`／`acceptance_cases`／`system_tests`／`refinement_contracts`の5 shard、各count/digest、root digestを決定的に生成する。projectionは手編集可能な第二正本ではない | IR未生成・区画欠落・入力順依存・二重正本化 |
| G-REQ-SEMANTIC-DRIFT | compatibility requirements viewと契約正本の同一IDについてsliceとupstream/downstream traceを比較し、L1 REQ MarkdownとREQ JSON ledgerの本文・出典・下流・充填・優先度も比較する | 同じIDを保ったまま別の責務・導入時期・追跡先を提示する意味ドリフト |
| G-REQ-TRACE-BIDIR | BR.trace_downとFR/SR.trace_upを双方向に照合し、孤児と片方向参照を拒否する | 上位価値・actor・scopeに戻れない要求、又は下流で実現されないBR |
| G-REQ-TRACE-LAYERS | BR→REQとREQ→FR/SR/NFRの各隣接辺を双方向照合し、NFRを含む孤児・片方向参照を拒否する | 中間REQだけに存在する責務、BR/REQへ戻れない品質要求、根拠のない下流契約 |
| G-REQ-TRACE-IMPLEMENTATION | DUのtrace.ac／trace.tcが現行AC／TCC契約IDへ解決し、旧`TC-*`別名を含まないことを検査する | 存在しない旧試験IDへの設計・実装trace、TCC正本との二重語彙 |
| G-REQ-TRACE-FUNCTION-LEDGER | REQ compatibility ledgerのFN参照とFN ledgerのREQ upstreamを双方向照合する | REQからだけ見える機能、要求根拠へ戻れない媒体機能 |
| G-REQ-PHASE-ALIGNMENT | FR→FNとFR→AC target_updateの導入phaseを厳密照合し、`S1+`／`S3+`を実装phaseとして拒否する | 同じ責務の実装順逆転、包含phaseによる未確定範囲の実装混入 |
| G-REQ-SEMANTIC-DIMENSIONS | BR／媒体BR／REQ／FR／SR／NFR／媒体MR／FN／AC／TCごとにactor、beneficiary、value、workflow、scope、禁止、人間判断、副作用、証跡、phaseの該当軸を検査する | ID・件数・文章参照だけで意味閉包を主張すること、媒体・機能台帳の意味欠落、上位判断を下流処理が暗黙代替すること |
| G-REQ-OBSOLETE-RUNTIME-ROUTES | ADR-007／013でVPS runtime、製品Web UI＋UI内inboxへ置換した後も、旧入力にWSL cron、Discord固定approval DDL、`discord_app/approval_request`初期tupleが残る状態を拒否する | 新要求と旧confirmed設計を同時に実装入力へ使い、Discordを必須承認入口として復活させること |
| G-REQ-WP-RESPONSIBILITY-BOUNDARY | MR-WPのcontent operation（記事・固定ページ・media・公開）と通常保守（core／theme／plugin／WP-CLI）、security保守を別actions、connection、policy、actor、release、AC／TCへ分離する | `content_publish`承認でplugin/theme変更を実行すること、保守rollbackと公開rollbackの混同 |
| G-REQ-NOTIFICATION-PURPOSE-BOUNDARY | 投稿可否承認、UI内operational notification、媒体community投稿、開発PR通知を別stable ID／policy／principal／transport／evidenceへ分離し、FR-16／43から承認用FR-46への接続とFR-76のApprovalTransport再利用を拒否する | 異常通知を承認要求として扱うこと、運用通知や媒体投稿からapprove/rejectを成立させること |
| G-REQ-MEDIA-ROUTE-SEMANTICS | 媒体BRの公式API優先、consumer Web UI禁止、browser write禁止、on-holdをMRのconnection／actions／execution mode／statusへ照合する | LINE API方針の逆転、生成AI規約違反fallback、X browser write、保留Play公開routeの実装混入 |
| G-REQ-CONNECTOR-PRIORITY-SEMANTICS | BR／FR／ADR-006／L4 CMP-07／L5 DU-13の経路優先順を照合し、公式無料APIをbrowserより前に置く単一語彙へ再降下するまで拒否する | 同じserviceでMCP→browser→paidとMCP→API→browser→paidの異なるRouteを返すこと |
| G-REQ-L2-REVALIDATION-SEMANTICS | 旧L2 prototypeのgeneric Discord deep-link、未定義return、未知FR trace、未契約subscription write、cross-profile BIを検出し、新要求からの再作成まで拒否する | draft画面を要求根拠にして承認状態・通知用途・profile認可を設計で捏造すること |
| G-REQ-VPS-CREDENTIAL-BOUNDARY | ADR-007のVPS `0600`環境fileと、S0／external-ifの暗号化store・runtime注入契約を照合し、単一のat-rest／in-memory／scope／rotation／recovery要求へ凍結するまで拒否する | file modeだけを暗号化とみなすこと、env／service unit／journal／argvへのsecret漏えい、test/prod credential混用 |
| G-REQ-MEDIA-ADMISSION | 全MRに`enabled`／`attended-only`／`read-only`／`deferred`、execution mode、principal、effect、policy category、下流AC／TC又はdeferred再開契約を要求する | proseのconnection/actionsだけで外部writeを有効化すること、全MR downstream空のまま媒体稼働を宣言すること |
| G-REQ-LEGACY-MEDIA-INVENTORY | 旧MR全件を新baselineでは安全側`deferred`として棚卸しし、業務価値、execution mode、principal、effect、policy、credential、quota、evidence、AC／TCを閉じた個別capabilityだけ再開可能にする | 旧connection／actions／safety本文から新baselineの実行許可又は経路を推測すること、一部MRの棚卸し漏れ |
| G-REQ-TRACE-SEMANTIC-RESPONSIBILITY | BR／REQが要求する状態、関係、禁止、証跡を下位FRのbehavior／postcondition／ACへ照合する。ID実在・双方向edgeだけでは成立扱いにしない | BR-A3のbrand/action plan traceをFR-71の汎用DDL生成で代替する等、意味の異なる契約へのfalse trace |
| G-REQ-DESCENT-ADMISSION | `design_status=requirements_defined` のFR／SRはFN・CMP・ACへ降下済み、又は`admission_status=deferred`と型付き再開条件を持つことを要求する | ACだけ存在してFN／CMPがない要求、戦略testだけ存在してACがない要求をimplementation-readyと扱うこと |
| G-REQ-VPS-UI-DESCENT | VPS UI主入口が要求する状態・証跡・KPI閲覧と、旧FR-77のread-only API限定／Web UI禁止を照合する | UIを初期主入口と宣言しながら閲覧契約がWeb UIを禁止したまま、画面だけを設計すること |
| G-REQ-HUMAN-JUDGEMENT-DESCENT | 上位BRのPO判断をFR／SRの責務、ACの反証条件、approval／decision evidenceまで追跡する | KPI tree初期承認、媒体追加、Design System改訂、オートモード移行、企画確定を自動処理又は別agent審査で代替すること |
| G-REQ-NFR-AUTHORITY | 全NFRをstable REQ／BRへ逆traceし、根拠未確定なら`deferred`理由・再開条件を要求する | requirements文書節、risk、MR、別NFRだけを根拠に法規・backup／recovery・quotaをconfirmedと扱うこと |
| G-REQ-STRATEGY-TEST-AUTHORITY | confirmed ACが参照する`STC-*`の台帳をPO content receipt付きconfirmed正本へ束縛し、未確定ならAC／SR側をdeferredにする | confirmed ACの反証oracleをactive／draft test ledgerへ依存させ、TCCと二重の試験正本にすること |
| G-REQ-PROVIDER-DEPENDENCY | provider-neutral要求と、旧L0／BR／L4のClaude Design必須、個人Codex CLI/home証跡、consumer Web UI fallbackを照合する | 開発client非必須と製品provider必須を混同し、VPS runtimeが個人home又は規約違反Web UIに依存すること |
| G-REQ-LEGACY-CONSUMER-ISOLATION | historical/revalidation扱いの旧REQ／requirements viewを、L0、S0契約、基本設計、検証設計、trace台帳の規範入力から隔離する | warningだけを根拠に同一ID・別slice・別traceの旧一覧を現行要求として下流設計へ再利用すること |
| G-REQ-DESIGN-NOT-STARTED | 要求baselineがrevisingの間、L2〜L6を`revalidation_required`かつ`implementation_input=false`に固定し、L2をdraftに保つ | 旧画面・API・DDL・状態・AC/TC・実装単位を新VPS UI要求の設計済み成果物として扱うこと |
| G-REQ-SCOPE-ASSIGNMENT | 旧要求864 IDを`legacy_revalidation_only`に固定し、新refinement全subjectをrequirements governance／initial／follow-on／deferred候補へ一意に割り当てる。VPS UI、初回activation、content gate、risk、research loopはinitial候補、Playwright routeとDiscord communityはfollow-on候補、旧Discord通知候補はdeferredへ固定する | 旧Discord・旧phase等を含むIDの初期scopeへの直接昇格、VPS UI/inbox/security/growth候補の欠落、生成AI/旧媒体の黙示有効化、Discord communityと通知の再混同 |
| G-REQ-DECISION-PACKETS | PO確認用packetが全refinement subjectを順序付きでexactly once被覆し、packet内でもsubject別receiptを要求する。会話からcaptureしたPO判断の`required_new_subject_ids`は実在refinementへmaterializeし、Playwright、Discord community、初回承認後自動運用、content gate、risk、research/funnel/KPIの回答意味が対応semantic dimensionsに存在しなければならない | 重要判断の欠落、回答を監査メモ又は空IDだけへ残すこと、回答と逆のrefinement、重複判断、packet一括approveによる個別semantic digest・source-set digest束縛の省略 |
| G-REQ-CANDIDATE-BINDINGS | baseline候補の全PRC見出しを実在refinement meaning ownerへ束縛し、全subjectが少なくとも一つのPRC責務を持つことを検査する。初期通知はVPS UI inbox、Discordはcommunity専用、VPS UI判断は毎回の投稿承認でなく初回activation／例外判断であることも固定する | 手書きPRCの孤立、未知subject参照、候補本文とtyped refinementの二重意味化、旧Discord通知又は個別投稿承認の再混入 |
| G-REQ-L0-CLAUSE-DISPOSITION | 旧charter v0.4の目的・loop・媒体・human/AI・provider・browser・runtime・Discord・auto-mode等をclause単位で`retain`／`replace`／`defer`へ分類し、replacement PRC、deferred再開条件、未承認・未設計境界を検査する | 旧L0の手段を事業価値と混同した現役復帰、Discord初期承認・consumer Web UI・Claude Design・旧auto-modeの暗黙継承、PWA/Playの無承認再開 |
| G-REQ-CRITICAL-RESPONSIBILITY-DISPOSITION | 旧BR-H2/H3及びFR-16/43/46/75/76/77の通知・承認・自動運用・profile binding・閲覧責務を、VPS UI内inbox、初回activation、content gate、repair/safety evidence、Web UI read modelへ明示分割する。旧Discord approval/operational notification、毎回投稿承認、機械criteriaだけのactivation、API-only UI禁止を継承禁止として検査する | 旧confirmed BR/FRを新要求へ直接戻し、Discord通知、ApprovalTransport再利用、個別投稿承認又はFR-77のWeb UI禁止を復活させること |
| G-REQ-SEMANTIC-DESCENT-POLICY | BR／媒体BR→REQ／MR→FR／SR／NFR→FN／AC→TCの各edgeで12意味軸の直接宣言又はsource revision・semantic digest・scope transform付き継承を要求する。actor、task、workflow、scope、人間判断、副作用、証跡、phaseは対象層で直接宣言し、上位禁止は弱めず継承する。FN→CMP→DUは要求freezeまでblockedとする | ID traceや散文から主体・scope・判断・副作用・phaseを推測すること、target IDをscopeへ読み替えること、要求未確定のまま設計者が欠落を補完してL2以降へ進むこと |
| G-REQ-LEGACY-NFR-DISPOSITION | 旧NFR-1〜11を業務価値、actor、scope、stable BR/REQ root、置換意味、未決事項及びmeaning ownerへ束縛し、`redescent`／`replace`／`defer`へ分類する。支出NFR-6、業務root未確定の法規NFR-9、VPSデータ分類未確定のbackup NFR-10、stable REQ不在の月次quota NFR-11は再開条件付きdeferredとし、NFR-7の全経路1〜5秒一様乱数をAPI/MCP quotaとPlaywright節度へ分離する | 旧測定式、SQLite、Discord、MR、risk ID、別NFR又は既存AC/TCだけを根拠に品質要求を現役化すること、有料経路や未分類quotaを初期実装へ混入すること |
| G-REQ-ORPHAN-REQUIREMENT-DISPOSITION | stable REQ root又はFN/CMP/AC降下を欠く旧FR 11件とSR 19件をstable ID exact coverageで責務groupへ収載し、`redescent`／`replace`／`defer`、root action、descent action、meaning owner、再開条件及び未承認・未設計境界を検査する。旧Discord/API-only UI、旧S0、S3+包括phase、有料支出、高度分析の暗黙採用を拒否する | ACだけあるFRをrequirements-defined又はimplementation-readyと扱うこと、charter/BR直結のSRをstable REQなしで採用すること、logic tree等をdraft testだけで先行設計すること |
| G-REQ-LEGACY-REQ-DISPOSITION | 旧REQ 55件をstable ID exact coverageし、confirmed Markdownとdraft JSONのどちらも現要求正本として採用せず、ID別`redescent`／`replace`／`defer`、meaning owner及びdeferred再開条件を検査する。SQLite、HTML/xlsx、MCP→browser→paid、WP固定、Claude Design、Discord承認/通知、旧auto-mode、全媒体browser乱数、媒体一括稼働を現要求へ置換又は延期する | 同一REQ IDの旧MD/JSON差分を自動unionすること、古い実現手段を業務要求として再利用すること、deferred対象を再開条件なしで初期scopeへ戻すこと |
| G-REQ-LEGACY-BR-DISPOSITION | 旧BR 41件をstable ID exact coverageし、保持する事業価値と置換する実現手段を分離する。browser/SQLite/HTML/xlsx、MCP→browser→paid、WP一律収束、Claude Design、二接点限定、Discord個別投稿承認、旧auto-mode及び旧通知をVPS/UI/API-first/provider-neutral/phase別判断へ置換する | 旧BRが上位だからという理由で古いruntime、provider、承認又は通知方式まで現要求へ無条件継承すること |
| G-REQ-LEGACY-MEDIA-BR-DISPOSITION | 旧媒体BR 70件を媒体別にexact coverageし、`replace`又は`defer`、現候補でのfunnel役割、route policy、meaning owner、再開条件、未承認・未設計境界を要求する。Discord community、affiliate offer authority、LINE API-first、measurement read、WP責務分離、X browser境界、Stripe顧客金銭operation等を明示する | 媒体名又は旧BRの存在を実行許可とみなすこと、製品通知とcommunityを混用すること、consumer Web UIやbrowser writeを暗黙に有効化すること、全媒体を一括releaseすること |
| G-REQ-LEGACY-FR-DISPOSITION | 旧FR 43件をstable IDでexact coverageし、`redescent`／`replace`／`defer`、meaning owner、延期理由と再開条件、未承認・未設計境界を要求する。旧SQLite、Discord通知・個別承認、provider固定、API-only UI、媒体一律route、phase混在を現要求へ直接継承しない | 旧confirmed FRを現在の実装入力とみなし、VPS製品状態、UI内inbox、初回activation、API/MCP優先＋Playwright確認、provider-neutral及びprofile/account権限を設計者が推測で補うこと |
| G-REQ-LEGACY-DERIVED-CONTRACTS | 旧FN 61件、AC 252件、TC 258件のstable ID集合をcount＋digestでexact固定し、親要求のPO凍結・再降下・意味軸再生成まで`legacy_revalidation_only`かつ未設計として扱う | 旧FNを機能設計、新要求と異なる旧AC/TCを受入証拠とみなすこと、旧Discord・phase・provider・fixtureから新runtimeを逆算すること |
| G-REQ-AUTHORITY-REVISION-CANDIDATE | 新revisionの単一JSON正本＋生成Markdown＋旧IDへのsupersedes mappingを推奨案として保持し、PO未回答の間は旧ID書換え、authority cutover及び設計開始を拒否する。旧requirements consumerをinventory化し、選択後に一括置換又はhistorical隔離する | 推奨案をPO決定とみなすこと、旧MD/JSONを自動unionすること、旧Discord・API-only UI・WSL・provider・phaseを新revisionへ暗黙移植すること |
| G-REQ-OBJECTIVE-COMPLETION-AUDIT | 意味全件棚卸し、旧参照隔離、VPS UI/inbox要求、設計未着手、新要求正本freezeを目的別に`proven`／`incomplete`／`blocked_by_po`へ分類し、証拠と残条件を要求する | 構造的棚卸し完了を新要求freeze又は設計完了と読み替えること、UI候補を実装済みとみなすこと、PO未承認を完了扱いすること |
| G-REQ-REFINEMENT | subject/revision、source event集合digest、12意味軸、positive/negative/boundary acceptanceとsystem test、pending解消、semantic digest、approved/frozen時のPO receipt束縛を検査する | 要約だけの仕様化、根拠差替え、反例・境界なしの承認、未解決事項を残した凍結 |
| G-REQ-REFINEMENT-COVERAGE | discoveryへ記録した全要求候補が、同じsubject IDの個別refinementを持つことを検査する | 質問又は候補を記録しただけで仕様化対象から欠落させること |
| G-REQ-OPEN-REFINEMENTS | 全refinementでpending_resolution=0、PO receipt、lifecycle=frozenの同時成立を要求する | draft候補、未回答質問、AI回答、部分承認を要求完了とみなすこと |
| G-REQ-APPROVAL-ADMISSION | activeなapproval requestがある場合、semantic driftと双方向trace違反が0でなければ承認工程を拒否する | 未精査要求の一括承認・構造だけを根拠にしたauthority cutover |
| G-REQ-AUTHORITY-CUTOVER | baseline=approved、semantic closure=0、refinement検証=0、全recordがPO receipt付きfrozen、未決approval request=0の同時成立時だけimplementation_authorized=trueを許す | 旧confirmed契約・未凍結要求・部分承認を製品実装入力へ戻す誤り |

## template_alignment — HELIX-HARNESS 適応

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-TEMPLATE-ALIGNMENT | `docs/00-authority/template/helix-harness-alignment.json` が schema に適合し、RetryYN/HELIX-HARNESS の固定採用 commit と latest checked commit を分離して read-only 方針・差分処置・Python-native／Bun 非依存・要件定義範囲を宣言する。対応 mapping、現行パス、L2 5 点セット、adapted discovery lifecycle、Python 3.14 pin、uv frozen sync、CI concurrency／timeout／checkout credential 非保持、`make doctor`／`make test`／全ゲートの導線を fail-close で検査する | テンプレート参照先や最新版確認点のすり替え、二重正本、toolchain drift、無制限・credential 残留 CI、未登録の開発環境・L2 設計、Bun／Node ランタイムの誤導入 |

## baseline — デグレ検出と配線

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-BASE-EXIST/HASH/STATUS/RATCHET | baseline.json に対し confirmed 文書のハッシュ一致・降格なし・分母縮小/ゲート削減なし・pytest skip 上限の未承認引き上げなし（引き上げは approvals.md の構造化 PO 承認行に加え、**同一変更の API 単位 UT 追加本数以内**であることを要求 — 承認行だけでは上げられない）・**S0.1 着手前提条件（plan-s0.1.json の preconditions[].id）の削除なし**（比較元は**親コミット**の baseline、引き上げには approvals.md の構造化 PO 承認行が必要） | デグレ：confirmed のサイレント改変・後退・スコープ縮小 |
| G-BASE-ART | 実装入力（契約 JSON・DDL・manifest・ゲートモジュール・CI・規律文書・hook・skip/coverage 予算）のハッシュが baseline と一致・未登録なし | 実装入力のサイレント改変 |
| G-BASE-ART-PATHS | baseline.json の `artifacts` が「**git 追跡下かつ作業ツリーに実在するパス** → sha256 64 桁」だけで構成される。この台帳は digest のみを持つため secret scanner（gitleaks）の allowlist で除外しているが、その除外が安全なのはキーが実在パスに限られることが機械保証されている場合だけであり、本ゲートがその保証を与える。allowlist の設定ファイル `.gitleaks.toml` 自体も baseline の改変検出対象に含める | 台帳に秘密らしきキー（`api_key.txt` 等）を紛れ込ませ、secret scan の allowlist を悪用する |
| G-COUNT-SYNC | 手書きのゲート件数、README の主要分母（BR/REQ/FR/NFR/FN）、README/CLAUDE/AGENTS各1行のAC/TCC/API/API_UT分母が各正本の実数と一致 | 入口・エージェント規約に残る旧件数・散在する件数のドリフト |
| G-WIRING | 全ゲート ID が本台帳に掲載され、CI が `tools/gates/run_all.py` を呼ぶ | ルールの配線漏れ・死蔵 |
| G-GATE-MODULES | ゲートが tools/gates/ の工程別モジュール（`common.GATE_MODULES` が正本）へ分割され、validate_requirements.py が薄い互換ラッパー（40 行以下・run_all 参照） | 巨大 validator への逆戻り |
| G-GATE-UNITTEST | 各ゲートモジュールに単体テスト（tests/gates/test_<module>.py）が存在し、`test_mutation_*` 関数**それ自身**が当該モジュールの関数を到達しうる位置で呼び、その**結果を観測する** assert を持つ（assert 式が呼出しを含むか、呼出し結果に束縛された名前を参照する。タプル代入は位置対応、名前伝播は固定点で解決） | 検査されないゲート実装／`def test_mutation_x(): pass`・結果を捨てる・到達しない位置に置く形骸 mutation |

## 運用

- 分母を意図的に変える場合（BR 追加等）は、正本 JSON・生成ビュー・manifest・baseline を **同一コミット**で更新する
- S1 以降で AC・WF・FN が増えたら、対応するゲート期待値の更新もそのスライスの完了条件に含める
- 旧体系（AC/TC/UT 台帳）に依存していたゲートは、archive 化に伴い契約正本ベースの後継へ置換した
  （G-CNT-AC→G-CNT-CONTRACT、旧 G-GWT は AC 契約へ、G-PAIR-*→G-PAIR-MANIFEST／G-TC-REJECT／G-TC-SLICE、
  G-UTC-*→G-UT-FILE-UNIQ／G-UT-FILE-EXIST、G-LEGACY-SUPERSEDED→G-LEGACY-ARCHIVED）。ゲート総数は減らしていない
