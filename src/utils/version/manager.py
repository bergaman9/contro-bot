"""
Version Control Manager for Contro Discord Bot
Automatically tracks version changes and manages release notes
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import git
import subprocess

logger = logging.getLogger('version_manager')

class VersionManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.versions_file = os.path.join(data_dir, "versions.json")
        self.ensure_data_directory()
        
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)
        
    def load_versions(self) -> Dict[str, Any]:
        """Load version data from JSON file"""
        try:
            if os.path.exists(self.versions_file):
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create initial structure
                return {
                    "versions": [],
                    "current_version": "1.0.0"
                }
        except Exception as e:
            logger.error(f"Error loading versions: {e}")
            return {"versions": [], "current_version": "1.0.0"}
    
    def save_versions(self, data: Dict[str, Any]):
        """Save version data to JSON file"""
        try:
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Version data saved to {self.versions_file}")
        except Exception as e:
            logger.error(f"Error saving versions: {e}")
    
    def get_current_version(self) -> str:
        """Get the current version"""
        data = self.load_versions()
        return data.get("current_version", "1.0.0")
    
    def get_next_version(self, version_type: str = "patch") -> str:
        """
        Generate next version number
        version_type: 'major', 'minor', or 'patch'
        """
        current = self.get_current_version()
        major, minor, patch = map(int, current.split('.'))
        
        if version_type == "major":
            return f"{major + 1}.0.0"
        elif version_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"
    
    def create_new_version(self, 
                          version_type: str = "patch",
                          features: List[str] = None,
                          fixes: List[str] = None,
                          upcoming: List[str] = None,
                          auto_detect: bool = True) -> str:
        """
        Create a new version entry
        """
        data = self.load_versions()
        new_version = self.get_next_version(version_type)
        
        # Auto-detect changes if enabled
        if auto_detect:
            auto_features, auto_fixes = self.detect_changes()
            features = (features or []) + auto_features
            fixes = (fixes or []) + auto_fixes
        
        new_entry = {
            "version": new_version,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "features": features or [],
            "fixes": fixes or [],
            "upcoming": upcoming or []
        }
        
        data["versions"].append(new_entry)
        data["current_version"] = new_version
        
        self.save_versions(data)
        logger.info(f"Created new version: {new_version}")
        
        return new_version
    
    def detect_changes(self) -> tuple[List[str], List[str]]:
        """
        Auto-detect changes from git commits
        Returns (features, fixes)
        """
        features = []
        fixes = []
        
        try:
            # Try to get git repository
            repo = git.Repo(search_parent_directories=True)
            
            # Get commits since last version tag
            try:
                last_tag = repo.git.describe('--tags', '--abbrev=0')
                commits = list(repo.iter_commits(f'{last_tag}..HEAD'))
            except:
                # No tags found, get recent commits
                commits = list(repo.iter_commits(max_count=10))
            
            for commit in commits:
                message = commit.message.strip().lower()
                
                # Categorize commits
                if any(keyword in message for keyword in ['feat:', 'feature:', 'add:', 'new:']):
                    features.append(commit.message.strip().split('\n')[0])
                elif any(keyword in message for keyword in ['fix:', 'bug:', 'patch:', 'hotfix:']):
                    fixes.append(commit.message.strip().split('\n')[0])
                elif any(keyword in message for keyword in ['update:', 'improve:', 'enhance:']):
                    features.append(commit.message.strip().split('\n')[0])
                    
        except Exception as e:
            logger.warning(f"Could not detect git changes: {e}")
            
        return features, fixes
    
    def get_version_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get version history"""
        data = self.load_versions()
        versions = data.get("versions", [])
        
        # Sort by version number (newest first)
        versions.sort(key=lambda x: [int(v) for v in x["version"].split('.')], reverse=True)
        
        if limit:
            return versions[:limit]
        return versions
    
    def get_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Get specific version information"""
        data = self.load_versions()
        for v in data.get("versions", []):
            if v["version"] == version:
                return v
        return None
    
    def generate_changelog(self, format_type: str = "markdown") -> str:
        """
        Generate changelog in specified format
        format_type: 'markdown', 'discord', 'html'
        """
        versions = self.get_version_history()
        
        if format_type == "markdown":
            return self._generate_markdown_changelog(versions)
        elif format_type == "discord":
            return self._generate_discord_changelog(versions)
        elif format_type == "html":
            return self._generate_html_changelog(versions)
        else:
            return self._generate_markdown_changelog(versions)
    
    def _generate_markdown_changelog(self, versions: List[Dict[str, Any]]) -> str:
        """Generate markdown changelog"""
        changelog = "# 📋 Changelog\n\n"
        
        for version in versions:
            changelog += f"## 🚀 Version {version['version']} - {version['date']}\n\n"
            
            if version.get('features'):
                changelog += "### ✨ New Features\n"
                for feature in version['features']:
                    changelog += f"- {feature}\n"
                changelog += "\n"
            
            if version.get('fixes'):
                changelog += "### 🐛 Bug Fixes\n"
                for fix in version['fixes']:
                    changelog += f"- {fix}\n"
                changelog += "\n"
                
            if version.get('upcoming'):
                changelog += "### 🔮 Upcoming Features\n"
                for upcoming in version['upcoming']:
                    changelog += f"- {upcoming}\n"
                changelog += "\n"
            
            changelog += "---\n\n"
        
        return changelog
    
    def _generate_discord_changelog(self, versions: List[Dict[str, Any]], limit: int = 3) -> str:
        """Generate Discord-formatted changelog"""
        changelog = "```md\n# 📋 Recent Updates\n\n"
        
        for version in versions[:limit]:
            changelog += f"## 🚀 Version {version['version']} ({version['date']})\n\n"
            
            if version.get('features'):
                changelog += "### ✨ Features:\n"
                for feature in version['features'][:5]:  # Limit features
                    changelog += f"• {feature}\n"
                changelog += "\n"
            
            if version.get('fixes'):
                changelog += "### 🐛 Fixes:\n"
                for fix in version['fixes'][:3]:  # Limit fixes
                    changelog += f"• {fix}\n"
                changelog += "\n"
        
        changelog += "```"
        return changelog
    
    def _generate_html_changelog(self, versions: List[Dict[str, Any]]) -> str:
        """Generate HTML changelog"""
        html = """
        <div class="changelog">
            <h1>📋 Changelog</h1>
        """
        
        for version in versions:
            html += f"""
            <div class="version">
                <h2>🚀 Version {version['version']} - {version['date']}</h2>
            """
            
            if version.get('features'):
                html += "<h3>✨ New Features</h3><ul>"
                for feature in version['features']:
                    html += f"<li>{feature}</li>"
                html += "</ul>"
            
            if version.get('fixes'):
                html += "<h3>🐛 Bug Fixes</h3><ul>"
                for fix in version['fixes']:
                    html += f"<li>{fix}</li>"
                html += "</ul>"
                
            html += "</div>"
        
        html += "</div>"
        return html
    
    def create_git_tag(self, version: str = None) -> bool:
        """Create a git tag for the current version"""
        try:
            if not version:
                version = self.get_current_version()
                
            repo = git.Repo(search_parent_directories=True)
            
            # Create annotated tag
            tag_message = f"Release version {version}"
            repo.create_tag(f"v{version}", message=tag_message)
            
            logger.info(f"Created git tag: v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating git tag: {e}")
            return False
    
    def export_version_data(self, format_type: str = "json") -> str:
        """Export version data in specified format"""
        data = self.load_versions()
        
        if format_type == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format_type == "yaml":
            try:
                import yaml
                return yaml.dump(data, default_flow_style=False, allow_unicode=True)
            except ImportError:
                logger.warning("PyYAML not installed, returning JSON format")
                return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(data, indent=2, ensure_ascii=False)

# Convenience functions
def get_version_manager() -> VersionManager:
    """Get a singleton version manager instance"""
    if not hasattr(get_version_manager, '_instance'):
        get_version_manager._instance = VersionManager()
    return get_version_manager._instance

def create_version(version_type: str = "patch", features: List[str] = None, fixes: List[str] = None) -> str:
    """Quick function to create a new version"""
    manager = get_version_manager()
    return manager.create_new_version(version_type, features, fixes)

def get_current_version() -> str:
    """Quick function to get current version"""
    manager = get_version_manager()
    return manager.get_current_version()

def generate_changelog(format_type: str = "markdown") -> str:
    """Quick function to generate changelog"""
    manager = get_version_manager()
    return manager.generate_changelog(format_type)
