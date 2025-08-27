#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC Stop Hook v3 for Polling Agents
ファイル内容の直接埋め込みとインテリジェントな選択
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


def find_project_root(start_path):
    """プロジェクトルート（VibeCodeHPC-jp）を探す"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def get_stop_count():
    """現在のディレクトリのstop_count.txtから回数を取得"""
    stop_count_file = Path.cwd() / ".claude" / "hooks" / "stop_count.txt"
    
    if stop_count_file.exists():
        try:
            return int(stop_count_file.read_text().strip())
        except:
            return 0
    return 0


def increment_stop_count():
    """stop_count.txtをインクリメント"""
    hooks_dir = Path.cwd() / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    stop_count_file = hooks_dir / "stop_count.txt"
    current_count = get_stop_count()
    new_count = current_count + 1
    
    stop_count_file.write_text(str(new_count))
    return new_count


def get_agent_info_from_cwd():
    """現在のディレクトリから自分のエージェント情報を取得"""
    # agent_id.txtから直接読み取り
    agent_id_file = Path.cwd() / ".claude" / "hooks" / "agent_id.txt"
    if agent_id_file.exists():
        agent_id = agent_id_file.read_text().strip()
        return {"agent_id": agent_id}
    
    # フォールバック：working_dirでマッチング
    cwd = Path.cwd()
    project_root = find_project_root(cwd)
    
    if not project_root:
        return None
    
    try:
        relative_dir = str(cwd.relative_to(project_root))
        if relative_dir == ".":
            relative_dir = ""
    except ValueError:
        relative_dir = str(cwd)
    
    table_file = project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
    
    if table_file.exists():
        with open(table_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                entry = json.loads(line)
                if entry.get('working_dir') == relative_dir:
                    return entry
    
    return None


def get_stop_threshold(agent_id):
    """エージェント種別ごとのSTOP回数閾値を返す"""
    if not agent_id:
        return 30
    
    project_root = find_project_root(Path.cwd())
    if project_root:
        threshold_file = project_root / "Agent-shared" / "stop_thresholds.json"
        if threshold_file.exists():
            try:
                with open(threshold_file, 'r') as f:
                    config = json.load(f)
                    thresholds = config.get('thresholds', {})
                    
                    # 完全一致をまず試す
                    if agent_id in thresholds:
                        return thresholds[agent_id]
                    
                    # プレフィックスマッチを試す
                    for prefix in ['PM', 'CD', 'SE', 'PG']:
                        if agent_id.startswith(prefix) and prefix in thresholds:
                            return thresholds[prefix]
            except:
                pass
    
    # フォールバック値
    if agent_id == "PM":
        return 50
    elif agent_id.startswith("CD"):
        return 40
    elif agent_id.startswith("SE"):
        return 30
    elif agent_id.startswith("PG"):
        return 20
    else:
        return 30


def load_config(project_root):
    """auto_tuning_config.jsonを読み込み"""
    config_file = project_root / "Agent-shared" / "strategies" / "auto_tuning" / "auto_tuning_config.json"
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # フォールバック設定
    return {
        "file_provision": {
            "always_full": [
                "requirement_definition.md",
                "Agent-shared/directory_pane_map.md",
                "CLAUDE.md"
            ],
            "periodic_full": [
                {"file": "instructions/{role}.md", "probability": 0.85},
                {"file": "ChangeLog.md", "probability": 0.75}
            ],
            "path_only": ["BaseCode/", "Agent-shared/strategies/"]
        },
        "agent_tasks": {}
    }


def should_provide_file(file_config, stop_count):
    """確率的にファイル提供を決定（決定論的実装）"""
    if isinstance(file_config, str):
        # always_fullの場合
        return True
    
    file_path = file_config.get("file", "")
    probability = file_config.get("probability", 0.5)
    
    # 確率を整数比に変換
    numerator = int(probability * 100)
    denominator = 100
    
    # ファイルパスのハッシュ値で分散
    hash_offset = hash(file_path) % denominator
    
    return ((stop_count + hash_offset) % denominator) < numerator


def read_file_content(file_path, project_root, max_lines=None):
    """ファイル内容を読み込み（ファイルタイプに応じた抽出）"""
    full_path = project_root / file_path
    
    if not full_path.exists():
        return None
    
    try:
        content = full_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # ChangeLog.mdの特別処理（最新エントリ優先）
        if file_path.endswith('ChangeLog.md'):
            entries = content.split('### v')
            if len(entries) > 1:
                recent = '### v' + '### v'.join(entries[1:min(3, len(entries))])
                return recent[:2000]
        
        # instructions/*.mdの特別処理（役割セクション優先）
        if 'instructions/' in file_path:
            # 主要責務と基本ワークフローを優先
            important_sections = []
            in_important = False
            for line in lines:
                if '## 📋 主要責務' in line or '## 🔄 基本ワークフロー' in line:
                    in_important = True
                elif line.startswith('## ') and in_important:
                    in_important = False
                if in_important:
                    important_sections.append(line)
            if important_sections and max_lines:
                return '\n'.join(important_sections[:max_lines])
        
        # CLAUDE.mdの特別処理（基本理念とコミュニケーション優先）
        if file_path.endswith('CLAUDE.md'):
            essential = []
            for i, line in enumerate(lines):
                if i < 30 or 'agent_send.sh' in line or '基本理念' in line:
                    essential.append(line)
                if len(essential) >= (max_lines or 50):
                    break
            return '\n'.join(essential)
        
        # 通常ファイルの処理
        if max_lines:
            # 先頭と重要そうなセクションを混合
            return '\n'.join(lines[:max_lines])
        
        # サイズ制限
        if len(content) > 3000:
            return content[:3000] + "\n...[以下省略]"
        
        return content
    except Exception as e:
        return f"[読み込みエラー: {str(e)}]"


def generate_embedded_content(stop_count, threshold, agent_id, project_root):
    """埋め込みコンテンツを生成"""
    config = load_config(project_root)
    
    # エージェントロールを取得
    role = agent_id.split('.')[0] if '.' in agent_id else agent_id
    
    embedded_parts = []
    reference_parts = []
    
    # 1. 常に全文提供
    embedded_parts.append("## 📄 必須ファイル内容\n")
    for file_path in config["file_provision"]["always_full"]:
        formatted_path = file_path.replace("{role}", role)
        content = read_file_content(formatted_path, project_root)
        if content:
            embedded_parts.append(f"### {formatted_path}")
            embedded_parts.append("```")
            embedded_parts.append(content)
            embedded_parts.append("```\n")
    
    # 2. 確率的に提供（periodic_full）
    provided_any = False
    for file_config in config["file_provision"]["periodic_full"]:
        if should_provide_file(file_config, stop_count):
            formatted_path = file_config["file"].replace("{role}", role)
            max_lines = file_config.get("max_lines")
            content = read_file_content(formatted_path, project_root, max_lines)
            if content:
                if not provided_any:
                    embedded_parts.append("\n## 📋 追加提供ファイル\n")
                    provided_any = True
                embedded_parts.append(f"### {formatted_path}")
                embedded_parts.append("```")
                embedded_parts.append(content)
                embedded_parts.append("```\n")
        else:
            # 提供しない場合はパス参照
            reference_parts.append(file_config["file"].replace("{role}", role))
    
    # 3. 低頻度で提供（rare_full）
    for file_config in config["file_provision"].get("rare_full", []):
        if should_provide_file(file_config, stop_count):
            formatted_path = file_config["file"].replace("{role}", role)
            max_lines = file_config.get("max_lines")
            content = read_file_content(formatted_path, project_root, max_lines)
            if content:
                if not provided_any:
                    embedded_parts.append("\n## 📋 追加提供ファイル\n")
                    provided_any = True
                embedded_parts.append(f"### {formatted_path}")
                embedded_parts.append("```")
                embedded_parts.append(content)
                embedded_parts.append("```\n")
        else:
            # 提供しない場合はパス参照
            reference_parts.append(file_config["file"].replace("{role}", role))
    
    if reference_parts:
        embedded_parts.append("\n## 📁 参照推奨ファイル（必要に応じて読み込み）\n")
        for path in reference_parts:
            embedded_parts.append(f"- {path}")
    
    # 4. メモリリセットの可能性を示唆
    if stop_count % 10 == 0:  # 10回ごと
        embedded_parts.append(f"\n{config['file_provision'].get('compact_recovery_hint', '')}")
    
    return '\n'.join(embedded_parts)


def get_agent_tasks(agent_id, config):
    """エージェント別のタスクリストを取得"""
    role = agent_id.split('.')[0] if '.' in agent_id else agent_id
    tasks = config.get("agent_tasks", {}).get(role, [])
    
    if not tasks:
        return ""
    
    task_list = "\n## 📌 必須タスク（全て確認）\n"
    for i, task in enumerate(tasks, 1):
        task_list += f"{i}. {task}\n"
    
    return task_list


def generate_block_reason(stop_count, agent_info):
    """ブロック理由を生成"""
    agent_id = agent_info.get('agent_id', 'unknown')
    threshold = get_stop_threshold(agent_id)
    project_root = find_project_root(Path.cwd())
    
    if not project_root:
        return "プロジェクトルートが見つかりません。"
    
    config = load_config(project_root)
    
    # 閾値到達時の処理
    if stop_count >= threshold:
        return f"""
