# Bütçe Takip Sistemi Yapılandırması

## HPC Kaynak Oranları Yapılandırması

HPC kaynak oranları artık kod değişikliği gerekmeden kolay güncellemeler için bir yapılandırma dosyasına aktarılmıştır.

### Yapılandırma Dosyası

**Konum**: `Agent-shared/budget/hpc_resource_rates.json`

### Format

```json
{
  "rates": {
    "kaynak-grubu-adı": {
      "gpu": <gpu_sayısı>,
      "rate": <saniye_başına_oran>,
      "description": "Opsiyonel açıklama"
    }
  },
  "default": {
    "gpu": <varsayılan_gpu_sayısı>,
    "rate": <varsayılan_oran>,
    "description": "Kaynak grubu bulunamadığında kullanılacak varsayılan oran"
  }
}
```

### Örnek

```json
{
  "rates": {
    "cx-small": {
      "gpu": 4,
      "rate": 0.007,
      "description": "Küçük hesaplama kaynağı"
    },
    "cx-large": {
      "gpu": 8,
      "rate": 0.010,
      "description": "Büyük hesaplama kaynağı"
    }
  },
  "default": {
    "gpu": 4,
    "rate": 0.007,
    "description": "Varsayılan hesaplama kaynağı oranı"
  }
}
```

### Oranları Güncelleme

HPC kaynak oranlarını güncellemek için:

1. `hpc_resource_rates.json` dosyasını düzenleyin
2. Gerektiğinde kaynak gruplarını ekleyin, değiştirin veya kaldırın
3. Dosyayı kaydedin
4. Bütçe takip sistemi bir sonraki çalıştırmada yeni oranları otomatik olarak yükleyecektir

### Yedek Davranış

Yapılandırma dosyası bulunamazsa veya ayrıştırılamazsa:
- Bütçe takip sistemi yerleşik varsayılan oranları kullanacaktır
- Sorunu belirlemeye yardımcı olmak için bir uyarı kaydedilecektir
- Sistem varsayılan değerlerle çalışmaya devam edecektir

### Hata İşleme

Bütçe takip sistemi kapsamlı hata işleme içerir:
- **JSON ayrıştırma hataları**: Ayrıntılarıyla kaydedilir, varsayılanlara geri döner
- **Eksik dosya**: Uyarı kaydedilir, yerleşik varsayılanları kullanır
- **G/Ç hataları**: Ayrıntılarıyla hata kaydedilir, varsayılanlara geri döner

Tüm hatalar, yapılandırma sorunlarının teşhisine yardımcı olmak için anlamlı mesajlarla kaydedilir.
