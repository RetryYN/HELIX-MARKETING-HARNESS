---
artifact_id: AUTH-ADR-ADR-010-APPROVAL-TRANSPORT-AND-UI-EVOLUTION
lifecycle_status: confirmed
slice: cross
---

# ADR-010: 承認の正本を VPS 側に置き、Discord から専用 UI へ発展させる

- status: accepted
- date: 2026-08-12
- decision_authority: PO（本対話で確定）
- 関連: ADR-007（VPS 無人車線）、ADR-009（製品出荷境界）、BR-H2、FR-46、CMP-11、DU-18

## 決定

承認状態・束縛・期限・応答者・証跡の正本は VPS 側 DB とし、製品実行時の承認契約を
Claude Code から独立させる。

承認の入口は交換可能な `ApprovalTransport` とする。初期アダプターには個人用 Discord
サーバーの Discord App を採用し、将来は製品の Web UI / PWA を主入口として追加する。
Discord は恒久的な業務正本ではなく、通知と承認操作を中継する初期アダプターである。

```text
初期: VPS approval API / DB <- Discord App <- mobile Discord
将来: VPS approval API / DB <- Web UI / PWA
                            <- Discord App（通知・補助入口）
```

Claude Code は開発支援、対話デバッグ、任意の閲覧クライアントとして利用できるが、通知、承認、
初期ヒアリング、BI 閲覧を含む製品実行時の必須依存にしない。

## 不変条件

1. 承認入口は状態を直接確定せず、VPS 側承認 API を通す
2. `binding_subject` / `binding_operation` / `binding_at` の完全一致を維持する
3. 許可された承認者 ID、要求期限、Discord interaction 署名を fail-close で検証する
4. pending 行は compare-and-set で一度だけ approved / rejected / expired に確定でき、再送・二重クリック・期限切れ操作を拒否する
5. transport token、署名鍵、session secret を repo・DB・ログへ保存しない
6. Discord 障害時も承認状態は失われず、VPS 側 pending から再通知または将来 UI で再開できる
7. Discord から将来 UI へ移行しても、承認 API、DB、証跡、状態遷移の意味を変更しない

## 初期 Discord アダプター

- 専用の個人 Discord サーバー／承認チャンネルを使い、会社 Slack と分離する
- 承認要求には対象、操作、時点、期限、プレビューへの参照を表示する
- `approve` / `reject` ボタンの interaction を VPS の HTTPS endpoint で受ける
- Discord application ID、guild ID、channel ID、許可 user ID を config から解決する
- Bot token 等は VPS 上の権限制限された環境ファイルで管理する

## 将来 UI / PWA

承認待ち一覧、コンテンツプレビュー、承認・拒否・差戻し理由、実行状況、失敗履歴、KPI、
ブランド／媒体設定を段階的に提供する。Discord 通知から UI を開く場合も、URL だけで承認を
確定せず、認証後に対象と操作を再表示して明示操作を要求する。

## 帰結

- S0 の channel は `discord` のみに閉じる。`web_ui` は認証・session・CSRF・再認証・principal束縛の要求とAC/TCを追加する将来スライスで初めて許可する
- 初期の実値は `discord`、service は `discord_app`、operation は `approval_request` とする
- 初期ヒアリングは構造化回答 API を正本とし、Claude Code 対話は任意クライアントへ降格する
- BI は標準ブラウザで閲覧可能な UI とし、Claude Code 内蔵ブラウザを必須にしない
- Discord 固有の署名検証・payload 変換は connector に閉じ、kernel は Discord 型を参照しない
