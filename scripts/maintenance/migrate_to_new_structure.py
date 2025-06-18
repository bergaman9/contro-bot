"""Script to migrate files to the new project structure."""

import os
import shutil
from pathlib import Path

# Define file mappings (simplified for key files)
FILE_MAPPINGS = {
    # API files
    "api/commands_api.py": "src/api/routes/commands.py",
    "api/guilds_api.py": "src/api/routes/guilds.py",
    "api/ping_api.py": "src/api/routes/health.py",
    
    # Move cogs by category
    "cogs/bot_settings.py": "src/cogs/admin/bot_management.py",
    "cogs/server_setup.py": "src/cogs/admin/server_setup.py",
    "cogs/settings.py": "src/cogs/admin/settings.py",
    
    "cogs/moderation.py": "src/cogs/moderation/actions.py",
    "cogs/logging.py": "src/cogs/moderation/logging.py",
    
    "cogs/levelling.py": "src/cogs/community/leveling.py",
    "cogs/register.py": "src/cogs/community/registration.py",
    "cogs/welcomer.py": "src/cogs/community/welcome.py",
    
    "cogs/fun.py": "src/cogs/fun/games.py",
    "cogs/utility.py": "src/cogs/utility/info.py",
}


def migrate_file(old_path: str, new_path: str):
    """Migrate a single file."""
    old = Path(old_path)
    new = Path(new_path)
    
    if old.exists():
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old, new)
        print(f"✓ Migrated: {old_path} -> {new_path}")
        return True
    else:
        print(f"✗ Not found: {old_path}")
        return False


def main():
    """Run the migration."""
    print("Starting file migration...")
    print("=" * 50)
    
    success_count = 0
    total_count = len(FILE_MAPPINGS)
    
    for old_path, new_path in FILE_MAPPINGS.items():
        if migrate_file(old_path, new_path):
            success_count += 1
    
    print("=" * 50)
    print(f"Migration complete: {success_count}/{total_count} files migrated")
    

if __name__ == "__main__":
    main() 