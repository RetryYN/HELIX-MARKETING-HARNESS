---
artifact_id: AUTH-ADR-ADR-007-UNATTENDED-EXECUTION-VPS
lifecycle_status: confirmed
slice: cross
---

# ADR-007: 無人自走レーンの実行基盤を cron（WSL）から VPS（helix-worker, systemd）へ移す

- status: accepted
- date: 2026-08-12
- decision_authority: PO（2026-08-14、本VPS稼働実態とXServer API PoC証跡を確認して採用）
- 関連: tech-stack §1（スケジューラ）/ §2（ブラウザ自動化）、NFR-2（決定性）、NFR-3（再開性）、charter の無人自走方針、RSK 系（運用停止リスク）

## 背景

tech-stack v0.1 はスケジューラを「cron（WSL）+ ハーネス内 heartbeat」と決定した。この決定は
専用実行基盤が存在しない前提での最適だったが、以下の実態と矛盾する:

1. cron（WSL）は Windows PC が起動している間しか発火しない。北極星の
   「ヒューマンアウトオブループ・cron 無人自走」が、実際には「人間が PC を点けている間だけ自走」になる
2. 運用実績上、ローカル実行系は無人稼働に不向きな障害を既に起こしている:
   WSL の OOM による claude プロセス kill（2026-08-06）、Windows Update の強制再起動、
   wsl --shutdown 後の Docker Desktop 復帰失敗
3. 2026-08-12 に専用 VPS「helix-worker」（Xserver VPS: 6vCPU / 12GB / 400GB NVMe,
   Ubuntu 26.04 LTS）が整備され、前提条件が変わった。Playwright + Chromium + xvfb +
   日本語フォント導入・動作確認済み。追加費用ゼロ（契約済み資源の転用）

## 決定

実行環境を有人/無人の二車線に分離する:

| 車線 | 実行基盤 | 対象 |
|---|---|---|
| 無人車線 | **VPS helix-worker（systemd service / timer）** | スケジュール発火・キュー駆動ワーカー・Playwright 無人突破・証跡蓄積・KPI 収集 |
| 有人車線 | **スマホ／標準ブラウザ＋ローカル開発環境** | Web UI＋UI内inbox、OAuth初回ログイン取得、Notion計画同期、Docker WP検証、開発 |

- tech-stack §1 の「cron（WSL）」を「systemd timer（helix-worker）」に改訂する。
  ハーネス内 heartbeat 判断は変更なし（OS は発火のみ、回転判断はエンジン、の原則は維持）
- ブラウザ三段構え（ADR-003）・API 第一経路（ADR-006）は変更なし。実行場所が VPS になるのみ
- 有人前提の操作入口はスマホ／標準ブラウザに置き、承認状態とAPIはVPS側に置く（ADR-010）。
  Claude Codeは開発・対話デバッグ用の任意クライアントであり、製品実行時の必須依存にしない

## 車線間の接続契約

1. **セッション搬入**: OAuth / ログインセッションはローカルの有人操作で取得し、
   ブラウザプロファイルとして VPS のブランド別プロファイル（brand-isolation 設計に従う）へ搬入する
2. **承認**: 承認待ちタスクは VPS 側キューで停止し、交換可能な承認入口（初期Web UI＋inbox、外部通知は任意adapter）から
   VPS側承認APIへ結果を書き込むことで再開する（承認状態の正本は VPS 側 DB）
3. **デプロイ**: 正本は GitHub。VPS は pull + 全ゲート PASS を確認してからワーカーを再起動する
   （fail-close: ゲート不合格の版は稼働しない）
4. **証跡**: 実行証跡の一次蓄積は VPS。ローカルの対話 BI は VPS から取得したデータを読む

## 理由

- 無人自走の可用性を人間の生活習慣（PC を点けているか）から切り離す。これは方針変更ではなく、
  北極星「ヒューマンアウトオブループ」と実装のねじれの解消である
- systemd は再起動後の自動復帰・リソース制限（MemoryMax/CPUQuota）・journal 証跡を標準提供し、
  NFR-2/NFR-3 の担保が cron + 手動復旧より強くなる
- 事故時の爆発半径分離: 実行系の暴走・資源枯渇が開発環境（WSL）を巻き込まない。逆も同様

## 帰結

- tech-stack §1 を次版で改訂する（本 ADR 承認後）
- s0-contract の環境契約に VPS 実行環境（helix-worker）の前提を追記する
- 秘密情報の置き場所規律（credential を repo・DB・ログに書かない）は VPS 側にも同一適用。
  接続資格情報は VPS 上の環境ファイル（600 権限）で管理し、GitHub を経由しない
- ローカル cron 前提で書かれた運用手順があれば systemd unit 前提に読み替える
- WSL cronは旧環境として終了し、製品runtimeと製品フロントの配備先はVPS `helix-worker`を基準とする

## 未決事項（後続要求・設計）

1. 人間向け主入口はADR-013の製品Web UI方針で再定義する。通知adapterの初期集合は要求で確定する
2. 証跡バックアップ先: GitHub 証跡リポジトリ / オブジェクトストレージ / ローカル同期のいずれか
3. Docker WP 検証環境を VPS 側にも複製するか（本番反映パイプラインの配置）
