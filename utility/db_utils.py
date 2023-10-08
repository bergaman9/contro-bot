import discord

from .utils import initialize_mongodb, async_initialize_mongodb

async def fetch_buttons_from_db():
    return [
        {"label": "Destek", "data_source": "default"},
        {"label": "Yetkili Başvuru", "style": discord.ButtonStyle.blurple, "custom_id": "button_01", "data_source": "application"},
        {"label": "Öneri", "style": discord.ButtonStyle.green, "data_source": "suggest"},
    ]

def fetch_fields_from_db():
    return [
        {"label": "Destek almak istediğiniz konu nedir?", "placeholder": "Yanıtınızı giriniz."},
    ]

def fetch_application_fields_from_db():
    return [
        {"label": "İsim", "placeholder": "İsminizi giriniz."},
        {"label": "Yaş", "placeholder": "Yaşınızı giriniz.", "max_length": 2},
        {"label": "Sunucu", "placeholder": "Sunucu ID'nizi giriniz."},
        {"label": "Önceki Deneyim", "placeholder": "Önceki deneyiminizi giriniz."},
        {"label": "Neden Başvuruyorsunuz?", "placeholder": "Neden başvurduğunuzu giriniz.", "style": discord.TextStyle.paragraph},
    ]

def fetch_suggest_fields_from_db():
    return [
        {"label": "Öneri", "placeholder": "Önerinizi giriniz."},
    ]

async def fetch_buttons_from_db():
    mongo_db = await async_initialize_mongodb()
    cursor = mongo_db["buttons"].find({})
    buttons = await cursor.to_list(length=100)  # Replace 100 with the maximum number of documents you expect to retrieve
    return buttons

async def fetch_buttons_for_guild(guild_id):
    mongo_db = await async_initialize_mongodb()
    cursor = mongo_db["buttons"].find({"guild_id": str(guild_id)})
    buttons = await cursor.to_list(length=100)
    return buttons

async def fetch_fields_by_data_source(data_source):
    mongo_db = await async_initialize_mongodb()
    button = await mongo_db["buttons"].find_one({"data_source": data_source})
    return button.get("fields", []) if button else []

def insert_buttons_into_db():
    db = initialize_mongodb()
    buttons_collection = db['buttons']  # 'buttons' adlı koleksiyon üzerinde işlem yapmak için

    data_to_insert = [
        {
            "label": "Destek",
            "data_source": "default",
            "fields": [
                {"label": "Destek almak istediğiniz konu nedir?", "placeholder": "Yanıtınızı giriniz."},
            ]
        },
        {
            "label": "Yetkili Başvuru",
            "data_source": "application",
            "fields": [
                {"label": "İsim", "placeholder": "İsminizi giriniz."},
                {"label": "Yaş", "placeholder": "Yaşınızı giriniz.", "max_length": 2},
                {"label": "Sunucu", "placeholder": "Sunucu ID'nizi giriniz."},
                {"label": "Önceki Deneyim", "placeholder": "Önceki deneyiminizi giriniz."},
                {"label": "Neden Başvuruyorsunuz?", "placeholder": "Neden başvurduğunuzu giriniz.", "style": discord.TextStyle.paragraph},
            ]
        },
        {
            "label": "Öneri",
            "data_source": "suggest",
            "fields": [
                {"label": "Öneri", "placeholder": "Önerinizi giriniz."},
            ]
        },
    ]

    # Veriyi MongoDB'ye ekle
    result = buttons_collection.insert_many(data_to_insert)
    print(f"Inserted IDs: {result.inserted_ids}")


async def parse_interaction_data(interaction, *custom_ids):
    components = interaction.data['components']
    results = {}

    for component in components:
        if 'components' in component:
            for sub_component in component['components']:
                custom_id = sub_component['custom_id']
                if custom_id in custom_ids:
                    value = sub_component['value']
                    results[custom_id] = f"`{value}`"

    description = '\n'.join(results.values())
    return description



