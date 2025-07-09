#!/usr/bin/env python3
"""
Test script to create a simple ticket panel
"""
import asyncio
import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def create_test_panel():
    """Create a test ticket panel in the database"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGO_DB") or os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("❌ MONGO_DB environment variable not set")
        return
    
    client = MongoClient(mongo_uri)
    db = client.get_database()
    
    # Test guild ID (replace with your actual guild ID)
    guild_id = "505520771603496971"  # From the logs
    
    # Create test panel
    test_panel = {
        "id": str(int(datetime.now().timestamp())),
        "guild_id": guild_id,
        "name": "Test Support Panel",
        "channel_id": None,  # Will be set when deployed
        "message_id": None,  # Will be set when deployed
        "enabled": True,
        "buttons": [
            {
                "id": str(int(datetime.now().timestamp()) + 1),
                "label": "Create Support Ticket",
                "style": "primary",
                "emoji": "🎫",
                "custom_id": f"create_ticket_{int(datetime.now().timestamp()) + 1}",
                "department_id": None
            },
            {
                "id": str(int(datetime.now().timestamp()) + 2),
                "label": "Technical Support",
                "style": "danger",
                "emoji": "🔧",
                "custom_id": f"create_ticket_{int(datetime.now().timestamp()) + 2}",
                "department_id": "technical_issues"
            }
        ],
        "embed": {
            "title": "🎫 Support Ticket System",
            "description": "Need help? Create a support ticket by clicking one of the buttons below.\n\nOur team will assist you as soon as possible.",
            "color": "#5865F2",
            "footer": "Powered by Contro Bot",
            "timestamp": True,
            "thumbnail": True,
            "fields": [
                {
                    "name": "What is your issue about?",
                    "value": "Briefly describe your ticket subject",
                    "inline": False
                },
                {
                    "name": "Your contact information",
                    "value": "Your Discord username or email",
                    "inline": False
                },
                {
                    "name": "Detailed description",
                    "value": "Please describe your issue in detail...",
                    "inline": False
                }
            ]
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    try:
        # Insert the panel
        result = db.ticket_panels.insert_one(test_panel)
        print(f"✅ Test panel created successfully!")
        print(f"Panel ID: {test_panel['id']}")
        print(f"Database ID: {result.inserted_id}")
        print(f"Guild ID: {guild_id}")
        print(f"Buttons: {len(test_panel['buttons'])}")
        print(f"Form fields: {len(test_panel['embed']['fields'])}")
        
        # Also create a test department if it doesn't exist
        existing_dept = db.ticket_departments.find_one({"id": "technical_issues"})
        if not existing_dept:
            test_department = {
                "id": "technical_issues",
                "guild_id": guild_id,
                "name": "Technical Issues",
                "description": "Technical problems and bug reports",
                "emoji": "🔧",
                "category_id": None,
                "staff_roles": [],
                "auto_assign_staff": False,
                "welcome_message": "Welcome to Technical Support!\nPlease describe your issue in detail.",
                "button_style": "danger",
                "form_fields": [
                    {
                        "id": "issue_type",
                        "label": "Issue Type",
                        "type": "text",
                        "required": True,
                        "placeholder": "e.g., Bug, Feature Request, Performance Issue"
                    },
                    {
                        "id": "priority",
                        "label": "Priority Level",
                        "type": "text",
                        "required": True,
                        "placeholder": "Low, Medium, High, Critical"
                    },
                    {
                        "id": "description",
                        "label": "Detailed Description",
                        "type": "textarea",
                        "required": True,
                        "placeholder": "Please provide a detailed description of the issue..."
                    }
                ],
                "created_at": datetime.utcnow()
            }
            
            dept_result = db.ticket_departments.insert_one(test_department)
            print(f"✅ Test department created: {test_department['name']}")
            print(f"Department ID: {dept_result.inserted_id}")
        
        return test_panel['id']
        
    except Exception as e:
        print(f"❌ Error creating test panel: {e}")
        return None
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(create_test_panel()) 