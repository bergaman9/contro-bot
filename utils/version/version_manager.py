"""
CONTRO Bot - Automated Version Control System
Advanced version tracking and management for Discord bot
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import asyncio
import logging

logger = logging.getLogger(__name__)

class VersionManager:
    """Advanced version control manager for CONTRO bot"""
    
    def __init__(self, bot_directory: str = None):
        self.bot_dir = Path(bot_directory or os.getcwd())
        self.versions_file = self.bot_dir / "data" / "versions.json"
        self.config_file = self.bot_dir / "config" / "version_config.json"
        self.changelog_file = self.bot_dir / "CHANGELOG.md"
        
        # Ensure directories exist
        self.versions_file.parent.mkdir(exist_ok=True)
        self.config_file.parent.mkdir(exist_ok=True)
        
        # Initialize configuration
        self._init_config()
    
    def _init_config(self):
        """Initialize version control configuration"""
        default_config = {
            "auto_increment": True,
            "version_format": "semantic",  # semantic, date, or custom
            "track_git_commits": True,
            "auto_changelog": True,
            "notification_webhook": None,
            "backup_versions": True,
            "features_tracking": {
                "registration_system": True,
                "level_system": True,
                "ticket_system": True,
                "welcome_system": True,
                "moderation_system": True,
                "giveaway_system": True,
                "game_stats": True,
                "fun_commands": True
            }
        }
        
        if not self.config_file.exists():
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    def get_current_version(self) -> str:
        """Get current bot version from versions.json"""
        try:
            if self.versions_file.exists():
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('current_version', '2.0.0')
            return '2.0.0'
        except Exception as e:
            logger.error(f"Error reading current version: {e}")
            return '2.0.0'
    
    def increment_version(self, version_type: str = 'patch') -> str:
        """
        Increment version number
        Args:
            version_type: 'major', 'minor', or 'patch'
        """
        current = self.get_current_version()
        parts = current.split('.')
        
        if len(parts) != 3:
            parts = ['2', '0', '0']
        
        major, minor, patch = map(int, parts)
        
        if version_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif version_type == 'minor':
            minor += 1
            patch = 0
        else:  # patch
            patch += 1
        
        return f"{major}.{minor}.{patch}"
    
    def create_version_entry(self, version: str, features: List[str] = None, 
                           fixes: List[str] = None, upcoming: List[str] = None,
                           description: str = None) -> Dict:
        """Create a new version entry"""
        return {
            "version": version,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "description": description or f"Version {version} release",
            "features": features or [],
            "fixes": fixes or [],
            "upcoming": upcoming or [],
            "git_commit": self._get_git_commit(),
            "files_changed": self._get_changed_files(),
            "system_info": self._get_system_info()
        }
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.bot_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()[:12]  # Short hash
        except Exception as e:
            logger.warning(f"Could not get git commit: {e}")
        return None
    
    def _get_changed_files(self) -> List[str]:
        """Get list of recently changed files"""
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
                cwd=self.bot_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return [f.strip() for f in result.stdout.split('\n') if f.strip()]
        except Exception as e:
            logger.warning(f"Could not get changed files: {e}")
        return []
    
    def _get_system_info(self) -> Dict:
        """Get system information for version tracking"""
        return {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "timestamp": datetime.now().isoformat()
        }
    
    def add_version(self, version_type: str = 'patch', features: List[str] = None,
                   fixes: List[str] = None, upcoming: List[str] = None,
                   description: str = None) -> str:
        """Add a new version to the tracking system"""
        try:
            # Load existing versions
            versions_data = {"versions": [], "current_version": "2.0.0"}
            if self.versions_file.exists():
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    versions_data = json.load(f)
            
            # Generate new version
            new_version = self.increment_version(version_type)
            
            # Create version entry
            version_entry = self.create_version_entry(
                new_version, features, fixes, upcoming, description
            )
            
            # Add to versions list
            versions_data["versions"].append(version_entry)
            versions_data["current_version"] = new_version
            
            # Save to file
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(versions_data, f, indent=2, ensure_ascii=False)
            
            # Update changelog
            self._update_changelog(version_entry)
            
            logger.info(f"Version {new_version} added successfully")
            return new_version
            
        except Exception as e:
            logger.error(f"Error adding version: {e}")
            raise
    
    def _update_changelog(self, version_entry: Dict):
        """Update CHANGELOG.md file"""
        try:
            changelog_content = f"""
