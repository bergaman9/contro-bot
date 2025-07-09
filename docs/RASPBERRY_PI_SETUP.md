# Raspberry Pi Bot API Genel Erişim Rehberi

Bu rehber, Raspberry Pi'nizde çalışan Discord bot'unuzun API'sini internetten erişilebilir hale getirme adımlarını açıklar.

## 🚀 Önerilen Çözüm: Cloudflare Tunnel (Ücretsiz ve Güvenli)

### Cloudflare Tunnel ile Güvenli Erişim

Cloudflare Tunnel, en güvenli ve kolay yöntemdir. Port forwarding veya IP açma gerektirmez.

```bash
# Cloudflared kurulumu (Raspberry Pi)
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared

# Cloudflare'e giriş yapın
cloudflared tunnel login

# Tunnel oluşturun
cloudflared tunnel create bot-api

# Tunnel'ı yapılandırın
nano ~/.cloudflared/config.yml
```

**config.yml içeriği:**
```yaml
tunnel: bot-api
credentials-file: /home/pi/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: your-bot-domain.your-domain.com
    service: http://localhost:8080
    originRequest:
      httpHostHeader: your-bot-domain.your-domain.com
  - service: http_status:404
```

```bash
# Tunnel'ı çalıştırın
cloudflared tunnel run bot-api

# Sistem servisi olarak kurulum
sudo cloudflared service install

# DNS kaydını ekleyin (otomatik)
cloudflared tunnel route dns bot-api your-bot-domain.your-domain.com
```

**Avantajları:**
- ✅ Ücretsiz
- ✅ Port forwarding gerektirmez
- ✅ DDoS koruması
- ✅ SSL/TLS otomatik
- ✅ Zero Trust entegrasyonu

---

## 🌐 Alternatif 1: Ngrok (Geliştirme için)

Hızlı test ve geliştirme için ngrok kullanabilirsiniz:

```bash
# Ngrok kurulumu
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz
tar xvzf ngrok-v3-stable-linux-arm64.tgz
sudo mv ngrok /usr/local/bin

# Auth token ekleyin (ngrok.com'dan alın)
ngrok config add-authtoken your_auth_token

# HTTP tunnel başlatın
ngrok http 8080
```

Dashboard .env dosyanızı güncelleyin:
```env
BOT_API_URL=https://abc123.ngrok.io
BOT_API_KEY=your-secure-api-key
```

**Sınırlamalar:**
- ⚠️ Ücretsiz plan sınırlı
- ⚠️ URL her yeniden başlatmada değişir
- ⚠️ Üretim için uygun değil

---

## 🔐 Alternatif 2: Tailscale VPN (Güvenli Private Network)

Tamamen private ve güvenli bağlantı için:

```bash
# Tailscale kurulumu
curl -fsSL https://tailscale.com/install.sh | sh

# Tailscale'e bağlanın
sudo tailscale up

# Device IP'sini alın
tailscale ip -4
```

Dashboard'ı da Tailscale ağında çalıştırın ve private IP kullanın:
```env
BOT_API_URL=http://100.x.x.x:8080  # Tailscale IP
BOT_API_KEY=your-secure-api-key
```

**Avantajları:**
- ✅ Tamamen güvenli
- ✅ Şifreleme
- ✅ Private network
- ✅ Kolay kurulum

---

## 🏠 Geleneksel Yöntem: DDNS + Port Forwarding

### 1. Dynamic DNS (DDNS) Kurulumu

#### No-IP Kullanarak (Ücretsiz)

```bash
# No-IP client kurulumu
sudo apt update
sudo apt install noip2

# No-IP hesap yapılandırması
sudo noip2 -C

# Servis olarak çalıştırma
sudo systemctl enable noip2
sudo systemctl start noip2
```

#### DuckDNS Kullanarak (Alternatif)

```bash
# DuckDNS script oluşturma
mkdir ~/duckdns
cd ~/duckdns
nano duck.sh
```