⚠️ STOP回数が上限（{threshold}回）に達しました。

【終了準備】
1. 現在進行中のタスクを切りの良いところまで完了
2. ChangeLog.mdの最終更新
3. 作業ディレクトリの整理
4. 成果物の確認

最終報告:
agent_send.sh PM "[{agent_id}] 終了準備完了。主な成果: [ここに成果を記載]"

その後、PMからの指示（ESC強制中止/続投/転属）を待ってください。
10秒ごとにsleepしながら、定期的にPMに状況確認してください。
"""
    
    # 通常のブロック
    reason = f"""あなたはポーリング型のエージェント（{agent_id}）です。待機状態に入ることは許可されていません。
[STOP試行: {stop_count}/{threshold}]

"""
    
    # 埋め込みコンテンツを追加
    reason += generate_embedded_content(stop_count, threshold, agent_id, project_root)
    
    # エージェントタスクを追加
    reason += get_agent_tasks(agent_id, config)
    
    # 通信方法のリマインダー
    reason += f"""

## 🔄 次のアクション
1. 上記ファイル内容を確認
2. 必須タスクから優先度の高いものを選択
3. 実行開始
4. 進捗があればagent_send.shで報告

【重要】agent_send.shの使用方法：
プロジェクトルートからの相対パスまたは絶対パスで指定
例: ../../communication/agent_send.sh PM "[{agent_id}] タスク完了"

（残りSTOP試行可能回数: {threshold - stop_count}回）
"""
    
    return reason


def main():
    try:
        # JSONを読み込み
        input_data = json.load(sys.stdin)
        stop_hook_active = input_data.get('stop_hook_active', False)
        
        # エージェント情報を取得
        agent_info = get_agent_info_from_cwd()
        if not agent_info:
            agent_info = {'agent_id': 'unknown'}
        
        # STOP回数をインクリメント
        stop_count = increment_stop_count()
        
        # ブロック理由を生成
        reason = generate_block_reason(stop_count, agent_info)
        
        # 終了コード2でstderrに出力（Stopイベントをブロック）
        print(reason, file=sys.stderr)
        sys.exit(2)
        
    except Exception as e:
        # エラーは静かに処理
        sys.exit(0)


if __name__ == "__main__":
    main()