## [{version_entry['version']}] - {version_entry['date']}

### Description
{version_entry.get('description', f"Version {version_entry['version']} release")}

### ✨ New Features
"""
            
            for feature in version_entry.get('features', []):
                changelog_content += f"- {feature}\n"
            
            if version_entry.get('fixes'):
                changelog_content += "\n### 🐛 Bug Fixes\n"
                for fix in version_entry['fixes']:
                    changelog_content += f"- {fix}\n"
            
            if version_entry.get('upcoming'):
                changelog_content += "\n### 🔮 Upcoming Features\n"
                for upcoming in version_entry['upcoming']:
                    changelog_content += f"- {upcoming}\n"
            
            if version_entry.get('git_commit'):
                changelog_content += f"\n**Git Commit:** `{version_entry['git_commit']}`\n"
            
            changelog_content += "\n---\n"
            
            # Prepend to existing changelog
            existing_content = ""
            if self.changelog_file.exists():
                with open(self.changelog_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            
            # Write updated changelog
            with open(self.changelog_file, 'w', encoding='utf-8') as f:
                if not existing_content.startswith("# CHANGELOG"):
                    f.write("# CHANGELOG\n\nAll notable changes to CONTRO Bot will be documented in this file.\n\n")
                f.write(changelog_content)
                f.write(existing_content)
                
        except Exception as e:
            logger.error(f"Error updating changelog: {e}")
    
    def get_version_history(self, limit: int = 10) -> List[Dict]:
        """Get version history"""
        try:
            if self.versions_file.exists():
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    versions = data.get('versions', [])
                    return versions[-limit:] if limit > 0 else versions
        except Exception as e:
            logger.error(f"Error reading version history: {e}")
        return []
    
    def auto_version_check(self) -> Optional[str]:
        """Automatically detect if a new version should be created based on git changes"""
        try:
            # Check if there are uncommitted changes
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.bot_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return "Changes detected - consider creating new version"
            
            # Check if there are new commits since last version
            last_version = self.get_version_history(1)
            if last_version:
                last_commit = last_version[0].get('git_commit')
                current_commit = self._get_git_commit()
                
                if last_commit != current_commit:
                    return "New commits detected - version update recommended"
            
        except Exception as e:
            logger.warning(f"Auto version check failed: {e}")
        
        return None
    
    def create_git_tag(self, version: str) -> bool:
        """Create git tag for version"""
        try:
            # Create tag
            subprocess.run(
                ['git', 'tag', '-a', f'v{version}', '-m', f'Version {version}'],
                cwd=self.bot_dir,
                check=True,
                timeout=10
            )
            
            # Push tag
            subprocess.run(
                ['git', 'push', 'origin', f'v{version}'],
                cwd=self.bot_dir,
                check=True,
                timeout=30
            )
            
            logger.info(f"Git tag v{version} created and pushed")
            return True
            
        except Exception as e:
            logger.error(f"Error creating git tag: {e}")
            return False
    
    async def schedule_auto_version(self, interval_hours: int = 24):
        """Schedule automatic version checking"""
        while True:
            try:
                check_result = self.auto_version_check()
                if check_result:
                    logger.info(f"Auto version check: {check_result}")
                
                await asyncio.sleep(interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in scheduled version check: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour

# Global version manager instance
version_manager = VersionManager()

def get_version_manager() -> VersionManager:
    """Get the global version manager instance"""
    return version_manager
