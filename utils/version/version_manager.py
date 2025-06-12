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

# Git and YAML imports with fallback handling
try:
    import git
    GIT_AVAILABLE = True
    logger.info("GitPython available - Git integration enabled")
except ImportError:
    GIT_AVAILABLE = False
    logger.warning("GitPython not available. Git integration disabled.")

try:
    import yaml
    YAML_AVAILABLE = True
    logger.info("PyYAML available - YAML export enabled")
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not available. YAML export disabled.")


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
            "backup_count": 10,
            "changelog_enabled": True,
            "git_integration": GIT_AVAILABLE,
            "yaml_export": YAML_AVAILABLE,
            "version_format": "semantic",
            "notification_channels": []
        }
        
        if not self.config_file.exists():
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
    
    def get_current_version(self) -> str:
        """Get the current version from versions.json"""
        try:
            if self.versions_file.exists():
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("current_version", "2.0.0")
            return "2.0.0"
        except Exception as e:
            logger.error(f"Error reading current version: {e}")
            return "2.0.0"
    
    def increment_version(self, version_type: str = 'patch') -> str:
        """Increment version based on type (major, minor, patch)"""
        current = self.get_current_version()
        
        try:
            major, minor, patch = map(int, current.split('.'))
        except ValueError:
            major, minor, patch = 2, 0, 0
        
        if version_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif version_type == 'minor':
            minor += 1
            patch = 0
        else:
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
        if not GIT_AVAILABLE:
            return None
            
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.bot_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()[:12]
        except Exception as e:
            logger.warning(f"Could not get git commit: {e}")
        return None
    
    def _get_changed_files(self) -> List[str]:
        """Get list of recently changed files"""
        if not GIT_AVAILABLE:
            return []
            
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
            versions_data = {"versions": [], "current_version": "2.0.0"}
            if self.versions_file.exists():
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    versions_data = json.load(f)
            
            new_version = self.increment_version(version_type)
            
            version_entry = self.create_version_entry(
                new_version, features, fixes, upcoming, description
            )
            
            versions_data["versions"].append(version_entry)
            versions_data["current_version"] = new_version
            
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(versions_data, f, indent=2, ensure_ascii=False)
            
            self.create_git_tag(new_version)
            self.update_changelog(version_entry)
            
            logger.info(f"Created version {new_version}")
            return new_version
            
        except Exception as e:
            logger.error(f"Error adding version: {e}")
            raise
    
    def create_git_tag(self, version: str) -> bool:
        """Create a git tag for the version"""
        if not GIT_AVAILABLE:
            return False
            
        try:
            result = subprocess.run(
                ['git', 'tag', '-a', f'v{version}', '-m', f'Version {version}'],
                cwd=self.bot_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Created git tag v{version}")
                return True
        except Exception as e:
            logger.warning(f"Could not create git tag: {e}")
        return False
    
    def update_changelog(self, version_entry: Dict):
        """Update CHANGELOG.md with new version"""
        try:
            changelog_content = f"# Changelog\n\n"
            
            if self.changelog_file.exists():
                with open(self.changelog_file, 'r', encoding='utf-8') as f:
                    existing = f.read()
                    if not existing.startswith("# Changelog"):
                        changelog_content = existing
                    else:
                        changelog_content = existing
            
            new_entry = f"## [{version_entry['version']}] - {version_entry['date']}\n\n"
            
            if version_entry['description']:
                new_entry += f"{version_entry['description']}\n\n"
            
            if version_entry['features']:
                new_entry += "### Added\n"
                for feature in version_entry['features']:
                    new_entry += f"- {feature}\n"
                new_entry += "\n"
            
            if version_entry['fixes']:
                new_entry += "### Fixed\n"
                for fix in version_entry['fixes']:
                    new_entry += f"- {fix}\n"
                new_entry += "\n"
            
            lines = changelog_content.split('\n')
            if len(lines) > 1:
                lines.insert(2, new_entry)
                changelog_content = '\n'.join(lines)
            else:
                changelog_content = f"# Changelog\n\n{new_entry}"
            
            with open(self.changelog_file, 'w', encoding='utf-8') as f:
                f.write(changelog_content)
                
        except Exception as e:
            logger.error(f"Error updating changelog: {e}")
    
    def get_version_history(self, limit: int = 10) -> List[Dict]:
        """Get version history with optional limit"""
        try:
            if not self.versions_file.exists():
                return []
            
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                versions = data.get("versions", [])
                return versions[-limit:] if limit else versions
                
        except Exception as e:
            logger.error(f"Error getting version history: {e}")
            return []
    
    def export_to_yaml(self, output_path: str = None) -> bool:
        """Export version data to YAML format"""
        if not YAML_AVAILABLE:
            logger.warning("YAML export unavailable - PyYAML not installed")
            return False
            
        try:
            if not self.versions_file.exists():
                return False
            
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            output_file = output_path or str(self.bot_dir / "data" / "versions.yaml")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Exported version data to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to YAML: {e}")
            return False
    
    def auto_version_check(self) -> Optional[str]:
        """Check if a version should be automatically created based on changes"""
        if not GIT_AVAILABLE:
            return None
            
        try:
            changed_files = self._get_changed_files()
            
            if not changed_files:
                return None
            
            has_major_changes = any(
                'main.py' in f or 'requirements.txt' in f 
                for f in changed_files
            )
            
            has_minor_changes = any(
                f.startswith('cogs/') or f.startswith('utils/')
                for f in changed_files
            )
            
            if has_major_changes:
                return 'major'
            elif has_minor_changes:
                return 'minor'
            else:
                return 'patch'
                
        except Exception as e:
            logger.error(f"Error in auto version check: {e}")
            return None


_version_manager = None


def get_version_manager() -> VersionManager:
    """Get the global version manager instance"""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager
