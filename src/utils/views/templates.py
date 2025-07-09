def get_emojis(emoji_style):
    """Emoji stiline göre emoji setini döndürür"""
    emoji_sets = {
        "modern": {
            "rules": "📋", "announcements": "📢", "roles": "👑", "intro": "👋",
            "chat": "💬", "gaming": "🎮", "voice": "🔊", "management": "⚙️",
            "music": "🎵", "events": "🎉", "support": "🆘", "logs": "📊",
            "forum": "🧠", "clips": "📹", "images": "📷", "videos": "🎥"
        },
        "colorful": {
            "rules": "📜", "announcements": "📣", "roles": "🎭", "intro": "🌟",
            "chat": "💭", "gaming": "🕹️", "voice": "🎤", "management": "🛠️",
            "music": "🎧", "events": "🎊", "support": "🤝", "logs": "📈",
            "forum": "💡", "clips": "🎬", "images": "🖼️", "videos": "🎞️"
        },
        "gaming": {
            "rules": "⚔️", "announcements": "🏆", "roles": "🎯", "intro": "🎮",
            "chat": "💬", "gaming": "🎮", "voice": "🔥", "management": "👑",
            "music": "🎵", "events": "🏅", "support": "🛡️", "logs": "📊",
            "forum": "⚡", "clips": "🎯", "images": "🖌️", "videos": "🎦"
        },
        "minimal": {
            "rules": "•", "announcements": "•", "roles": "•", "intro": "•",
            "chat": "•", "gaming": "•", "voice": "•", "management": "•",
            "music": "•", "events": "•", "support": "•", "logs": "•",
            "forum": "•", "clips": "•", "images": "•", "videos": "•"
        },
        "business": {
            "rules": "📄", "announcements": "📢", "roles": "💼", "intro": "🤝",
            "chat": "💼", "gaming": "🎯", "voice": "📞", "management": "👔",
            "music": "🎵", "events": "📅", "support": "📞", "logs": "📊",
            "forum": "💡", "clips": "📹", "images": "🖼️", "videos": "🎥"
        }
    }
    return emoji_sets.get(emoji_style, emoji_sets["modern"])

def get_headers(header_style):
    """Header stiline göre kategori başlıklarını döndürür"""
    header_styles = {
        "classic": {"prefix": "┌─── ", "suffix": " ───┐"},
        "modern": {"prefix": "╭─ ", "suffix": " ─╮"},
        "elegant": {"prefix": "◤ ", "suffix": " ◥"},
        "simple": {"prefix": "[ ", "suffix": " ]"},
        "gaming": {"prefix": "▸ ", "suffix": " ◂"},
        "minimal": {"prefix": "", "suffix": ""},
        "arrows": {"prefix": "➤ ", "suffix": " ◄"},
        "stars": {"prefix": "✦ ", "suffix": " ✦"}
    }
    return header_styles.get(header_style, header_styles["classic"])

def format_category_name(name, header_style):
    """Kategori adını header stiline göre formatlar"""
    headers = get_headers(header_style)
    return f"{headers['prefix']}{name.upper()}{headers['suffix']}"

def get_builtin_template(template_name, language="tr", emoji_style="modern", header_style="classic"):
    """Dahili template'leri döndürür"""
    emojis = get_emojis(emoji_style)
    
    templates = {
        "default": get_default_template(language, emojis, header_style),
        "gaming": get_gaming_template(language, emojis, header_style),
        "community": get_community_template(language, emojis, header_style),
        "business": get_business_template(language, emojis, header_style),
        "educational": get_educational_template(language, emojis, header_style),
        "streaming": get_streaming_template(language, emojis, header_style),
        "roleplay": get_roleplay_template(language, emojis, header_style)
    }
    
    return templates.get(template_name, templates["default"])

