<div align="center">
  <h1>🚀 Contro Discord Bot Platformu</h1>
  <p><b>Gelişmiş, Modüler ve Arayüz Odaklı Bir Discord Bot Platformu</b></p>
  
  [![İngilizce](https://img.shields.io/badge/Language-English-blue)](README.md)
  [![Türkçe](https://img.shields.io/badge/Language-T%C3%BCrk%C3%A7e-red)](#)
  <br>
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/discord.py-2.7.1-blue?logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white" alt="MongoDB">
</div>

---

Contro, modern ve premium odaklı bir Discord bot platformudur. Tamamen modüler bir yapıda tasarlanmıştır, böylece topluluklar sadece istedikleri özellikleri seçip kullanabilir. Tüm yönetim işlemleri Web Dashboard üzerinden veya Discord içindeki yenilikçi ve etkileşimli /settings arayüzü ile yapılabilir.

## 🌐 Next.js Web Dashboard

Discord botu, **Next.js 15 Web Dashboard** ile kusursuz bir uyum içinde çalışır.
Sunucu yöneticileri gerçek zamanlı istatistikleri görebilir, karmaşık modülleri yapılandırabilir ve aboneliklerini doğrudan tarayıcı üzerinden yönetebilir. Tüm değişiklikler anında bota yansır.

👉 **[Web Dashboard'u Ziyaret Edin: controapp.vercel.app](https://controapp.vercel.app/)**

## 🌟 Temel Özellikler

- **🧩 %100 Modüler Mimari:** Moderasyondan Seviye sistemine kadar her şey bağımsız bir modüldür. Sadece ihtiyacınız olanları aktif edin.
- **🎛️ Arayüz Odaklı Yönetim:** Uzun komutlar yazmayı unutun. Tüm sunucunuzu /settings paneli içindeki açılır menüler, butonlar ve modallar ile kolayca yönetin.
- **💳 Premium ve Kripto Desteği:** Premium üyelikler ve kripto ödemeleri (BTC, ETH, USDC, USDT) için yerleşik destek.
- **🛡️ Üstün Güvenlik:** Sıkı yetkilendirme sınırlarıyla inşa edilmiştir. Büyük topluluklar için maksimum güvenliği sağlamak adına her işlem doğrulanır, denetlenir ve loglanır.
- **⚡ Yüksek Performans:** Verimlilik için özel tasarlandı. Ağır görevler arka planda işlenir, veritabanı (MongoDB) indekslemesi optimize edilmiştir ve görsel oluşturma işlemleri RAM dostudur.

## 🖼️ Dinamik Görsel Oluşturma

Contro, Karşılama ve Uğurlama etkinlikleri için anında ve markanıza özel, göz alıcı banner'lar oluşturabilen güçlü bir yerleşik görsel oluşturucuya sahiptir.

<div align="center">
  <img src="assets/welcome-banner.png" alt="Karşılama Banner Örneği" width="45%">
  <img src="assets/goodbye-banner.png" alt="Uğurlama Banner Örneği" width="45%">
</div>

## 🛠️ Modüller ve Tüm Komutlar

Contro, 20'den fazla yerleşik modülle birlikte gelir. Aşağıda botun sunduğu temel komutlar ve işlevler yer almaktadır:

### ⚙️ Çekirdek ve Yönetim
- /settings (veya /admin): Tüm modülleri yapılandırmak için etkileşimli yönetim panelini açar.
- /goal: Botun arka plan görevleri için kalıcı hedefler belirler.
- /schedule: Tekrarlayan etkinlikleri ve görevleri zamanlar.
- /ping: Botun anlık gecikme süresini (latency) ve durumunu kontrol eder.

### 🛡️ Moderasyon ve Güvenlik
- /purge all count: veya /clear amount:: Kanallardaki mesajları toplu şekilde silerek kolayca temizlik yapar.
- /ban add @user: Belirtilen kullanıcıyı sunucudan yasaklar.
- **Oto-Mod:** Spam, küfür ve oltalama (phishing) bağlantılarını anında yakalayan güçlü filtreler.
- **Denetim Kayıtları (Audit Logging):** Sunucudaki tüm aksiyonların detaylı loglanması.
- **Güvenlik Limitleri:** Hesabı çalınan yetkililerin sunucuya zarar vermesini (toplu ban/kick) otomatik engeller.

### 🎮 Etkileşim ve Topluluk
- **Seviye Sistemi (/rank, /leaderboard):** Hem metin hem de ses kanallarındaki aktiviteye göre üyeleri XP ve özel rol ödülleri ile ödüllendirir.
- **Çekilişler (/giveaway create prize: limit:):** Sadece birkaç tıklamayla çekilişler düzenleyin, katılımcı sınırları ve rol şartları belirleyin.
- **Rol Menüleri (Tepki Rolleri):** Kullanıcıların kendi rollerini butonlar ve menüler ile kolayca seçmelerini sağlayın.
- **Starboard:** Topluluğunuzdaki en iyi mesajları (en çok yıldız alanları) öne çıkarın.
- **Özel Komutlar (Custom Commands):** Kod yazmadan sunucunuza özel komutlar oluşturun.

### 🎫 Destek ve Araçlar
- **Destek Talepleri (/ticket):** Transkript, talep üstlenme (claiming) ve özel alt-kanallar barındıran gelişmiş ticket sistemi.
- **Geçici Ses Kanalları (/vc limit <sayı>):** İhtiyaç anında kendini oluşturan ve boşaldığında otomatik silinen ses kanalları. Üyeler kendi kanallarının limitini belirleyebilir.
- **Yapay Zeka Sohbet (/imagine prompt: vb.):** Akıllı ve yapay zeka destekli sohbetleri, görsel üretimini doğrudan sunucunuza entegre edin.

### 🎲 Eğlence ve Ekstralar
- /meme: En güncel ve komik capsleri (memes) getirir.
- /movie [isim]: Filmler hakkında bilgi ve puanlama getirir.
- /play [şarkı], /youtube: Müzik çalar veya YouTube videolarını aratır.
- /bump: Disboard üzerinde sunucunuzu öne çıkararak yeni üyeler kazanmanızı sağlar.
- /poll create: Üyeleriniz için etkileşimli anketler oluşturur.

---
*Not: Bu depo yalnızca tanıtım amaçlıdır. Contro'nun temel kaynak kodu, sistem güvenliğini korumak amacıyla gizli (private) bir depoda tutulmaktadır.*

