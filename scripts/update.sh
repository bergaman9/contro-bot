#!/bin/bash

# Contro Bot otomatik güncelleyici
# Bu betik, GitHub repo'da değişiklik olup olmadığını kontrol eder
# ve değişiklik varsa botu günceller

# Bot klasörüne git
cd /home/bergaman/Desktop/contro-bot || exit 1

echo "$(date): Güncelleme kontrolü başlatılıyor..."

# GitHub'dan son değişiklikleri çek ama henüz uygulama
git fetch origin main

# Yerel ve uzak commit hash'leri karşılaştır
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Güncelleme bulundu. Bot güncelleniyor..."
    
    # Değişiklikleri kaydet
    git pull origin main
    
    # Gereklilikleri güncelle
    pip install -r requirements.txt
    
    # Botu yeniden başlat (systemd kullanarak)
    echo "Bot yeniden başlatılıyor (systemd)..."
    sudo systemctl restart contro_bot
    
    echo "$(date): Bot güncellendi ve yeniden başlatıldı."
else
    echo "$(date): Güncelleme yok. Bot çalışmaya devam ediyor."
fi 