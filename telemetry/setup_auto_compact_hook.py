#!/usr/bin/env python3
"""
Auto-compact検出用のフック設定スクリプト
各エージェントの~/.claude/settings.jsonにPreCompactフックを追加
"""

import json
import os
from pathlib import Path
import argparse
from datetime import datetime

def create_settings_with_hook(agent_id: str, telemetry_dir: str = "/telemetry/auto_compact") -> dict:
    """Auto-compact検出用のsettings.json設定を生成"""
    
    # ログ記録用のコマンド
    # エージェントID、タイムスタンプ、セッションIDを記録
    log_command = (
        f"echo '[AUTO-COMPACT] agent_id={agent_id} "
        f"timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ) "
        f"session_id=$CLAUDE_CODE_SESSION_ID "
        f"tmux_pane=$TMUX_PANE' >> {telemetry_dir}/auto_compact.log"
    )
    
    settings = {
        "hooks": {
            "PreCompact": [
                {
                    "matcher": "auto",
                    "hooks": [
                        {
                            "type": "command",
                            "command": log_command
                        }
                    ]
                }
            ]
        }
    }
    
    return settings

def merge_settings(existing_settings: dict, new_settings: dict) -> dict:
    """既存の設定と新しい設定をマージ"""
    
    # 既存の設定のコピー
    merged = existing_settings.copy()
    
    # hooksセクションがない場合は作成
    if "hooks" not in merged:
        merged["hooks"] = {}
    
    # PreCompactフックがない場合は作成
    if "PreCompact" not in merged["hooks"]:
        merged["hooks"]["PreCompact"] = []
    
    # 新しいフックを追加（重複チェック）
    existing_matchers = [hook.get("matcher") for hook in merged["hooks"]["PreCompact"]]
    
    for new_hook in new_settings["hooks"]["PreCompact"]:
        if new_hook.get("matcher") not in existing_matchers:
            merged["hooks"]["PreCompact"].append(new_hook)
    
    return merged

def setup_hook_for_agent(agent_id: str, settings_dir: Path = None) -> bool:
    """特定のエージェントにフックを設定"""
    
    # 設定ディレクトリの決定
    if settings_dir is None:
        home = Path.home()
        settings_dir = home / ".claude"
    
    settings_dir.mkdir(exist_ok=True)
    settings_file = settings_dir / "settings.json"
    
    # プロジェクトルートからの相対パス
    project_root = Path(__file__).parent.parent
    telemetry_dir = project_root / "telemetry" / "auto_compact"
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    
    # 既存の設定を読み込み
    existing_settings = {}
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                existing_settings = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {settings_file}, creating new settings")
    
    # 新しいフック設定を作成
    new_settings = create_settings_with_hook(agent_id, str(telemetry_dir))
    
    # 設定をマージ
    final_settings = merge_settings(existing_settings, new_settings)
    
    # バックアップを作成
    if settings_file.exists():
        backup_file = settings_file.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        settings_file.rename(backup_file)
        print(f"Created backup: {backup_file}")
    
    # 新しい設定を保存
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(final_settings, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Auto-compact hook configured for agent: {agent_id}")
    print(f"  Settings file: {settings_file}")
    print(f"  Log file: {telemetry_dir}/auto_compact.log")
    
    return True

def create_hook_setup_script(project_root: Path) -> Path:
    """全エージェント用のフック設定スクリプトを生成"""
    
    script_path = project_root / "telemetry" / "setup_all_hooks.sh"
    
    script_content = """#!/bin/bash
# Auto-compact hook setup for all agents

TELEMETRY_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$TELEMETRY_DIR")"

echo "Setting up auto-compact hooks for all agents..."

# 各エージェントのホームディレクトリにsettings.jsonを作成
# （実際の環境では、各エージェントのセッション内で実行する必要があります）

cat << 'EOF'
⚠️  Important: Run the following command in each agent's session:

python $PROJECT_ROOT/telemetry/setup_auto_compact_hook.py --agent-id <AGENT_ID>

Example:
  For SE1: python $PROJECT_ROOT/telemetry/setup_auto_compact_hook.py --agent-id SE1
  For CI1.1: python $PROJECT_ROOT/telemetry/setup_auto_compact_hook.py --agent-id CI1.1
  For PG1.1.1: python $PROJECT_ROOT/telemetry/setup_auto_compact_hook.py --agent-id PG1.1.1

This will configure the PreCompact hook to log auto-compact events.
EOF
"""
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    
    return script_path

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='Setup auto-compact detection hook')
    parser.add_argument('--agent-id', required=True, help='Agent ID (e.g., SE1, CI1.1, PG1.1.1)')
    parser.add_argument('--settings-dir', type=Path, help='Override settings directory (default: ~/.claude)')
    
    args = parser.parse_args()
    
    # フックを設定
    success = setup_hook_for_agent(args.agent_id, args.settings_dir)
    
    if success:
        print("\n✅ Hook setup complete!")
        print("\nTo verify, check the settings file:")
        print(f"  cat ~/.claude/settings.json | jq '.hooks.PreCompact'")
    else:
        print("\n❌ Hook setup failed!")

if __name__ == "__main__":
    main()