Duck.sh içeriği:
```bash
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=your-domain&token=your-token&ip=" | curl -k -o ~/duckdns/duck.log -K -
```

```bash
# Executable yapma ve cron job ekleme
chmod 700 duck.sh
crontab -e
# Şu satırı ekleyin: */5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1
```

### 2. Router Port Forwarding

Router ayarlarınızda:
- **İç IP:** Raspberry Pi IP'si (örn: 192.168.1.100)
- **İç Port:** 8080 (bot API portu)
- **Dış Port:** 8080 (veya güvenlik için farklı bir port)
- **Protokol:** TCP

### 3. SSL/HTTPS Kurulumu

#### Let's Encrypt ile Otomatik SSL

```bash
# Certbot kurulumu
sudo apt install certbot

# SSL sertifikası alma (standalone mode)
sudo certbot certonly --standalone -d your-domain.ddns.net

# SSL sertifikalarını bot'a entegre etme
# Bot main.py dosyasında SSL context ekleyin
```

#### Self-Signed SSL Sertifikası

```bash
# SSL sertifikası oluşturma
sudo apt install openssl
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Dosya izinlerini ayarlama
chmod 600 key.pem cert.pem
```

---

## 🛡️ Güvenlik Konfigürasyonu

### 1. API Key Güvenliği

Güçlü API key oluşturun:

```python
import secrets
import string

def generate_api_key(length=32):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

print(generate_api_key(64))  # 64 karakter güçlü key
```

### 2. Güvenlik Duvarı Ayarları

```bash
# UFW güvenlik duvarı kurulumu
sudo apt install ufw

# Sadece gerekli portları açma
sudo ufw allow ssh
sudo ufw allow 8080/tcp

# Rate limiting ekleyin
sudo ufw limit ssh
sudo ufw limit 8080/tcp

# Güvenlik duvarını etkinleştirme
sudo ufw enable

# Durum kontrolü
sudo ufw status verbose
```

### 3. Fail2ban Koruması

```bash
# Fail2ban kurulumu
sudo apt install fail2ban

# Bot API için jail konfigürasyonu
sudo nano /etc/fail2ban/jail.local
```

jail.local içeriği:
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[bot-api]
enabled = true
port = 8080
filter = bot-api
logpath = /home/pi/contro-bot/logs/api.log
maxretry = 3
bantime = 7200
```

---

## 🤖 Bot API Konfigürasyonu

### 1. Bot main.py'da API Server

Bot'unuzda API server otomatik olarak başlar. Eğer özel port istiyorsanız:

```python
# main.py içinde API port'u değiştirmek için
def run_api():
    uvicorn.run(api_app, host="0.0.0.0", port=8080, log_level="info")
```

### 2. Systemd Service Kurulumu

```bash
# Service dosyası oluşturma
sudo nano /etc/systemd/system/contro-bot.service
```

Service dosyası:
```ini
[Unit]
Description=Contro Discord Bot with API
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/contro-bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=/home/pi/contro-bot

# API port'u açık tutmak için
Environment=API_PORT=8080

[Install]
WantedBy=multi-user.target
```

```bash
# Servisi etkinleştirme
sudo systemctl daemon-reload
sudo systemctl enable contro-bot
sudo systemctl start contro-bot

# Durum kontrolü
sudo systemctl status contro-bot
```

---

## 📱 Dashboard Konfigürasyonu

Dashboard .env dosyanızı güncelleyin:

```env
# Local development için
BOT_API_URL=http://localhost:8080
BOT_API_KEY=your-secure-64-char-api-key

# Cloudflare Tunnel için
BOT_API_URL=https://your-bot-domain.your-domain.com
BOT_API_KEY=your-secure-64-char-api-key

# DDNS için
BOT_API_URL=https://your-bot.ddns.net:8080
BOT_API_KEY=your-secure-64-char-api-key
```

---

## 🧪 Test Etme

### API Endpoint'lerini Test Edin

```bash
# Health check
curl -H "Authorization: Bearer your-api-key" http://localhost:8080/api/health

