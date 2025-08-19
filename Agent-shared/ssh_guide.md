# 🔌 SSH接続運用ガイド

## 概要

PGエージェントがリモート環境にSSH接続してコマンド実行・ファイル転送を行うためのガイドです。
MCPサーバ（wcgw、DesktopCommanderなど）を活用することで以下の課題を解決します：
- 2段階認証の処理
- 大容量ファイル転送の効率化
- 大量の標準出力によるコンテキスト浪費の防止

## 運用方針

### MCPサーバ使用対象
- **PG（Program Generator）エージェント**: 主要なMCPサーバ使用者
  - ジョブ実行ログの取得
  - 大容量ファイルの転送（SFTP）
  - 長時間のコンパイル・実行処理
- **PM/SE**: 必要に応じて使用
  - 環境調査時のコマンド実行
  - 予算確認用コマンド

### MCPサーバ不使用対象
- **CD**: 緊急時を除きSSH接続しない

### サブエージェントでの対応
大量データ通信が必要な場合は、`claude -p` によるサブエージェントで対応：
```bash
# 例：大容量ログの解析
cat huge_job_output.log | claude -p "エラーメッセージを抽出して要約"
```

## ディレクトリ構造の維持

### 重要な原則
- **リモート環境でもローカルと同じディレクトリ階層を維持**
- これによりmakefileや.bashrcの混同を防ぐ
- directory_pane_map.txtの階層を再現することを推奨

### 階層再現の範囲
- エージェント配置ディレクトリまでは厳密に再現
- PGが作成する下位階層は、実行に影響なければ自由

## wcgw初期設定手順（PG用）

### 1. thread_id作成の担当
- **2段階認証がある場合**: PMが主導（ユーザとの対話が必要）
  - サブエージェント（`claude -p`）を活用して効率化
- **2段階認証がない場合**: 各PGが自分用のthread_idを作成
  - 必要に応じて追加作成（全員が5個作るのは避ける）

### 2. thread_id作成手順
```bash
# 各PGエージェントが自分用に1-2個作成
# wcgwでinitialize実行
# thread_id_PG1.1.1_main, thread_id_PG1.1.1_backup など命名
```

### 3. thread_idの管理
- 各PGエージェントが自分のthread_idを管理
- 必要に応じて追加作成
- 各PGのローカルディレクトリにwcgw_thread_id_list.txtを作成・更新

## MCP設定の運用

### 現在の方針
- プロジェクトレベル（-s project）の.mcp.jsonは使用しない
  - 許可が毎回求められる問題
  - .mcp.jsonが読み込まれないバグ
- ローカルスコープ（デフォルト）で各エージェントごとに設定

### エージェント割り当て時の手順
```bash
# 方法1: MCP不要な場合（PG等）
agent_send.sh PG1.1.1 "!cd Flow/TypeII/single-node/gcc11.3.0/OpenMP && claude --dangerously-skip-permissions"

# 方法2: MCP必要な場合（PM/SE/PG）- 事前設定方式
# 1. 該当tmuxペインでMCPサーバを事前追加（Claude起動前）
claude mcp add desktop-commander -- npx -y @wonderwhy-er/desktop-commander
# 2. その後Claude Codeを起動
claude --dangerously-skip-permissions
# 注: exitやrestartは不要（MCPは起動前に設定済みのため）
```

## 効率化のヒント

### PGエージェントの事前準備
1. プロジェクト開始時にPGエージェントのMCP設定を一括実行
2. エージェント停止時は`start_agent.sh`で再起動
   - `./communication/start_agent.sh [AGENT_ID] [DIR] --continue`で記憶を維持
3. 必要に応じて接続情報を共有

### 緊急時の対応
- PM/SEが一時的にSSH接続する場合は、MCP経由を推奨
- 2段階認証がある場合はMCP必須

## まとめ

MCPサーバ（wcgw、DesktopCommanderなど）は主にPGエージェントが使用し、PM/SEも必要に応じて使用します。この運用により、効率的なSSH接続管理とコンテキスト消費の最適化を実現します。