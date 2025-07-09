import json
import os
import logging

logger = logging.getLogger(__name__)

# Define content directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "data", "content")
os.makedirs(CONTENT_DIR, exist_ok=True)

def load_content(content_key, lang="tr", **kwargs):
    """
    Load content from JSON files based on key and language
    
    Args:
        content_key (str): The content identifier key (e.g. "welcome_message")
        lang (str): Language code (default: "tr")
        **kwargs: Variables to format into the content
    
    Returns:
        str: The formatted content
    """
    try:
        # Try to load from language-specific file
        lang_file = os.path.join(CONTENT_DIR, f"{lang}.json")
        
        if os.path.exists(lang_file):
            with open(lang_file, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
                
            if content_key in content_data:
                content = content_data[content_key]
                # Format with provided variables
                if kwargs:
                    try:
                        return content.format(**kwargs)
                    except KeyError as e:
                        logger.warning(f"Missing key in content formatting: {e}")
                        return content
                return content
        
        # Fallback to default messages
        fallback = {
            "welcome_message": "Welcome to the server, {user}!",
            "rules_title": "Server Rules",
            "about_server": "This is our Discord server.",
            "error_message": "An error occurred.",
            "success_message": "Operation successful!",
        }
        
        if content_key in fallback:
            content = fallback[content_key]
            if kwargs:
                try:
                    return content.format(**kwargs)
                except KeyError:
                    return content
            return content
            
        # If content is not found, return a placeholder
        return f"Missing content: {content_key}"
        
    except Exception as e:
        logger.error(f"Error loading content '{content_key}': {e}")
        return f"Error loading content: {content_key}" 