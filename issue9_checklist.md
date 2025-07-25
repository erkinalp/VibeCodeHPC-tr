# Issue #9 チェックリスト

## 🤖CIエージェント
- [x] mcp起動が上手くいっていない(CI_wcgw_setup_by_SE → restart_agent_after_mcp_setup.shに改名)
- [x] fgではなくclaude --continue --dangerously-skip-permissionsで復帰
- [ ] wcgwサーバのBashCommandツールのみ、呼び出し型が合わず成功しない ※Claude Code側の問題

### wcgwの代替案
- [ ] 直接SSH（２段階認証では無理）
- [x] DesktopCommander MCPサーバ

## 🤖SE
- [ ] log_analyzerまで手が回っていない
- [ ] 複数のchanges.mdをまとめたレポートがほしい（タスク量的にPMよりSEを推奨）

## 🤖PM
- [x] directory_map.txtはリアルタイムなロボットの割当を反映してほしいので、PMはロボット割り当て直後に、即更新する
- [x] mapのフォルダとエージェントが識別困難なので、必ず絵文字📁と🤖で区別する
- [x] 最初にvisionを出力するのは良いがfuture_directory_map.txtとか別ファイルにしたい
- [x] 実際の進化的mkdirはランタイムで動的に行いたい
- [x] 序盤から待機エージェントを作るのは愚策

## その他
- [x] Pane上のエージェント対応表が機能していない
- [x] 実現策：claude🤖エージェント化
- [x] 名前：英語の２文字（大文字） → ID (Information Display)
- [x] PMが🤖を割り当てる度に、このエージェントに依頼するイベントドリブン形式

## 対応済み
- [x] setup.sh: cd $(pwd)をプロジェクトルートに修正（保留中）
- [x] PMの起動方法とセッション管理の修正
- [x] CI_wcgw_setup_by_SE.shをrestart_agent_after_mcp_setup.shに改名・修正