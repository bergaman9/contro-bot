#!/usr/bin/env python3
"""
CONTRO Bot Deployment Verification Script
Verifies that all components are properly configured and ready for deployment.
"""

import os
import sys
import json
import importlib.util
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and return status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: Found")
        return True
    else:
        print(f"❌ {description}: Missing - {filepath}")
        return False

def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = ".env"
    if not os.path.exists(env_path):
        print("❌ Environment file: .env file not found")
        print("   Create .env file with: BOT_TOKEN, MONGODB_CONNECTION_STRING")
        return False
    
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    required_vars = ['BOT_TOKEN', 'MONGODB_CONNECTION_STRING']
    missing_vars = []
    
    for var in required_vars:
        if var not in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Environment variables missing: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ Environment file: All required variables present")
        return True

def check_python_version():
    """Check Python version compatibility."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python version: {version.major}.{version.minor}.{version.micro} (requires 3.10+)")
        return False

def check_dependencies():
    """Check if all required dependencies can be imported."""
    required_modules = [
        ('discord', 'discord.py'),
        ('pymongo', 'pymongo'),
        ('aiohttp', 'aiohttp'),
        ('PIL', 'Pillow'),
        ('dotenv', 'python-dotenv'),
        ('requests', 'requests'),
        ('flask', 'flask')
    ]
    
    all_good = True
    for module_name, package_name in required_modules:
        try:
            importlib.import_module(module_name)
            print(f"✅ Dependency: {package_name}")
        except ImportError:
            print(f"❌ Dependency: {package_name} not installed")
            all_good = False
    
    return all_good

def check_config_files():
    """Check configuration files."""
    config_files = [
        ('config/config.json', 'Main configuration'),
        ('config/version_config.json', 'Version configuration'),
        ('data/versions.json', 'Version data'),
        ('data/format.json', 'Format configuration')
    ]
    
    all_good = True
    for filepath, description in config_files:
        if not check_file_exists(filepath, description):
            all_good = False
        else:
            # Try to parse JSON
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"   └─ Valid JSON format")
            except json.JSONDecodeError as e:
                print(f"   └─ ❌ Invalid JSON: {e}")
                all_good = False
    
    return all_good

def check_cogs():
    """Check that all cogs exist."""
    cog_files = [
        'bot_settings.py', 'bump.py', 'fun.py', 'game_stats.py',
        'giveaways.py', 'interface.py', 'invites.py', 'levelling.py',
        'logging.py', 'moderation.py', 'perplexity_chat.py', 'register.py',
        'server_setup.py', 'settings.py', 'spin.py', 'starboard.py',
        'temp_channels.py', 'ticket.py', 'updater.py', 'utility.py',
        'version_control.py', 'welcomer.py'
    ]
    
    all_good = True
    print("📁 Checking cogs:")
    for cog_file in cog_files:
        filepath = f"cogs/{cog_file}"
        if os.path.exists(filepath):
            print(f"   ✅ {cog_file}")
        else:
            print(f"   ❌ {cog_file}")
            all_good = False
    
    return all_good

def check_utils_structure():
    """Check utils directory structure."""
    required_dirs = [
        'utils/core', 'utils/community', 'utils/database',
        'utils/settings', 'utils/version', 'utils/greeting'
    ]
    
    all_good = True
    print("📁 Checking utils structure:")
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"   ✅ {directory}")
        else:
            print(f"   ❌ {directory}")
            all_good = False
    
    return all_good

def main():
    """Main verification function."""
    print("🤖 CONTRO Bot Deployment Verification")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Dependencies", check_dependencies),
        ("Configuration Files", check_config_files),
        ("Cogs", check_cogs),
        ("Utils Structure", check_utils_structure),
    ]
    
    file_checks = [
        ("main.py", "Main bot file"),
        ("requirements.txt", "Dependencies file"),
        ("README.md", "Documentation"),
        ("CHANGELOG.md", "Change log"),
        ("LICENSE", "License file"),
        ("SECURITY.md", "Security policy"),
        (".gitignore", "Git ignore file"),
    ]
    
    all_passed = True
    
    # Run function checks
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}:")
        if not check_func():
            all_passed = False
    
    # Run file checks
    print(f"\n🔍 Required Files:")
    for filepath, description in file_checks:
        if not check_file_exists(filepath, description):
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks passed! Bot is ready for deployment.")
        print("\nNext steps:")
        print("1. Set up your MongoDB database")
        print("2. Configure your .env file with bot token")
        print("3. Run: python main.py")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