def get_default_template(language, emojis, header_style):
    if language == "tr":
        return {
            "name": "Varsayılan Sunucu",
            "description": "Genel amaçlı sunucu şablonu",
            "categories": [
                {
                    "name": format_category_name("HOŞ GELDİN", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・kurallar", "type": "text"},
                        {"name": f"{emojis['announcements']}・duyurular", "type": "text"},
                        {"name": f"{emojis['roles']}・roller", "type": "text"},
                        {"name": f"{emojis['intro']}・kendini-tanıt", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("GENEL", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・sohbet", "type": "text"},
                        {"name": f"{emojis['forum']}・tartışmalar", "type": "text"},
                        {"name": f"{emojis['support']}・destek", "type": "text"},
                        {"name": f"{emojis['voice']} Genel Sohbet", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("MEDYA", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['images']}・görseller", "type": "text"},
                        {"name": f"{emojis['videos']}・videolar", "type": "text"},
                        {"name": f"{emojis['clips']}・klipler", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("YÖNETİM", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['management']}・yönetim", "type": "text"},
                        {"name": f"{emojis['logs']}・loglar", "type": "text"},
                        {"name": "🔒 Yetkili Odası", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 Kurucu", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🛡️ Admin", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "⚡ Moderatör", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "🌟 VIP", "color": 0x9b59b6, "hoist": True, "mentionable": False},
                {"name": "📺 Yayıncı", "color": 0x8B4BFF, "hoist": True, "mentionable": False},
                {"name": "🎮 Oyuncu", "color": 0x2ecc71, "hoist": False, "mentionable": False},
                {"name": "✅ Doğrulandı", "color": 0x2ecc71, "hoist": False, "mentionable": False}
            ]
        }
    else:  # English
        return {
            "name": "Default Server",
            "description": "General purpose server template",
            "categories": [
                {
                    "name": format_category_name("WELCOME", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・rules", "type": "text"},
                        {"name": f"{emojis['announcements']}・announcements", "type": "text"},
                        {"name": f"{emojis['roles']}・roles", "type": "text"},
                        {"name": f"{emojis['intro']}・introductions", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("GENERAL", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・general-chat", "type": "text"},
                        {"name": f"{emojis['forum']}・discussions", "type": "text"},
                        {"name": f"{emojis['support']}・support", "type": "text"},
                        {"name": f"{emojis['voice']} General Voice", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("MEDIA", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['images']}・images", "type": "text"},
                        {"name": f"{emojis['videos']}・videos", "type": "text"},
                        {"name": f"{emojis['clips']}・clips", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("MANAGEMENT", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['management']}・staff", "type": "text"},
                        {"name": f"{emojis['logs']}・logs", "type": "text"},
                        {"name": "🔒 Staff Room", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 Founder", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🛡️ Admin", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "⚡ Moderator", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "🌟 VIP", "color": 0x9b59b6, "hoist": True, "mentionable": False},
                {"name": "📺 Streamer", "color": 0x8B4BFF, "hoist": True, "mentionable": False},
                {"name": "🎮 Gamer", "color": 0x2ecc71, "hoist": False, "mentionable": False},
                {"name": "✅ Verified", "color": 0x2ecc71, "hoist": False, "mentionable": False}
            ]
        }

def get_gaming_template(language, emojis, header_style):
    if language == "tr":
        return {
            "name": "Oyun Sunucusu",
            "description": "Oyuncular için özel sunucu şablonu",
            "categories": [
                {
                    "name": format_category_name("HOŞ GELDİN", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・kurallar", "type": "text"},
                        {"name": f"{emojis['announcements']}・duyurular", "type": "text"},
                        {"name": f"{emojis['roles']}・roller", "type": "text"},
                        {"name": "🎮・oyun-rolleri", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("OYUNLAR", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🎯・valorant", "type": "text"},
                        {"name": "⚔️・league-of-legends", "type": "text"},
                        {"name": "🔫・counter-strike", "type": "text"},
                        {"name": "🏗️・minecraft", "type": "text"},
                        {"name": "🌌・genshin-impact", "type": "text"},
                        {"name": f"{emojis['gaming']} Oyun Odası 1", "type": "voice"},
                        {"name": f"{emojis['gaming']} Oyun Odası 2", "type": "voice"},
                        {"name": f"{emojis['gaming']} Oyun Odası 3", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("GENEL", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・sohbet", "type": "text"},
                        {"name": f"{emojis['gaming']}・oyuncu-arama", "type": "text"},
                        {"name": f"{emojis['clips']}・klipler", "type": "text"},
                        {"name": f"{emojis['events']}・turnuvalar", "type": "text"},
                        {"name": f"{emojis['voice']} Genel Sohbet", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 Clan Leader", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🛡️ Admin", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "⚡ Moderatör", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "🏆 Pro Oyuncu", "color": 0xFF6B35, "hoist": True, "mentionable": False},
                {"name": "🎯 Valorant", "color": 0xFF4655, "hoist": False, "mentionable": False},
                {"name": "⚔️ League of Legends", "color": 0x0596AA, "hoist": False, "mentionable": False},
                {"name": "🔫 Counter-Strike", "color": 0xF79100, "hoist": False, "mentionable": False},
                {"name": "🏗️ Minecraft", "color": 0x00AA00, "hoist": False, "mentionable": False},
                {"name": "✅ Doğrulandı", "color": 0x2ecc71, "hoist": False, "mentionable": False}
            ]
        }
    else:  # English
        return {
            "name": "Gaming Server",
            "description": "Gaming focused server template",
            "categories": [
                {
                    "name": format_category_name("WELCOME", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・rules", "type": "text"},
                        {"name": f"{emojis['announcements']}・announcements", "type": "text"},
                        {"name": f"{emojis['roles']}・roles", "type": "text"},
                        {"name": "🎮・game-roles", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("GAMES", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🎯・valorant", "type": "text"},
                        {"name": "⚔️・league-of-legends", "type": "text"},
                        {"name": "🔫・counter-strike", "type": "text"},
                        {"name": "🏗️・minecraft", "type": "text"},
                        {"name": "🌌・genshin-impact", "type": "text"},
                        {"name": f"{emojis['gaming']} Game Room 1", "type": "voice"},
                        {"name": f"{emojis['gaming']} Game Room 2", "type": "voice"},
                        {"name": f"{emojis['gaming']} Game Room 3", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("GENERAL", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・general-chat", "type": "text"},
                        {"name": f"{emojis['gaming']}・looking-for-group", "type": "text"},
                        {"name": f"{emojis['clips']}・clips", "type": "text"},
                        {"name": f"{emojis['events']}・tournaments", "type": "text"},
                        {"name": f"{emojis['voice']} General Voice", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 Clan Leader", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🛡️ Admin", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "⚡ Moderator", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "🏆 Pro Gamer", "color": 0xFF6B35, "hoist": True, "mentionable": False},
                {"name": "🎯 Valorant", "color": 0xFF4655, "hoist": False, "mentionable": False},
                {"name": "⚔️ League of Legends", "color": 0x0596AA, "hoist": False, "mentionable": False},
                {"name": "🔫 Counter-Strike", "color": 0xF79100, "hoist": False, "mentionable": False},
                {"name": "🏗️ Minecraft", "color": 0x00AA00, "hoist": False, "mentionable": False},
                {"name": "✅ Verified", "color": 0x2ecc71, "hoist": False, "mentionable": False}
            ]
        }

def get_community_template(language, emojis, header_style):
    if language == "tr":
        return {
            "name": "Topluluk Sunucusu",
            "description": "Sosyal topluluk sunucu şablonu",
            "categories": [
                {
                    "name": format_category_name("KARŞILAMA", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・kurallar", "type": "text"},
                        {"name": f"{emojis['announcements']}・duyurular", "type": "text"},
                        {"name": f"{emojis['intro']}・tanışma", "type": "text"},
                        {"name": f"{emojis['roles']}・roller", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("TOPLULUK", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・genel-sohbet", "type": "text"},
                        {"name": f"{emojis['forum']}・tartışmalar", "type": "text"},
                        {"name": "📚・kitap-kulübü", "type": "text"},
                        {"name": "🎬・sinema-dizi", "type": "text"},
                        {"name": "🍕・yemek-tarifleri", "type": "text"},
                        {"name": f"{emojis['voice']} Sohbet Odası", "type": "voice"},
                        {"name": "📖 Kitap Okuma", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("ETKİNLİKLER", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['events']}・etkinlikler", "type": "text"},
                        {"name": "🎊・çekilişler", "type": "text"},
                        {"name": "🎂・doğum-günleri", "type": "text"},
                        {"name": "🎪 Etkinlik Odası", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("YARATICILIK", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🎨・sanat-galerisi", "type": "text"},
                        {"name": f"{emojis['music']}・müzik", "type": "text"},
                        {"name": "✍️・yazılar", "type": "text"},
                        {"name": "📷・fotoğrafçılık", "type": "text"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 Kurucu", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🛡️ Yönetici", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "⚡ Moderatör", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "🎉 Etkinlik Sorumlusu", "color": 0xf39c12, "hoist": True, "mentionable": True},
                {"name": "🌟 Aktif Üye", "color": 0x2ecc71, "hoist": True, "mentionable": False},
                {"name": "🎨 Sanatçı", "color": 0x9b59b6, "hoist": False, "mentionable": False},
                {"name": "📚 Okur", "color": 0x34495e, "hoist": False, "mentionable": False},
                {"name": "🎵 Müzisyen", "color": 0x1abc9c, "hoist": False, "mentionable": False},
                {"name": "✅ Doğrulandı", "color": 0x95a5a6, "hoist": False, "mentionable": False}
            ]
        }
    else:  # English
        return {
            "name": "Community Server",
            "description": "Social community server template",
            "categories": [
                {
                    "name": format_category_name("WELCOME", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・rules", "type": "text"},
                        {"name": f"{emojis['announcements']}・announcements", "type": "text"},
                        {"name": f"{emojis['intro']}・introductions", "type": "text"},
                        {"name": f"{emojis['roles']}・roles", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("COMMUNITY", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・general-chat", "type": "text"},
                        {"name": f"{emojis['forum']}・discussions", "type": "text"},
                        {"name": "📚・book-club", "type": "text"},
                        {"name": "🎬・movies-tv", "type": "text"},
                        {"name": "🍕・food-recipes", "type": "text"},
                        {"name": f"{emojis['voice']} Chat Room", "type": "voice"},
                        {"name": "📖 Book Reading", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("EVENTS", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['events']}・events", "type": "text"},
                        {"name": "🎊・giveaways", "type": "text"},
                        {"name": "🎂・birthdays", "type": "text"},
                        {"name": "🎪 Event Room", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("CREATIVITY", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🎨・art-gallery", "type": "text"},
                        {"name": f"{emojis['music']}・music", "type": "text"},
                        {"name": "✍️・creative-writing", "type": "text"},
                        {"name": "📷・photography", "type": "text"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 Founder", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🛡️ Admin", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "⚡ Moderator", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "🎉 Event Manager", "color": 0xf39c12, "hoist": True, "mentionable": True},
                {"name": "🌟 Active Member", "color": 0x2ecc71, "hoist": True, "mentionable": False},
                {"name": "🎨 Artist", "color": 0x9b59b6, "hoist": False, "mentionable": False},
                {"name": "📚 Reader", "color": 0x34495e, "hoist": False, "mentionable": False},
                {"name": "🎵 Musician", "color": 0x1abc9c, "hoist": False, "mentionable": False},
                {"name": "✅ Verified", "color": 0x95a5a6, "hoist": False, "mentionable": False}
            ]
        }

def get_business_template(language, emojis, header_style):
    if language == "tr":
        return {
            "name": "İş Sunucusu",
            "description": "Profesyonel iş ortamı şablonu",
            "categories": [
                {
                    "name": format_category_name("GENEL", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・politikalar", "type": "text"},
                        {"name": f"{emojis['announcements']}・duyurular", "type": "text"},
                        {"name": "ℹ️・şirket-bilgileri", "type": "text"},
                        {"name": f"{emojis['chat']}・genel", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("ÇALIŞMA", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "💼・projeler", "type": "text"},
                        {"name": "📊・raporlar", "type": "text"},
                        {"name": "📅・toplantılar", "type": "text"},
                        {"name": f"{emojis['support']}・it-destek", "type": "text"},
                        {"name": "🏢 Toplantı Odası", "type": "voice"},
                        {"name": "💻 Çalışma Odası", "type": "voice"},
                        {"name": "☎️ Görüşme Odası", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("DEPARTMANLAR", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "💰・finans", "type": "text"},
                        {"name": "📈・pazarlama", "type": "text"},
                        {"name": "👥・insan-kaynakları", "type": "text"},
                        {"name": "🔧・teknik", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("SOSYAL", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "☕・kahve-molası", "type": "text"},
                        {"name": "🎉・şirket-etkinlikleri", "type": "text"},
                        {"name": "🌟 Dinlenme Odası", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 CEO", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🏢 Üst Yönetim", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "📊 Departman Müdürü", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "👨‍💼 Takım Lideri", "color": 0xf39c12, "hoist": True, "mentionable": True},
                {"name": "💼 Kıdemli Çalışan", "color": 0x2ecc71, "hoist": True, "mentionable": False},
                {"name": "🆕 Yeni Çalışan", "color": 0x95a5a6, "hoist": False, "mentionable": False},
                {"name": "🤝 Müşteri", "color": 0x9b59b6, "hoist": False, "mentionable": False},
                {"name": "🔧 IT Destek", "color": 0x1abc9c, "hoist": False, "mentionable": True}
            ]
        }
    else:  # English
        return {
            "name": "Business Server",
            "description": "Professional business environment template",
            "categories": [
                {
                    "name": format_category_name("GENERAL", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・policies", "type": "text"},
                        {"name": f"{emojis['announcements']}・announcements", "type": "text"},
                        {"name": "ℹ️・company-info", "type": "text"},
                        {"name": f"{emojis['chat']}・general", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("WORK", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "💼・projects", "type": "text"},
                        {"name": "📊・reports", "type": "text"},
                        {"name": "📅・meetings", "type": "text"},
                        {"name": f"{emojis['support']}・it-support", "type": "text"},
                        {"name": "🏢 Meeting Room", "type": "voice"},
                        {"name": "💻 Work Room", "type": "voice"},
                        {"name": "☎️ Call Room", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("DEPARTMENTS", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "💰・finance", "type": "text"},
                        {"name": "📈・marketing", "type": "text"},
                        {"name": "👥・human-resources", "type": "text"},
                        {"name": "🔧・technical", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("SOCIAL", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "☕・coffee-break", "type": "text"},
                        {"name": "🎉・company-events", "type": "text"},
                        {"name": "🌟 Break Room", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 CEO", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🏢 Executive", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "📊 Department Manager", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "👨‍💼 Team Leader", "color": 0xf39c12, "hoist": True, "mentionable": True},
                {"name": "💼 Senior Employee", "color": 0x2ecc71, "hoist": True, "mentionable": False},
                {"name": "🆕 New Employee", "color": 0x95a5a6, "hoist": False, "mentionable": False},
                {"name": "🤝 Client", "color": 0x9b59b6, "hoist": False, "mentionable": False},
                {"name": "🔧 IT Support", "color": 0x1abc9c, "hoist": False, "mentionable": True}
            ]
        }

def get_educational_template(language, emojis, header_style):
    if language == "tr":
        return {
            "name": "Eğitim Sunucusu",
            "description": "Eğitim kurumları için şablon",
            "categories": [
                {
                    "name": format_category_name("BİLGİLENDİRME", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・kurallar", "type": "text"},
                        {"name": f"{emojis['announcements']}・duyurular", "type": "text"},
                        {"name": "📚・ders-programı", "type": "text"},
                        {"name": "🎓・mezun-öğrenciler", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("DERSLER", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🧮・matematik", "type": "text"},
                        {"name": "🔬・fen-bilimleri", "type": "text"},
                        {"name": "🌍・sosyal-bilimler", "type": "text"},
                        {"name": "🎨・sanat", "type": "text"},
                        {"name": "💻・bilgisayar", "type": "text"},
                        {"name": "🇬🇧・yabancı-dil", "type": "text"},
                        {"name": "🎓 Ders 1", "type": "voice"},
                        {"name": "🎓 Ders 2", "type": "voice"},
                        {"name": "🎓 Ders 3", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("ÇALIŞMA", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "📝・ödevler", "type": "text"},
                        {"name": "🔍・araştırma", "type": "text"},
                        {"name": "👥・grup-çalışması", "type": "text"},
                        {"name": "❓・soru-cevap", "type": "text"},
                        {"name": "📚 Kütüphane", "type": "voice"},
                        {"name": "🤝 Grup Çalışması", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("SOSYAL", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "💬・sohbet", "type": "text"},
                        {"name": "🎮・oyunlar", "type": "text"},
                        {"name": "🎉・etkinlikler", "type": "text"},
                        {"name": "🌟 Dinlenme", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👨‍🏫 Müdür", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "📚 Öğretmen", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "🎓 Asistan", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "📖 12. Sınıf", "color": 0x2ecc71, "hoist": True, "mentionable": False},
                {"name": "📗 11. Sınıf", "color": 0xf39c12, "hoist": True, "mentionable": False},
                {"name": "📘 10. Sınıf", "color": 0x9b59b6, "hoist": True, "mentionable": False},
                {"name": "📙 9. Sınıf", "color": 0x1abc9c, "hoist": True, "mentionable": False},
                {"name": "🎓 Mezun", "color": 0x95a5a6, "hoist": False, "mentionable": False}
            ]
        }
    else:  # English
        return {
            "name": "Educational Server",
            "description": "Educational institution template",
            "categories": [
                {
                    "name": format_category_name("INFORMATION", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・rules", "type": "text"},
                        {"name": f"{emojis['announcements']}・announcements", "type": "text"},
                        {"name": "📚・course-schedule", "type": "text"},
                        {"name": "🎓・alumni", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("SUBJECTS", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🧮・mathematics", "type": "text"},
                        {"name": "🔬・science", "type": "text"},
                        {"name": "🌍・social-studies", "type": "text"},
                        {"name": "🎨・arts", "type": "text"},
                        {"name": "💻・computer-science", "type": "text"},
                        {"name": "🇬🇧・languages", "type": "text"},
                        {"name": "🎓 Class 1", "type": "voice"},
                        {"name": "🎓 Class 2", "type": "voice"},
                        {"name": "🎓 Class 3", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("STUDY", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "📝・homework", "type": "text"},
                        {"name": "🔍・research", "type": "text"},
                        {"name": "👥・group-work", "type": "text"},
                        {"name": "❓・q-and-a", "type": "text"},
                        {"name": "📚 Library", "type": "voice"},
                        {"name": "🤝 Study Group", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("SOCIAL", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "💬・chat", "type": "text"},
                        {"name": "🎮・games", "type": "text"},
                        {"name": "🎉・events", "type": "text"},
                        {"name": "🌟 Lounge", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👨‍🏫 Principal", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "📚 Teacher", "color": 0xe74c3c, "hoist": True, "mentionable": True},
                {"name": "🎓 Assistant", "color": 0x3498db, "hoist": True, "mentionable": True},
                {"name": "📖 Senior", "color": 0x2ecc71, "hoist": True, "mentionable": False},
                {"name": "📗 Junior", "color": 0xf39c12, "hoist": True, "mentionable": False},
                {"name": "📘 Sophomore", "color": 0x9b59b6, "hoist": True, "mentionable": False},
                {"name": "📙 Freshman", "color": 0x1abc9c, "hoist": True, "mentionable": False},
                {"name": "🎓 Alumni", "color": 0x95a5a6, "hoist": False, "mentionable": False}
            ]
        }

def get_streaming_template(language, emojis, header_style):
    if language == "tr":
        return {
            "name": "Yayın Sunucusu",
            "description": "Yayıncılar ve izleyiciler için şablon",
            "categories": [
                {
                    "name": format_category_name("HOŞ GELDİN", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・kurallar", "type": "text"},
                        {"name": f"{emojis['announcements']}・duyurular", "type": "text"},
                        {"name": "📺・yayın-programı", "type": "text"},
                        {"name": f"{emojis['roles']}・roller", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("YAYINLAR", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🔴・canlı-yayın", "type": "text"},
                        {"name": "🎮・oyun-yayınları", "type": "text"},
                        {"name": "🎨・sanat-yayınları", "type": "text"},
                        {"name": "🎵・müzik-yayınları", "type": "text"},
                        {"name": "📱・irl-yayınları", "type": "text"},
                        {"name": "🎙️ Yayın Odası", "type": "voice"},
                        {"name": "⏳ Bekleme Odası", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("İÇERİK", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['clips']}・en-iyi-anlar", "type": "text"},
                        {"name": "📹・videolar", "type": "text"},
                        {"name": "🖼️・fan-art", "type": "text"},
                        {"name": "💡・içerik-önerileri", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("TOPLULUK", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・genel-sohbet", "type": "text"},
                        {"name": "🎉・etkinlikler", "type": "text"},
                        {"name": "🎁・çekilişler", "type": "text"},
                        {"name": "💰・bağışlar", "type": "text"},
                        {"name": f"{emojis['voice']} İzleyici Sohbeti", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "🎥 Ana Yayıncı", "color": 0xFF0000, "hoist": True, "mentionable": True},
                {"name": "🎬 Moderatör", "color": 0x8B4BFF, "hoist": True, "mentionable": True},
                {"name": "⚡ VIP Abone", "color": 0xFFD700, "hoist": True, "mentionable": False},
                {"name": "💎 Abone", "color": 0x9b59b6, "hoist": True, "mentionable": False},
                {"name": "🔔 Bildirim Açık", "color": 0xf39c12, "hoist": False, "mentionable": True},
                {"name": "🎮 Oyun Sever", "color": 0x2ecc71, "hoist": False, "mentionable": False},
                {"name": "🎨 Sanat Sever", "color": 0xe74c3c, "hoist": False, "mentionable": False},
                {"name": "🎵 Müzik Sever", "color": 0x1abc9c, "hoist": False, "mentionable": False},
                {"name": "👀 İzleyici", "color": 0x95a5a6, "hoist": False, "mentionable": False}
            ]
        }
    else:  # English
        return {
            "name": "Streaming Server",
            "description": "Template for streamers and viewers",
            "categories": [
                {
                    "name": format_category_name("WELCOME", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・rules", "type": "text"},
                        {"name": f"{emojis['announcements']}・announcements", "type": "text"},
                        {"name": "📺・stream-schedule", "type": "text"},
                        {"name": f"{emojis['roles']}・roles", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("STREAMS", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🔴・live-stream", "type": "text"},
                        {"name": "🎮・gaming-streams", "type": "text"},
                        {"name": "🎨・art-streams", "type": "text"},
                        {"name": "🎵・music-streams", "type": "text"},
                        {"name": "📱・irl-streams", "type": "text"},
                        {"name": "🎙️ Stream Room", "type": "voice"},
                        {"name": "⏳ Waiting Room", "type": "voice"}
                    ]
                },
                {
                    "name": format_category_name("CONTENT", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['clips']}・highlights", "type": "text"},
                        {"name": "📹・videos", "type": "text"},
                        {"name": "🖼️・fan-art", "type": "text"},
                        {"name": "💡・content-suggestions", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("COMMUNITY", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・general-chat", "type": "text"},
                        {"name": "🎉・events", "type": "text"},
                        {"name": "🎁・giveaways", "type": "text"},
                        {"name": "💰・donations", "type": "text"},
                        {"name": f"{emojis['voice']} Viewer Chat", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "🎥 Main Streamer", "color": 0xFF0000, "hoist": True, "mentionable": True},
                {"name": "🎬 Moderator", "color": 0x8B4BFF, "hoist": True, "mentionable": True},
                {"name": "⚡ VIP Subscriber", "color": 0xFFD700, "hoist": True, "mentionable": False},
                {"name": "💎 Subscriber", "color": 0x9b59b6, "hoist": True, "mentionable": False},
                {"name": "🔔 Notifications On", "color": 0xf39c12, "hoist": False, "mentionable": True},
                {"name": "🎮 Gaming Fan", "color": 0x2ecc71, "hoist": False, "mentionable": False},
                {"name": "🎨 Art Fan", "color": 0xe74c3c, "hoist": False, "mentionable": False},
                {"name": "🎵 Music Fan", "color": 0x1abc9c, "hoist": False, "mentionable": False},
                {"name": "👀 Viewer", "color": 0x95a5a6, "hoist": False, "mentionable": False}
            ]
        }

def get_roleplay_template(language, emojis, header_style):
    if language == "tr":
        return {
            "name": "Roleplay Sunucusu",
            "description": "Rol yapma oyunları için şablon",
            "categories": [
                {
                    "name": format_category_name("BAŞLANGIÇ", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・kurallar", "type": "text"},
                        {"name": "📖・hikaye", "type": "text"},
                        {"name": "👤・karakter-oluşturma", "type": "text"},
                        {"name": "✅・karakter-onayı", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("OYUN İÇİ", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🏰・merkez-şehir", "type": "text"},
                        {"name": "🌲・orman", "type": "text"},
                        {"name": "⛰️・dağlar", "type": "text"},
                        {"name": "🏖️・sahil", "type": "text"},
                        {"name": "🏚️・terk-edilmiş-yerler", "type": "text"},
                        {"name": "⚔️・savaş-alanı", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("YAŞAM", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🏠・evler", "type": "text"},
                        {"name": "🏪・dükkanlar", "type": "text"},
                        {"name": "🍺・taverna", "type": "text"},
                        {"name": "⛪・tapınak", "type": "text"},
                        {"name": "📚・kütüphane", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("OYUN DIŞI", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・ooc-sohbet", "type": "text"},
                        {"name": "❓・sorular", "type": "text"},
                        {"name": "💡・öneriler", "type": "text"},
                        {"name": "🎨・karakter-galerisi", "type": "text"},
                        {"name": f"{emojis['voice']} OOC Sohbet", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 Dungeon Master", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🎭 Hikaye Anlatıcısı", "color": 0x8B4BFF, "hoist": True, "mentionable": True},
                {"name": "⚔️ Savaşçı", "color": 0xe74c3c, "hoist": True, "mentionable": False},
                {"name": "🏹 Okçu", "color": 0x2ecc71, "hoist": True, "mentionable": False},
                {"name": "🔮 Büyücü", "color": 0x9b59b6, "hoist": True, "mentionable": False},
                {"name": "🛡️ Paladin", "color": 0xf39c12, "hoist": True, "mentionable": False},
                {"name": "🗡️ Haydut", "color": 0x34495e, "hoist": True, "mentionable": False},
                {"name": "🎶 Çırak", "color": 0x1abc9c, "hoist": True, "mentionable": False},
                {"name": "👤 Karakter Bekliyor", "color": 0x95a5a6, "hoist": False, "mentionable": False}
            ]
        }
    else:  # English
        return {
            "name": "Roleplay Server",
            "description": "Template for roleplay games",
            "categories": [
                {
                    "name": format_category_name("GETTING STARTED", header_style),
                    "verified_only": False,
                    "channels": [
                        {"name": f"{emojis['rules']}・rules", "type": "text"},
                        {"name": "📖・lore", "type": "text"},
                        {"name": "👤・character-creation", "type": "text"},
                        {"name": "✅・character-approval", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("IN-GAME", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🏰・central-city", "type": "text"},
                        {"name": "🌲・forest", "type": "text"},
                        {"name": "⛰️・mountains", "type": "text"},
                        {"name": "🏖️・coast", "type": "text"},
                        {"name": "🏚️・abandoned-places", "type": "text"},
                        {"name": "⚔️・battlefield", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("LIFE", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": "🏠・homes", "type": "text"},
                        {"name": "🏪・shops", "type": "text"},
                        {"name": "🍺・tavern", "type": "text"},
                        {"name": "⛪・temple", "type": "text"},
                        {"name": "📚・library", "type": "text"}
                    ]
                },
                {
                    "name": format_category_name("OUT-OF-CHARACTER", header_style),
                    "verified_only": True,
                    "channels": [
                        {"name": f"{emojis['chat']}・ooc-chat", "type": "text"},
                        {"name": "❓・questions", "type": "text"},
                        {"name": "💡・suggestions", "type": "text"},
                        {"name": "🎨・character-gallery", "type": "text"},
                        {"name": f"{emojis['voice']} OOC Voice", "type": "voice"}
                    ]
                }
            ],
            "roles": [
                {"name": "👑 Dungeon Master", "color": 0xFFD700, "hoist": True, "mentionable": True},
                {"name": "🎭 Storyteller", "color": 0x8B4BFF, "hoist": True, "mentionable": True},
                {"name": "⚔️ Warrior", "color": 0xe74c3c, "hoist": True, "mentionable": False},
                {"name": "🏹 Archer", "color": 0x2ecc71, "hoist": True, "mentionable": False},
                {"name": "🔮 Mage", "color": 0x9b59b6, "hoist": True, "mentionable": False},
                {"name": "🛡️ Paladin", "color": 0xf39c12, "hoist": True, "mentionable": False},
                {"name": "🗡️ Rogue", "color": 0x34495e, "hoist": True, "mentionable": False},
                {"name": "🎶 Bard", "color": 0x1abc9c, "hoist": True, "mentionable": False},
                {"name": "👤 Awaiting Character", "color": 0x95a5a6, "hoist": False, "mentionable": False}
            ]
        } 