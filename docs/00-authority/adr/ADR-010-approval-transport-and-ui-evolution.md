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

> 2026-08-14追補: ADR-013が入口の投入順序を「Web UI＋UI内inboxを初期主入口、Discordは任意補助」へ
> 置換した。本ADRのVPS側API／DB正本、binding、CAS、秘密隔離、transport交換可能性は引き続き有効である。

承認状態・束縛・期限・応答者・証跡の正本は VPS 側 DB とし、製品実行時の承認契約を
Claude Code から独立させる。

承認の入口は交換可能な `ApprovalTransport` とする。当初案は個人用 DiscordサーバーのDiscord Appを
初期adapterとしたが、ADR-013により製品Web UIを初期主入口へ変更した。
Discord は恒久的な業務正本でも初期必須adapterでもない。採用する場合はUIへの通知deep-link補助に限る。

```text
初期: VPS approval API / DB <- Web UI + UI内inbox <- standard browser
任意: VPS approval API / DB <- Discord App（通知deep-link補助。単体でdecisionしない）
```

Claude Code は開発支援、対話デバッグ、任意の閲覧クライアントとして利用できるが、通知、承認、
初期ヒアリング、BI 閲覧を含む製品実行時の必須依存にしない。

## 不変条件

1. 承認入口は状態を直接確定せず、VPS 側承認 API を通す
2. `binding_subject` / `binding_operation` / `binding_at` の完全一致を維持する
3. 許可された承認者 ID、要求期限、Web UI session、CSRF、操作時再認証を fail-close で検証する
4. pending 行は compare-and-set で一度だけ approved / rejected / expired に確定でき、再送・二重クリック・期限切れ操作を拒否する
5. transport token、署名鍵、session secret を repo・DB・ログへ保存しない
6. 任意の外部通知が障害でも承認状態は失われず、VPS 側 pending とUI内inboxから再開できる
7. 外部通知adapterを追加・交換しても、承認 API、DB、証跡、状態遷移の意味を変更しない

## 任意 Discord 補助アダプター

- 専用の個人 Discord サーバー／承認チャンネルを使い、会社 Slack と分離する
- 承認要求には対象、操作、時点、期限、プレビューへの参照を表示する
- Discord messageは認証済みWeb UIへのdeep-linkだけを持つ。button、interaction、slash command、reactionで
  `approve` / `reject` / `expired`を記録せず、VPS approval APIのdecision endpointへ直接接続しない
- Discord application ID、guild ID、channel ID、許可 user ID を config から解決する
- Bot token 等は VPS 上の権限制限された環境ファイルで管理する

## 初期 Web UI／将来PWA拡張

承認待ち一覧、コンテンツプレビュー、承認・拒否理由、実行状況、失敗履歴、KPI、
ブランド／媒体設定を段階的に提供する。Discord 通知から UI を開く場合も、URL だけで承認を
確定せず、認証後に対象と操作を再表示して明示操作を要求する。

## 帰結

- 初期channelは`web_ui`とUI内inboxとする。認証・session・CSRF・再認証・principal束縛は要求確定後のAC/TCでfail-closeに設計する
- `discord_app/approval_request`は初期必須tupleから外す。採用時も通知deep-link補助専用とし、Discord interactionだけでdecisionを確定しない
- 初期ヒアリングは構造化回答 API を正本とし、Claude Code 対話は任意クライアントへ降格する
- BI は標準ブラウザで閲覧可能な UI とし、Claude Code 内蔵ブラウザを必須にしない
- Discord 固有の署名検証・payload 変換は connector に閉じ、kernel は Discord 型を参照しない
