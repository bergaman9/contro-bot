#!/usr/bin/env python3
"""
Migration script to merge legacy_users into users collection
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.database.connection import get_database

async def migrate_users_collection():
    """Migrate legacy_users to users collection"""
    
    print("🔄 Starting user collection migration...")
    
    try:
        # Get database connection
        db = get_database()
        print("✅ Database connected")
        
        # Get collections
        try:
            legacy_users = db['legacy_users']
            legacy_count = legacy_users.count_documents({})
            print(f"📊 Found {legacy_count} documents in legacy_users")
        except Exception as e:
            print(f"⚠️  No legacy_users collection found: {e}")
            legacy_count = 0
        
        users = db['users']
        users_count = users.count_documents({})
        print(f"📊 Found {users_count} documents in users")
        
        if legacy_count == 0:
            print("✅ No documents to migrate from legacy_users")
            return
        
        # Get all documents from legacy_users
        legacy_docs = list(legacy_users.find({}))
        print(f"📥 Retrieved {len(legacy_docs)} documents from legacy_users")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for doc in legacy_docs:
            try:
                # Check if user already exists in users collection
                existing_user = users.find_one({
                    'guild_id': doc.get('guild_id'),
                    'user_id': doc.get('user_id')
                })
                
                if existing_user:
                    print(f"⚠️  User {doc.get('user_id')} in guild {doc.get('guild_id')} already exists, skipping")
                    skipped_count += 1
                    continue
                
                # Transform document to match users collection format
                new_doc = {
                    'guild_id': doc.get('guild_id'),
                    'user_id': doc.get('user_id'),
                    'xp': doc.get('xp', 0),
                    'level': doc.get('level', 0),
                    'next_level_xp': doc.get('next_level_xp', 1000),
                    'messages': doc.get('messages', 0),
                    'voice_minutes': doc.get('voice_minutes', 0),
                    'registered': doc.get('registered', False),
                    'games': doc.get('games', []),
                    'last_active': doc.get('last_active', datetime.utcnow())
                }
                
                # Insert into users collection
                result = users.insert_one(new_doc)
                print(f"✅ Migrated user {doc.get('user_id')} in guild {doc.get('guild_id')} (ID: {result.inserted_id})")
                migrated_count += 1
                
            except Exception as e:
                print(f"❌ Error migrating user {doc.get('user_id')}: {e}")
                error_count += 1
        
        print(f"\n📊 Migration Summary:")
        print(f"   ✅ Migrated: {migrated_count}")
        print(f"   ⚠️  Skipped: {skipped_count}")
        print(f"   ❌ Errors: {error_count}")
        
        # Verify migration
        final_users_count = users.count_documents({})
        print(f"📊 Final users collection count: {final_users_count}")
        
        if migrated_count > 0:
            print("\n🗑️  Do you want to drop the legacy_users collection? (y/N): ", end="")
            response = input().strip().lower()
            
            if response == 'y':
                legacy_users.drop()
                print("✅ legacy_users collection dropped")
            else:
                print("ℹ️  legacy_users collection preserved")
        
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

async def backup_collections():
    """Create backup of both collections before migration"""
    
    print("💾 Creating backup...")
    
    try:
        db = get_database()
        
        # Create backup collections
        legacy_backup = db['legacy_users_backup']
        users_backup = db['users_backup']
        
        # Backup legacy_users
        try:
            legacy_docs = list(db['legacy_users'].find({}))
            if legacy_docs:
                legacy_backup.insert_many(legacy_docs)
                print(f"✅ Backed up {len(legacy_docs)} documents to legacy_users_backup")
        except Exception as e:
            print(f"⚠️  No legacy_users collection found: {e}")
        
        # Backup users
        try:
            users_docs = list(db['users'].find({}))
            if users_docs:
                users_backup.insert_many(users_docs)
                print(f"✅ Backed up {len(users_docs)} documents to users_backup")
        except Exception as e:
            print(f"⚠️  No users collection found: {e}")
        
        print("✅ Backup completed")
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        raise

if __name__ == "__main__":
    load_dotenv()
    
    async def main():
        print("🚀 User Collection Migration Tool")
        print("=" * 50)
        
        # Ask for backup
        print("💾 Do you want to create a backup before migration? (Y/n): ", end="")
        backup_response = input().strip().lower()
        
        if backup_response != 'n':
            await backup_collections()
        
        # Confirm migration
        print("\n⚠️  This will merge legacy_users into users collection.")
        print("Continue? (y/N): ", end="")
        confirm = input().strip().lower()
        
        if confirm == 'y':
            await migrate_users_collection()
        else:
            print("❌ Migration cancelled")
    
    asyncio.run(main()) 