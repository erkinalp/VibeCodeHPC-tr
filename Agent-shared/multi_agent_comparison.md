# マルチエージェント比較の将来構想

## 概要
同一グラフ上で異なるエージェント構成の性能向上速度を比較する機能。
現在の`sota_visualizer.py`を拡張して実装予定。

## 比較パターン

### 1. エージェント数による比較
- **Single Agent**: PMが全タスクを実行（--singleオプション）
- **Few Agents** (2-4体): 最小構成のチーム
- **Standard** (8-12体): 標準的な構成
- **Many Agents** (16+体): 大規模チーム

### 2. 比較軸
- **横軸**: 実時間（プロジェクト開始からの経過時間）
- **縦軸**: SOTA性能（GFLOPS等）

### 3. グラフ表現
```
性能
 ↑
 │     ╱─── Many Agents (急速な立ち上がり)
 │   ╱───── Standard
 │ ╱─────── Few Agents
 │╱───────── Single Agent (緩やかな上昇)
 └────────────────→ 時間
```

## 実装方法

### リポジトリ間比較
異なるプロジェクト実行結果を統合比較：

```python
# 将来の実装例
class MultiProjectComparison:
    def __init__(self, project_dirs: List[Path]):
        """複数プロジェクトのディレクトリを指定"""
        self.projects = {}
        for dir in project_dirs:
            # 各プロジェクトのChangeLog.mdを収集
            self.projects[dir.name] = self.collect_project_data(dir)
    
    def plot_comparison(self):
        """同一グラフ上に複数プロジェクトの曲線を描画"""
        for project_name, data in self.projects.items():
            # 各プロジェクトのSOTA推移をプロット
            plt.plot(data['times'], data['values'], 
                    label=f"{project_name} ({data['agent_count']} agents)")
```

### メタデータの活用
`agent_and_pane_id_table.jsonl`からエージェント数を自動取得：

```python
def get_agent_count(project_root: Path) -> int:
    """プロジェクトのエージェント数を取得"""
    jsonl_path = project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
    if jsonl_path.exists():
        with open(jsonl_path) as f:
            agents = [json.loads(line) for line in f]
            # PM, SE, PG, CDの合計
            return len([a for a in agents if a.get('agent_id')])
    return 1  # シングルエージェントモード
```

## 期待される知見

### 1. 最適なエージェント数
- タスクの複雑さに応じた適正規模
- 収穫逓減の観点からの上限値

### 2. 並列化の効果
- エージェント数と性能向上速度の相関
- コミュニケーションオーバーヘッドの影響

### 3. コスト効率
- エージェント数あたりの性能向上率
- トークン消費量との関係

## 実装優先度
現時点では基本的なSOTA可視化（`sota_visualizer.py`）を優先。
フォーマットとPython仕様が固まれば、後から以下を実装：

1. プロジェクト間比較機能
2. エージェント構成のメタデータ統合
3. 統計的有意性の検証
4. コスト効率の可視化

## 使用例（将来）

```bash
# 複数プロジェクトの比較
python Agent-shared/multi_project_comparison.py \
    --projects ./run1_single ./run2_few ./run3_many \
    --output comparison_graph.png

# 同一条件での複数実行結果の統計処理
python Agent-shared/statistical_comparison.py \
    --pattern "./runs/*/ChangeLog.md" \
    --confidence 0.95
```