# Bot commands
curl -H "Authorization: Bearer your-api-key" http://localhost:8080/api/commands

# Bot stats
curl -H "Authorization: Bearer your-api-key" http://localhost:8080/api/stats

# Guilds info
curl -H "Authorization: Bearer your-api-key" http://localhost:8080/api/guilds
```

### Dashboard'dan Test

Dashboard'a giriş yapın ve:
1. Commands sayfasını kontrol edin
2. Admin paneldeki bot stats'i kontrol edin
3. Server listesinin yüklendiğini kontrol edin

---

## 📊 Monitoring ve Logs

### 1. Bot Logları

```bash
# Bot loglarını izleme
sudo journalctl -u contro-bot -f

# API specific logları
tail -f /home/pi/contro-bot/logs/api.log
```

### 2. System Monitoring

```bash
# Resource monitoring
htop
iostat 1
free -h

# Network monitoring
netstat -tlnp | grep :8080
ss -tlnp | grep :8080
```

### 3. API Health Monitoring

Cron job ile API sağlığını kontrol edin:

```bash
# Health check script
nano ~/check_api_health.sh
```

```bash
#!/bin/bash
API_URL="http://localhost:8080/api/health"
API_KEY="your-api-key"

response=$(curl -s -H "Authorization: Bearer $API_KEY" $API_URL)
if [ $? -eq 0 ]; then
    echo "$(date): API is healthy" >> ~/api_health.log
else
    echo "$(date): API is down!" >> ~/api_health.log
    # Restart bot service
    sudo systemctl restart contro-bot
fi
```

```bash
chmod +x ~/check_api_health.sh

# Cron job ekleyin (her 5 dakikada bir kontrol)
crontab -e
# */5 * * * * /home/pi/check_api_health.sh
```

---

## 🔒 Gelişmiş Güvenlik (İsteğe Bağlı)

### 1. Cloudflare Zero Trust

Cloudflare Tunnel kullanıyorsanız, Zero Trust ile ek güvenlik:

1. Cloudflare Dashboard'a gidin
2. Zero Trust → Access → Applications
3. Yeni uygulama oluşturun
4. Bot API domain'inizi koruyun
5. Sadece sizin erişiminize izin verin

### 2. IP Whitelist

Sadece belirli IP'lerden erişime izin vermek için:

```python
# Bot API'de IP whitelist
ALLOWED_IPS = ["your.dashboard.ip", "your.home.ip"]

@app.middleware("http")
async def ip_whitelist(request, call_next):
    client_ip = request.client.host
    if client_ip not in ALLOWED_IPS:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    return await call_next(request)
```

### 3. Rate Limiting

API'ye hız sınırı ekleyin:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/commands")
@limiter.limit("10/minute")
async def get_commands(request: Request):
    # API endpoint implementation
```

---

## 🏁 Özet Checklist

### Cloudflare Tunnel (Önerilen)
- [ ] Cloudflared kuruldu
- [ ] Tunnel oluşturuldu ve yapılandırıldı
- [ ] DNS kaydı eklendi
- [ ] Bot API'si çalışıyor
- [ ] Dashboard'dan erişim test edildi

### Geleneksel DDNS
- [ ] DDNS servisi kuruldu
- [ ] Router port forwarding yapıldı
- [ ] SSL sertifikası alındı
- [ ] UFW firewall ayarlandı
- [ ] Fail2ban kuruldu

### Genel
- [ ] Bot API güvenlik ayarları yapıldı
- [ ] Systemd service oluşturuldu
- [ ] API key güvende
- [ ] Monitoring kuruldu
- [ ] Dashboard .env güncellendi
- [ ] Test başarılı

Bu rehberi takip ederek Discord bot'unuzun API'sini güvenli bir şekilde internetten erişilebilir hale getirebilirsiniz! Cloudflare Tunnel en güvenli ve kolay yöntemdir. 