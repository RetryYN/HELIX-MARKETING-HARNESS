---
artifact_id: AUTH-ADR-ADR-014-VPS-CREDENTIAL-STORE-AMENDMENT
lifecycle_status: draft
slice: cross
---

# ADR-014: VPS credential保存境界を暗号化storeへ改訂する

- status: proposed
- date: 2026-08-14
- decision_authority: PO（未承認）
- 関連: ADR-007、s0-contract、external-if-design、DU-14

## 状況

承認済みADR-007は、接続資格情報をVPS上の`0600`環境ファイルに置く。一方、S0契約と外部IF設計は
暗号化store又は実行時の人手注入を要求し、credentialを設定・環境変数として横流ししない。Unix file modeは
他userからの読取りを抑制するが、平文at-rest、service定義、journal、process argv、dumpへの漏えいを防ぐ
暗号化境界ではない。

## 提案

1. 永続credentialはVPS上の暗号化credential storeへ保存し、必要なprocessへ実行時だけ注入する。
2. backend未整備時は有人の一時注入だけを許し、再起動後の無人復旧を成立扱いにしない。
3. `0600`だけの平文env fileを永続保存先として許可しない。
4. repo、製品DB、監査本文、service unit、journal、process argv、core dumpへcredential値を残さない。
5. 媒体PoCと本番はprincipal、credential、scopeを分離し、本番昇格時に再承認する。

## 非決定

具体backend、unlock方式、rotation期間、backup/recovery、systemd credential連携は要求refinementで閉じた後に
設計する。本ADRが承認されるまでADR-007の承認済み文言を履歴上書きせず、要件baselineは
`revalidation_required`のまま維持する。
