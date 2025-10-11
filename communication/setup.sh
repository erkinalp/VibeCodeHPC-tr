#!/bin/bash

# Bu betik, yeni bir projenin kurulumunu gerçekleştirir.
# Gerekli bağımlılıkları kurar ve başlangıç ayarlarını yapar.

PROJECT_NAME="MyAwesomeProject"

# Proje dizinini oluştur
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

echo "$PROJECT_NAME kurulumu başlatılıyor..."

# Bağımlılıkları yükle
# (Örn: Python projesi için)
# pip install -r requirements.txt

# Başlangıç ayar dosyalarını oluştur
# (Örn: Ayar dosyasını kopyala)
# cp ../config.template.json ./config.json

# İzinleri ayarla
chmod +x setup.sh

# Tamamlandı mesajı
echo "Kurulum tamamlandı."
echo "Projeyi başlatmak için 'cd $PROJECT_NAME' komutunu çalıştırın."

# Hata yönetimi örneği
# if [ $? -ne 0 ]; then
#   echo "Hata: Kurulum sırasında bir sorun oluştu." >&2 # Türkçe hata mesajı
#   exit 1
# fi

