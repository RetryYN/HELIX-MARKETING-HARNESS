---
artifact_id: AUTH-AUDIT-XSERVER-API-POC-EVIDENCE-2026-08-14
lifecycle_status: draft
slice: cross
---

# XServer API/CLI PoC証跡監査（2026-08-14）

## 判定

VPS `helix-worker`からXServerレンタルサーバー上のWordPressを自動管理するPoCは実施済みであり、
P0〜P4の主要成功条件を満たす証跡がVPSローカルの独立Gitリポジトリ
`/home/tenni/dev/poc-wp`に存在する。credentialや実値を本リポジトリへ複製せず、commit IDと
証跡digestだけを監査参照とする。

これは次を証明する。

1. `helix-worker`からXServer API/CLIへ認証・疎通できる。
2. サブドメイン、SSL、WordPress、SSH鍵をスクリプトで払い出せる。
3. REST／WP-CLIでコンテンツと設定を冪等同期できる。
4. backup→update→cache purge→Playwright smoke→失敗時rollbackの保守経路を構成できる。
5. WordPressを破壊後に再構築し、before／afterが同一digest、diffが空になる。

これはXServer VPS管理APIや製品Web UIの認証・TLS・session・CSRF・reverse proxyを検証した証跡ではない。
検証対象は、`helix-worker`を実行主体とするXServerレンタルサーバー／WordPress連携である。

## 実行系譜

| phase | commit | 内容 |
|---|---|---|
| P0 | `603358f91177ab1a9a1e9de57180397f8ee5b913` | XServer CLI疎通、秘密隔離 |
| P1 | `d06a67153a68516e8fdc86440bfc472b228cb9ee` | subdomain／SSL／WP／SSH provisioning |
| P2〜P4 | `0c03abf7fd3fd68e4aa63ff087705568bf266dc3` | 冪等同期、保守、破壊再構築PASS |

## 代表証跡digest

| evidence | sha256 |
|---|---|
| `p0-me.json` | `4bfecfc3171f2aab7f9491830117e6602d7d1b0f803e4af5bb5bf428d3ec18cf` |
| `p0-server-info.json` | `3bdfde6052d73f46f5a9dabcacb9e534aadf7c1099908db860e5a032cf327375` |
| `p1-subdomain-add.json` | `63924a14175b409e38bb451b3940af5edd370780ece24a1a3585a5d73b737f2a` |
| `p1-ssl-list.json` | `423644ea0ce7bebc9fa01f1c61b2930869b1fb01c38ece4acca3c6dd40fc3cf8` |
| `p1-wp-add.json` | `04a8bd0e98582d78a329bcd5c5540a33389cab0489ea45c3a27c892b80f58979` |
| `p2-sync-all-run1.json` | `c43cedda5fcd26a59dadf038655e0553e6786395484c6ced52922bcb489d65b7` |
| `p2-sync-all-run2.json` | `3ed93e36ef37ceed47078e05e8beed6bb9694bc5f943e0cd7fe183bc6fe25c0c` |
| `p3-failure-sim.json` | `9b427e3abac98486768072a86405362f779fec2cc82fd52cc85afa6700a93b57` |
| `p4-before.json` | `19b93073ef1e84b83fe5e00a9f1508d3bf440d5370e0591a1a6ec5830a257ef7` |
| `p4-after.json` | `19b93073ef1e84b83fe5e00a9f1508d3bf440d5370e0591a1a6ec5830a257ef7` |
| `p4-diff.txt` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## 要求への反映

- VPS採用は未決候補ではなく、ADR-007のaccepted決定とする。
- XServer API/CLIはWP環境provisioning／運用adapterの実証済み経路とする。
- API成功だけでは公開反映を証明しない。server cache purge後のPlaywright表示検証を完了条件に含める。
- credentialはVPSの権限制限領域に置き、repo、DB、ログ、監査本文へ複製しない。
- 製品Web UIは同VPSへ組込み可能だが、認証・公開・service構成は要求承認後に設計・検証する。
