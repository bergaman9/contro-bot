#!/usr/bin/env python3

"""
Test script for the enhanced ticket system
"""

import sys
import os
import asyncio
import importlib

# Add the bot directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_ticket_imports():
    """Test if all ticket system components can be imported successfully"""
    try:
        print("Testing ticket system imports...")
        
        # Test core ticket views import
        from utils.settings.ticket_views import (
            TicketSettingsView,
            CreateTicketMessageModal,
            TicketButtonManagementView,
            ExtraTicketMessagesModal,
            MessageFormatView,
            DeleteArchiveView,
            AutoArchiveModal,
            SetTicketCategoryModal,
            SetTicketLogChannelModal,
            SetSupportRolesModal,
            EditTicketFieldsModal,
            AddTicketButtonModal,
            EditTicketButtonModal,
            DeleteTicketButtonModal
        )
        print("✅ All ticket views imported successfully")
          # Test database connection
        from utils.database.connection import initialize_mongodb
        mongo_db = initialize_mongodb()
        db_available = mongo_db is not None
        print(f"✅ Database connection: {'Available' if db_available else 'Not Available'}")
        
        # Test ticket views initialization
        class MockBot:
            def __init__(self):
                pass
        
        mock_bot = MockBot()
        ticket_view = TicketSettingsView(mock_bot)
        print("✅ TicketSettingsView initialized successfully")
        
        # Test modal initialization
        create_modal = CreateTicketMessageModal(mock_bot)
        print("✅ CreateTicketMessageModal initialized successfully")
        
        button_mgmt_view = TicketButtonManagementView(mock_bot)
        print("✅ TicketButtonManagementView initialized successfully")
        
        extra_messages_modal = ExtraTicketMessagesModal(mock_bot)
        print("✅ ExtraTicketMessagesModal initialized successfully")
        
        print("🎉 All ticket system components are working correctly!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_translation():
    """Test if translations are applied correctly"""
    try:
        from utils.settings.ticket_views import TicketSettingsView
        
        class MockBot:
            pass
        
        mock_bot = MockBot()
        ticket_view = TicketSettingsView(mock_bot)
        
        # Check if button labels are in English
        buttons = []
        for item in ticket_view.children:
            if hasattr(item, 'label'):
                buttons.append(item.label)
        
        print("Button labels found:")
        for label in buttons:
            print(f"  - {label}")
              # Check for English labels
        english_buttons = [
            "Set Category", "Set Log Channel", "Set Support Roles", "Create Ticket Message",
            "Manage Ticket Fields", "Manage Ticket Buttons", "Set Message Format", 
            "Level Card Integration", "Auto Archive", "Extra Ticket Messages", 
            "Delete/Archive Options", "Ticket Statistics"
        ]
        
        found_english = any(btn in buttons for btn in english_buttons)
        if found_english:
            print("✅ English translations applied successfully")
            return True
        else:
            print("❌ English translations not found")
            return False
            
    except Exception as e:
        print(f"❌ Translation test error: {e}")
        return False

async def main():
    """Main test function"""
    print("Starting Ticket System Enhancement Tests")
    print("=" * 50)
    
    # Test imports
    import_success = await test_ticket_imports()
    print()
    
    # Test translations
    translation_success = await test_translation()
    print()
    
    if import_success and translation_success:
        print("🎉 All tests passed! The ticket system enhancement is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    asyncio.run(main())
