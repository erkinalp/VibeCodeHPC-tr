# ChangeLog PM Geçersiz Kılma Örneği

**Dikkat**: Bu, `ChangeLog_format_PM_override.md` oluşturma örneğidir.
PM, gerçek projeye göre bu örneği referans alarak oluşturmalıdır.

Bu belge, temel format (`ChangeLog_format.md`) için **yalnızca ek kuralları** tanımlar.
Temel formatın yapısı değiştirilemez.

## PM Geçersiz Kılma Öğeleri

### 1. Performans Göstergelerinin Birleştirilmesi
- **Birimin belirtilmesi**: `test` bölümünün `unit` alanına mutlaka yazılmalıdır
  - Matris hesaplama: `GFLOPS` veya `MFLOPS`
  - Simülasyon: `iterations/sec` veya `seconds`
- **Gösterim hassasiyeti**: Ondalık noktadan sonra 1 basamak (örn: `285.7`)

### 2. Projeye Özgü Zorunlu params
Temel formatın `params` bölümüne aşağıdakiler eklenir:
- `compile_flags`: Kullanılan derleme seçenekleri (zorunlu)
- `mpi_processes`: MPI işlem sayısı (MPI kullanımında zorunlu)
- `omp_threads`: OpenMP iş parçacığı sayısı (OpenMP kullanımında zorunlu)

### 3. Derleme Uyarılarının İşlenmesi
`compile`'ın `status: warning` durumunda:
- Paralelleştirme ile ilgili uyarılar `message` alanında 1-2 satırda özetlenir
- Ayrıntı gerekiyorsa `compile_warnings` alanı eklenir (isteğe bağlı)

### 4. SOTA Güncellemesinde Ek Bilgi
`sota` bölümüne aşağıdakiler isteğe bağlı olarak eklenir:
- `previous`: Önceki kayıt değeri
- `improvement`: İyileştirme oranı (% gösterimi)

## Kayıt Örneği (matris hesaplama projesi)

```markdown
### v1.2.3
**Değişiklikler**: "OpenMP collapse(2) ve MPI bölge bölümleme uygulandı"  
**Sonuç**: Performans artışı doğrulandı `285.7`  
**Yorum**: "collapse cümlesi ile iç döngü de paralelleştirildi, MPI ile bölge bölümleme eklendi"  

<details>

- [x] **compile**
    - status: `warning`
    - message: "OpenMP: Bazı döngülerde paralelleştirme devre dışı bırakılıyor uyarısı"
    - compile_warnings: "loop at line 45: not vectorized due to data dependency"
    - log: `/results/compile_v1.2.3.log`
- [x] **job**
    - id: `12345`
    - status: `success`
- [x] **test**
    - status: `pass`
    - performance: `285.7`
    - unit: `GFLOPS`
- [x] **sota**
    - scope: `hardware`
    - previous: `241.3`
    - improvement: `+18.4%`
- **params**:
    - nodes: `4`
    - compile_flags: `-O3 -fopenmp -march=native`
    - mpi_processes: `16`
    - omp_threads: `8`

</details>
```

## Fark Özeti

Temel formattan eklenen noktalar:
1. `test`'in `unit` alanı (temel formata zaten eklendi)
2. `compile_warnings` alanı (isteğe bağlı)
3. `sota`'nın `previous` ve `improvement` alanları (isteğe bağlı)
4. `params`'ın `compile_flags`, `mpi_processes`, `omp_threads` alanları (koşullu zorunlu)

## Dikkat Edilmesi Gerekenler

1. **Markdown Yapısının Korunması**
   - `<details>` etiketi kesinlikle değiştirilmez
   - Alanların hiyerarşik yapısı korunur
   - Türkçe ile yazıma devam edilir
   - **Önemli**: PM'nin değiştirebileceği yalnızca `<details>` içindeki öğe alanlarıdır
   - **Katlanmış format (4 satır gösterim) mutlaka korunmalıdır**

2. **Python Analizi ile Uyumluluk**
   - Alan adları yalnızca yarım genişlik alfasayısal karakterler ve alt çizgi
   - Sayılar tırnak işareti olmadan yazılabilir
   - Birimler ayrı alanlara ayrılır

3. **İşletim Kuralları**
   - PM proje başlangıcında bu örneği referans alarak oluşturur
   - Ara değişiklikler minimumda tutulur
   - Tüm aracılara bildirim kesinlikle yapılır
   - PG aracıları katlanmış formatı kesinlikle korur

