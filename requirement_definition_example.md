# Gereksinim Tanımı
(Requirement Definition)

## Proje Bilgileri
- **Proje adı**: tmux_demo1
- **Oluşturulma tarihi**: 2025-07-23

## Optimizasyon Kapsamı
### Kod edinim yöntemi
- [x] Yerel dosyalar: BaseCode/ altı

### Hedef dosyalar
- **Ana dosyalar**: mat-mat.c, mat-mat-d.c
- **Bağımlı dosyalar**: mat-mat-.bash, Makefile

## Optimizasyon derecesi (hedef)
### Performans hedefi
- **Hedef performans**: Teorik tepe performansa yaklaşmak

### Öncelikler
- [x] Çalışma süresini en aza indirme
- [ ] Bellek kullanımını en aza indirme
- [ ] Enerji verimliliğini en üst düzeye çıkarma
- [x] Ölçeklenebilirliği artırma
- [ ] Diğer:

## Özet
### Uygulama özeti
Birden çok matris boyutu için, MPI süreç sayısı 1–576 (düğüm sayısı 1–12) aralığında yürütme süresi ölçülecektir.
MPI süreç sayısı 1 için ölçülen süre 1 kabul edilerek 576 sürece kadar hızlanma (ölçek etkisi) grafiği oluşturulacaktır.

### Optimizasyon yaklaşımı
Aşağıdakiler paralel olarak ilerletilecektir:

(i) Mat-Mat (iletişim fonksiyonu gerektirmeyen) örnek programı paralelleştirilecektir.
Burada A, B, C matrisleri için başlangıç durumunda her PE’de kopyalı veri bulunmasına izin verilir.

(ii) Mat-Mat-d (bire bir iletişim fonksiyonu gerektirir)
MPI süreç sayısı 1’deki yürütme, (i)’deki sıralı matris çarpım süresi ölçülerek referans alınacaktır.

## 制約（指定）

### ハードウェア（サブシステム）
#### 選択されたスパコン
- **システム名**: 不老 (flow)

#### 利用可能なハードウェア
- [x] TypeI: 1~12ノード（1ジョブあたり）

### SSH先で使用するディレクトリ
_remote_info に記載

### ジョブリソース（ノード数）
#### 段階的スケールアップ
- 毎回1~576ノードで試す必要はありません
- デバッグ時は576ノードのみで試すなど、工夫してください
- 行列サイズも段階的に大きくし、実行に数時間もかかるジョブを投げないようにしてください

#### リソース制約
- 最大実行時間は、原則1分で利用してください
- 大規模なデータを取るときだけ、10分以下

#### ジョブ実行方式
- [x] バッチジョブ（推奨）
- [ ] インタラクティブジョブ
- [ ] ログインノードでの実行（非推奨）

### ミドルウェア（コンパイラ・並列化モジュール）
#### コンパイラ選択肢
- [x] GCC 10.4.0 (default)
- [x] fjmpi-gcc ※ログインノードでは利用不可、バッチジョブまたはインタラクティブジョブから利用

#### 並列化ライブラリ
- [x] MPI
- [x] OpenMP
- [x] ACLE (intrinsicなSIMD)

### 並列化戦略（実装順序や適用箇所）
#### 実装フェーズ
進化的探索（様々なアルゴリズムの考案・探索は各PGに任せます）

#### 適用箇所
主にmat-mat(-d).cのMy-mat-matとmain関数内での呼び出し前後

### 許容される精度（テストコード 指定/生成）
#### 精度要件
- [x] 既存テストと同精度

### 予算（ジョブ）
#### 計算資源予算
- **最低消費ライン**: 1,000ポイント
- **目安**: 3,000ポイント
- **上限**: 10,000ポイント
    TypeI：経過時間1秒につき0.0056ポイントに使用ノード数を乗じて得たポイント数
- 1円当たり0.8ポイントに換算

#### 制約
- 最大実行時間は、原則1分で利用してください
- 大規模なデータを取るときだけ、10分以下

### CD(Git Agent)を使用するか
#### GitHub連携
- [x] 使用する
- [ ] 使用しない
- [ ] 段階的導入

#### 通知設定
- 不要

## 追加要件・制約
### セキュリティ要件
- **機密レベル**: BaseCodeはGitHub（Privateリポジトリ）にコピー可能
- **データ保護**: スパコン・ユーザ情報はGitHubにpushする前に匿名化

### 互換性要件
- **他システム連携**: 特になし
- **結果フォーマット**: CSV形式で性能データを出力

### その他
- これはVibeCodeHPCのtmux並列エージェント自体のテストでもあります
#### CD
- GitHubを管理するCDエージェントは、性能に関わらず生成された全バージョンのコードもpushしてください
- commitはメッセージが書きやすい単位で行ってください
- GitHub/📁以下の.gitignoreはVibeCodeHPCプロジェクトルート直下のものをコピーし、必要に応じて修正してください
- このrequirement_definition.md等も匿名化してpushしてください。実際のIDを匿名化する.pyや.shをGit管轄外で作成し、使用しても構いません

---

## 自動生成情報（PM記入）
- **不足項目**: [自動記入]
- **推奨構成**: [自動記入]
- **初期エージェント配置**: [自動記入]
