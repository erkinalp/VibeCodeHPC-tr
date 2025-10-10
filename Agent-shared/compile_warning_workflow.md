# Derleme uyarı metinlerinin işlenme iş akışı

## Genel Bakış
Paralelleştirme modülleri (OpenMP, MPI, CUDA vb.) için make sırasında üretilen uyarıları PG’ye uygun biçimde iletip, işin yürütülüp yürütülmeyeceğini belirleme mekanizması.

## Uygulama içeriği

### 1. ChangeLog.md formatının genişletilmesi
Aşağıdaki alanlar eklenir:
- `compile_status`: success | fail | **warning** | pending
- `compile_warnings`: Uyarı mesajlarının özeti
- `compile_output_path`: Derleme günlüğünün kayıt yolu

### 2. PG aracısının işlem akışı
1. **make yürütme çıktısının kaydı**
   ```bash
   make 2>&1 | tee /results/compile_v1.2.3.log
   ```

2. **Uyarıların analizi ve sınıflandırılması**
   - Paralelleştirmenin devre dışı bırakıldığı uyarısı (önem derecesi: yüksek)
   - Veri yarışması olasılığı (önem derecesi: yüksek)
   - Optimizasyon önerileri (önem derecesi: düşük)

3. **ChangeLog.md güncellemesi**
   `<details>`内の`message`欄に警告を記載：
   ```markdown
   - [x] **compile**
       - status: `warning`
       - message: "OpenMP: Döngü bağımlılığı uyarısı - collapse tümcesi optimize edilmeyebilir"
       - log: `/results/compile_v1.2.3.log`
   ```

4. **Uyarıların kaydı**
   ChangeLog.md içindeki message alanına uyarı içeriğini yazın

### 3. Uyarılar için karar kriterleri

#### İşi durdurması gereken uyarılar
- Döngü bağımlılığı nedeniyle paralelleştirmenin etkisiz olması
- Veri yarışmasına ilişkin uyarılar
- Bellek erişim deseni sorunları
- Paralelleştirme direktiflerinin yok sayılması

#### İzin verilebilir uyarılar
- Önerilen optimizasyon seviyeleri
- Performans iyileştirme önerileri
- Kullanımı önerilmeyen (deprecated) özelliklerle ilgili uyarılar

### 4. Uyarı örnekleri

#### OpenMP ile ilgili
```
warning: ignoring #pragma omp parallel for [-Wunknown-pragmas]
warning: loop not vectorized: loop contains data dependences
warning: collapse clause will be ignored because the loops are not perfectly nested
```

#### MPI ile ilgili
```
warning: MPI_Send/MPI_Recv may cause deadlock in this pattern
warning: collective operation in conditional branch may cause hang
```

#### CUDA ile ilgili
```
warning: __global__ function uses too much shared memory
warning: potential race condition in kernel execution
```

## Etkiler
- Gereksiz iş yürütmelerinin azaltılması
- Paralelleştirmenin doğru uygulanmadığı durumların erken tespiti
- Hesaplama kaynaklarının verimli kullanımı

## İşletimsel dikkatler
- Her uyarıda işi durdurmak gerekmez
- Uyarıların önem derecesini PG belirler
- Gerektiğinde compile_output_path altındaki günlük dosyasını inceleyin
