# ChangeLog PMオーバーライドテンプレート

**重要**: これはテンプレートファイルです。PMがプロジェクト開始時に、このテンプレートを参考にして
`ChangeLog_format_PM_override.md`を生成し、プロジェクト固有のルールを定義してください。

このドキュメントは、プロジェクトマネージャー（PM）が定義するOpenCodeAT全体での統一ルールの例を示します。
これらのルールは基本フォーマットに優先します。

## プロジェクト全体の統一事項（例）

### 1. ファイル名規則
- `ChangeLog.md`
- 各PGの作業ディレクトリ直下に配置

### 2. 性能指標の統一
※ PMがプロジェクトの種類に応じて定義してください

#### 行列計算系（例）
- **単位**: `MFLOPS` または `GFLOPS`
- **表記**: 小数点第1位まで（例: `8555.4 MFLOPS`）

#### シミュレーション系（例）
- **単位**: `iterations/sec` または実行時間 `seconds`
- **表記**: 用途に応じて適切な有効数字

### 3. request_id形式
```
[PGエージェントID]-[CIエージェントID]-[連番3桁]
```
例: `PG1.2.1-CI1.2-004`

### 4. 必須記載事項の追加

#### 全PG共通の必須params
- `nodes`: 使用ノード数
- 実行に使用した主要な並列化パラメータ（例: MPIプロセス数、スレッド数）

#### コンパイル警告の扱い
- compile statusが`warning`の場合、主要な警告内容をmessageに記載
- 警告が多い場合は`<details>`内に別途警告セクションを追加可能

### 5. SOTA（State of the Art）記録のルール

#### scope定義の明確化
- **local**: 該当PGディレクトリ内での最高記録
- **hardware**: 同一ハードウェア構成（例: Flow/TypeII/single-node）内での最高記録
- **project**: OpenCodeATプロジェクト全体での最高記録

#### SOTA更新時の記載
```markdown
- [x] **sota**
    - scope: `hardware`
    - previous: `7234.5 MFLOPS` ※任意
    - improvement: `+18.3%` ※任意
```

### 6. エラーハンドリングの統一

#### コンパイルエラー
- 主要なエラーメッセージを1-2行でmessageに記載
- 詳細はログファイルを参照

#### 実行時エラー
- セグメンテーションフォルトは `status: error, message: "Segmentation fault"`
- タイムアウトは `status: timeout`
- その他のエラーは具体的なメッセージを記載

### 7. 日本語記述の統一

#### 用語統一
- "実装" not "implementation"
- "並列化" not "parallelization"
- "最適化" not "optimization"
- "性能" not "performance"（ただしフィールド名は英語のまま）

#### コメントの書き方
- 実装の意図を明確に
- 失敗の原因分析を含める
- 次の改善点への示唆があれば記載

### 8. テンプレートの提供

新規PGエージェント作成時に、以下のテンプレートをChangeLog.mdとして配置：

```markdown
# [並列化モジュール名]📁 `ChangeLog.md`
🤖PG [エージェントID]  
- **ハードウェア**：[スパコン名] [タイプ]  
- **モジュール**：[コンパイラ情報]  

## Change Log

- 基本の型：`ChangeLog_format.md`に記載
- PMオーバーライド：`ChangeLog_format_PM_override.md`に記載
<details>
<summary>PGオーバーライド</summary>

[このPG固有のルールを記載]

</details>

---

[ここからバージョンエントリを追加]
```

## PMへの指示

このテンプレートを基に、以下の手順でプロジェクト固有のオーバーライドファイルを作成してください：

1. このファイルをコピーして `ChangeLog_format_PM_override.md` として保存
2. プロジェクトの特性に応じて各項目をカスタマイズ
3. 「（例）」の記載を実際の値に置き換え
4. プロジェクト固有のルールや制約を追加
5. 全エージェントに周知

## 更新履歴
- 2024-01-XX: テンプレート作成（changes.md → ChangeLog.md移行）