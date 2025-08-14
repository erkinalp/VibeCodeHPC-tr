# VibeCodeHPC エージェント配置マップ

## プロジェクト階層構造
```
VibeCodeHPC-GEMM📂
├── 🤖PM (プロジェクト管理)
├── directory_pane_map.md (このファイル - IDエージェント代替)
├── GitHub📁 🤖CD ⬛
└── Flow/TypeII📂
    ├── single-node📂 🤖SE1 🟨
    │   ├── gcc11.3.0📂 🤖CI1.1 🟦
    │   │   ├── OpenMP📁 🤖PG1.1.1 🟦
    │   │   ├── MPI📁 🤖PG1.1.2 🟦
    │   │   ├── AVX2📁
    │   │   └── OpenMP_MPI📁 (第2世代)
    │   ├── intel2024📂 🤖CI1.2 🟪
    │   │   ├── OpenMP📁 🤖PG1.2.1 🟪
    │   │   ├── MPI📁
    │   │   └── AVX512📁
    │   └── nvidia_hpc📂 🤖CI1.3 🟫
    │       ├── CUDA📁 🤖PG1.3.1 🟫
    │       └── OpenACC📁
    └── multi-node📂 🤖SE2 🟡
        ├── gcc11.3.0📂 🤖CI2.1 🔵
        │   ├── MPI📁 🤖PG2.1.1 🔵
        │   └── OpenMP📁
        └── intel2024📂
            └── MPI📁
```

## tmux配置図（Worker数:12のとき）
markdownを文字のまま表示するエディタ上でも見やすいように
以下のフォーマットを徹底し、空白文字で上下を揃えること

### tmux分割が1Windowで収まる場合（12/12ペイン - 4x3配置）
| Team1 | Workers1 | | |
|:---|:---|:---|:---|
| 🟨SE1     | 🟦CI1.1   | 🟦PG1.1.1 | 🟦PG1.1.2 |
| 🟪CI1.2   | 🟪PG1.2.1 | 🟫CI1.3   | 🟫PG1.3.1 |
| 🟡SE2     | 🔵CI2.1   | 🔵PG2.1.1 | ⬛CD      |

### 狭すぎて1Windowでは分割しきれない場合
`no space for new pane`エラーとなった際は自動で複数tmuxセッションを作成
※tmuxセッション：tmux Window = 1：1

#### Team1_Workers1（8/9ペイン - 3x3配置）
| Team1 | Workers1 | |
|:---|:---|:---|
| 🟨SE1     | 🟦CI1.1   | 🟦PG1.1.1 |
| 🟦PG1.1.2 | 🟪CI1.2   | 🟪PG1.2.1 |
| 🟫CI1.3   | 🟫PG1.3.1 | ⬜        |

#### Team1_Workers2（4/9ペイン - 3x3配置）
| Team1 | Workers2 | |
|:---|:---|:---|
| 🟡SE2     | 🔵CI2.1   | 🔵PG2.1.1 |
| ⬛CD      | ⬜        | ⬜        |
| ⬜        | ⬜        | ⬜        |

## 色凡例（優先度順）
### 四角絵文字（基本）
- 🟨 黄: SE1（single-node監視）
- 🟦 青: Team1.1（CI1.1/gcc系チーム）
- 🟪 紫: Team1.2（CI1.2/intel系チーム）
- 🟫 茶: Team1.3（CI1.3/nvidia系チーム）
- ⬛ 黒: CD（GitHub管理）
- ⬜ 白: 空きペイン

### 丸絵文字（色不足時）
- 🟡 金: SE2（multi-node監視）
- 🔵 青丸: Team2.1（CI2.1/multi-node gcc系）
- 🟣 紫丸: 追加チーム用（必要時）
- 🟤 茶丸: 追加チーム用（必要時）
