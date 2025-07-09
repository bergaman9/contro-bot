# Contro Discord Bot - Eksiksiz Dosya Yapısı

```
bot/
├── LICENSE
├── README.md
├── SECURITY.md
├── main.py
├── requirements.txt
├── verify_deployment.py (silindi)
│
├── .venv/                          # Python sanal ortamı
│   ├── Scripts/
│   ├── Include/
│   ├── Lib/
│   └── pyvenv.cfg
│
├── api/                            # API modülleri
│   ├── __init__.py
│   ├── commands_api.py
│   ├── guilds_api.py
│   └── ping_api.py
│
├── cogs/                           # Bot komut modülleri
│   ├── bot_settings.py
│   ├── bump.py
│   ├── fun.py
│   ├── game_stats.py
│   ├── giveaways.py
│   ├── interface.py
│   ├── invites.py
│   ├── levelling.py
│   ├── logging.py
│   ├── moderation.py
│   ├── perplexity_chat.py
│   ├── register.py
│   ├── server_setup.py
│   ├── settings.py
│   ├── spin.py
│   ├── starboard.py
│   ├── temp_channels.py
│   ├── ticket.py
│   ├── updater.py
│   ├── utility.py
│   ├── version_control.py
│   └── welcomer.py
│
├── config/                         # Yapılandırma dosyaları
│   ├── config.json
│   └── version_config.json
│
├── data/                           # Veri dosyaları
│   ├── bergaman9.csv
│   ├── format.json
│   ├── versions.json
│   │
│   ├── Backgrounds/                # Arka plan görselleri
│   │   ├── byebye_blue.png
│   │   ├── byebye_dark.png
│   │   ├── byebye_green.png
│   │   ├── byebye_light.png
│   │   ├── byebye_purple.png
│   │   ├── byebye_red.png
│   │   ├── default_background.png
│   │   ├── welcome_blue.png
│   │   ├── welcome_dark.png
│   │   ├── welcome_green.png
│   │   ├── welcome_light.png
│   │   ├── welcome_purple.png
│   │   └── welcome_red.png
│   │
│   ├── content/                    # İçerik klasörü (boş)
│   │
│   ├── contents/                   # Markdown içerikler
│   │   ├── announcements.md
│   │   ├── channels.md
│   │   ├── commands.md
│   │   ├── roles.md
│   │   ├── rules.md
│   │   ├── server.md
│   │   ├── services.md
│   │   └── version.md
│   │
│   ├── fonts/                      # Font dosyaları
│   │   ├── Gotham-Black.otf
│   │   └── GothamNarrow-Bold.otf
│   │
│   ├── Temp/                       # Geçici dosyalar
│   │   └── level_card_336615299694460933.png
│   │
│   └── templates/                  # Şablon klasörü (boş)
│
├── docs/                           # Dokümantasyon klasörü (boş)
│
├── images/                         # Görsel dosyaları
│   ├── contro_bot_features.png
│   ├── default_background.png
│   ├── register_card_d563575f-39ba-45e2-b306-30e1e0af7cb3.png
│   ├── support_system_card_0705175a-3c57-4596-9e2a-02e23a0006fe.png
│   ├── support_system_card_12b1966f-32ec-4488-a0b4-b69a43a0a46b.png
│   ├── support_system_card_f65cfe75-4bc8-4888-b459-5995705d47d4.png
│   │
│   └── backgrounds/                # Arka plan görsel kopyaları
│       ├── byebye_blue.png
│       ├── byebye_dark.png
│       ├── byebye_green.png
│       ├── byebye_light.png
│       ├── byebye_purple.png
│       ├── byebye_red.png
│       ├── welcome_blue.png
│       ├── welcome_dark.png
│       ├── welcome_green.png
│       ├── welcome_light.png
│       ├── welcome_purple.png
│       └── welcome_red.png
│
├── logs/                           # Log dosyaları
│   ├── README.md
│   ├── game_stats.log
│   ├── giveaways.log
│   ├── invites.log
│   └── spin.log
│
├── scripts/                        # Yardımcı scriptler
│   ├── background_generator.py
│   ├── coin_emoji_creator.py
│   ├── contro_bot.service
│   ├── deploy_pi5.sh
│   ├── setup-git-hooks.ps1
│   ├── update.sh
│   │
│   └── git-hooks/                  # Git hook dosyaları
│       ├── post-commit
│       └── pre-commit
│
└── utils/                          # Yardımcı modüller
    ├── __init__.py
    ├── content_loader.py
    ├── error_handler.py
    ├── setup.py
    ├── steam.py
    ├── ticket_views.py
    │
    ├── class_utils/
    │   └── __init__.py
    │
    ├── commands/                   # Komut yardımcıları (boş)
    │
    ├── common/                     # Ortak yardımcılar
    │   ├── __init__.py
    │   ├── confirmations.py
    │   ├── messages.py
    │   ├── pagination.py
    │   └── selectors.py
    │
    ├── community/                  # Topluluk özel modülleri
    │   ├── __init__.py
    │   │
    │   └── turkoyto/
    │       ├── __init__.py
    │       ├── card_renderer.py
    │       ├── event_view.py
    │       ├── game_matching_view.py
    │       ├── level_view.py
    │       ├── registration_view.py
    │       ├── safe_db.py
    │       ├── temp_channel_manager.py
    │       ├── ticket_views.py
    │       └── xp_manager.py
    │
    ├── core/                       # Çekirdek modüller
    │   ├── __init__.py
    │   ├── class_utils.py
    │   ├── config.py
    │   ├── content_loader.py
    │   ├── db.py
    │   ├── discord_helpers.py
    │   ├── error_handler.py
    │   ├── formatting.py
    │   ├── helpers.py
    │   └── logger.py
    │
    ├── database/                   # Veritabanı modülleri
    │   ├── __init__.py
    │   ├── connection.py
    │   ├── content_manager.py
    │   └── db_manager.py
    │
    ├── discord_helpers/            # Discord yardımcıları
    │   ├── __init__.py
    │   └── giveaway.py
    │
    ├── formatting/                 # Formatlamı yardımcıları
    │   └── __init__.py
    │
    ├── greeting/                   # Karşılama sistemi
    │   ├── __init__.py
    │   ├── imaging.py
    │   │
    │   └── welcomer/
    │       ├── config_view.py
    │       ├── image_utils.py
    │       └── preview_generator.py
    │
    ├── imaging/                    # Görsel işleme
    │   └── __init__.py
    │
    ├── logs/                       # Uygulama logları
    │   ├── bot_2025-05-27.log
    │   ├── bot_2025-06-09.log
    │   ├── bot_2025-06-10.log
    │   ├── bot_2025-06-12.log
    │   ├── bot_2025-06-16.log
    │   ├── bot_2025-06-17.log
    │   ├── bot_2025-06-18.log
    │   ├── discord_2025-05-27.log
    │   ├── discord_2025-06-09.log
    │   ├── discord_2025-06-10.log
    │   ├── discord_2025-06-12.log
    │   ├── discord_2025-06-16.log
    │   ├── discord_2025-06-17.log
    │   └── discord_2025-06-18.log
    │
    ├── moderation/                 # Moderasyon yardımcıları
    │   └── __init__.py
    │
    ├── registration/               # Kayıt sistemi
    │   ├── __init__.py
    │   │
    │   └── views/
    │       └── __init__.py
    │
    ├── settings/                   # Ayarlar görünümleri
    │   ├── __init__.py
    │   ├── ai_moderation.py
    │   ├── channel_selector.py
    │   ├── logging_views.py
    │   ├── managers.py
    │   ├── perplexity_settings.py
    │   ├── register_views.py
    │   ├── role_views.py
    │   ├── server_views.py
    │   ├── temp_channels_view.py
    │   ├── ticket_view.py
    │   ├── ticket_views.py
    │   ├── views.py
    │   └── welcome_views.py
    │
    ├── setup/                      # Kurulum yardımcıları
    │   ├── __init__.py
    │   ├── templates.py
    │   ├── views.py
    │   │
    │   └── views/                  # Kurulum görünümleri (boş)
    │
    └── version/                    # Versiyon yönetimi
        ├── __init__.py
        ├── manager.py
        └── version_manager.py
```

## Toplam Dosya Sayısı

- **Python Dosyaları (.py):** 108 adet
- **Görsel Dosyaları (.png):** 32 adet
- **Yapılandırma Dosyaları (.json):** 4 adet
- **Markdown Dosyaları (.md):** 12 adet
- **Font Dosyaları (.otf):** 2 adet
- **Shell Script Dosyaları (.sh/.ps1):** 4 adet
- **Service Dosyası (.service):** 1 adet
- **CSV Dosyası (.csv):** 1 adet
- **Log Dosyaları (.log):** 18 adet
- **Git Hook Dosyaları:** 2 adet
- **Diğer Dosyalar:** 4 adet (LICENSE, requirements.txt, pyvenv.cfg)

**Toplam:** ~190 dosya (Python cache dosyaları hariç) 