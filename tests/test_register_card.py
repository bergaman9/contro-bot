#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.community.turkoyto.card_renderer import create_register_card
from utils.database.connection import initialize_mongodb

async def test_register_card():
    try:
        # Initialize MongoDB
        mongo_db = initialize_mongodb()
        print("✅ MongoDB connected")
        
        # Create a mock guild object with necessary attributes
        class MockGuild:
            def __init__(self):
                self.id = 1234567890
                self.name = "Test Guild"
        
        guild = MockGuild()
        
        # Create the registration card
        print("🖼️ Creating registration card...")
        card_path = await create_register_card(None, guild, mongo_db)
        
        if card_path:
            print(f"✅ Registration card created successfully: {card_path}")
            if os.path.exists(card_path):
                print(f"📁 File exists and is {os.path.getsize(card_path)} bytes")
            else:
                print("❌ File was not created")
        else:
            print("❌ Failed to create registration card")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_register_card())
