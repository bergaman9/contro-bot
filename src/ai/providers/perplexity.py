"""
Perplexity AI Provider for Server Design and Content Generation
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
import json
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PerplexityModel(Enum):
    """Available Perplexity models"""
    LLAMA_3_1_SONAR_SMALL = "llama-3.1-sonar-small-128k-online"
    LLAMA_3_1_SONAR_LARGE = "llama-3.1-sonar-large-128k-online"
    LLAMA_3_1_SONAR_HUGE = "llama-3.1-sonar-huge-128k-online"

@dataclass
class ServerStructure:
    """Data class for AI-generated server structure"""
    name: str
    description: str
    categories: List[Dict[str, Any]]
    roles: List[Dict[str, Any]]
    permissions: Dict[str, Any]
    welcome_message: str
    rules: List[str]
    
@dataclass
class ContentAnalysis:
    """Data class for content analysis results"""
    is_safe: bool
    confidence: float
    categories: List[str]
    explanation: str

class PerplexityProvider:
    """Perplexity AI provider for server design and content analysis"""
    
    def __init__(self, api_key: str, model: PerplexityModel = PerplexityModel.LLAMA_3_1_SONAR_LARGE):
        self.api_key = api_key
        self.model = model.value
        self.base_url = "https://api.perplexity.ai"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(self, prompt: str, max_tokens: int = 4000) -> str:
        """Make a request to Perplexity API"""
        if not self.session:
            raise RuntimeError("PerplexityProvider must be used as async context manager")
            
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Discord server designer. Provide detailed, practical responses in JSON format when requested."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            async with self.session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Perplexity API error {response.status}: {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"].strip()
                
        except Exception as e:
            logger.error(f"Error making Perplexity API request: {e}")
            raise
    
    async def generate_server_structure(self, description: str, server_type: str = "community") -> ServerStructure:
        """Generate complete server structure from description"""
        prompt = f"""
        Create a detailed Discord server structure based on this description: "{description}"
        Server type: {server_type}
        
        Provide a JSON response with the following structure:
        {{
            "name": "Server Name",
            "description": "Server description",
            "categories": [
                {{
                    "name": "Category Name",
                    "position": 0,
                    "channels": [
                        {{
                            "name": "channel-name",
                            "type": "text|voice|forum",
                            "description": "Channel purpose",
                            "nsfw": false,
                            "slowmode": 0,
                            "permissions": {{}}
                        }}
                    ]
                }}
            ],
            "roles": [
                {{
                    "name": "Role Name",
                    "color": "#FF0000",
                    "permissions": ["permission_name"],
                    "hoist": true,
                    "mentionable": true,
                    "position": 1
                }}
            ],
            "permissions": {{
                "default_permissions": ["read_messages", "send_messages"],
                "admin_permissions": ["administrator"],
                "moderator_permissions": ["manage_messages", "kick_members"]
            }},
            "welcome_message": "Welcome message template",
            "rules": ["Rule 1", "Rule 2", "Rule 3"]
        }}
        
        Make the structure practical, organized, and suitable for the described purpose.
        Include at least 3-5 categories with relevant channels.
        Create a proper role hierarchy with clear permissions.
        Ensure channel names follow Discord naming conventions (lowercase, hyphens).
        """
        
        try:
            response = await self._make_request(prompt)
            
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
                
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            return ServerStructure(
                name=data.get("name", "AI Generated Server"),
                description=data.get("description", ""),
                categories=data.get("categories", []),
                roles=data.get("roles", []),
                permissions=data.get("permissions", {}),
                welcome_message=data.get("welcome_message", "Welcome to the server!"),
                rules=data.get("rules", [])
            )
            
        except Exception as e:
            logger.error(f"Error generating server structure: {e}")
            # Return a default structure if AI fails
            return self._get_default_structure(description, server_type)
    
    async def analyze_content(self, content: str, context: str = "discord_message") -> ContentAnalysis:
        """Analyze content for safety and appropriateness"""
        prompt = f"""
        Analyze this Discord message content for safety and appropriateness:
        Content: "{content}"
        Context: {context}
        
        Provide a JSON response:
        {{
            "is_safe": true/false,
            "confidence": 0.95,
            "categories": ["spam", "toxic", "inappropriate", "safe"],
            "explanation": "Brief explanation of the analysis"
        }}
        
        Consider: spam, toxicity, harassment, inappropriate content, NSFW material, threats, doxxing.
        """
        
        try:
            response = await self._make_request(prompt, max_tokens=500)
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                # Default to safe if parsing fails
                return ContentAnalysis(
                    is_safe=True,
                    confidence=0.5,
                    categories=["unknown"],
                    explanation="Analysis failed, defaulting to safe"
                )
                
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            return ContentAnalysis(
                is_safe=data.get("is_safe", True),
                confidence=data.get("confidence", 0.5),
                categories=data.get("categories", []),
                explanation=data.get("explanation", "")
            )
            
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return ContentAnalysis(
                is_safe=True,
                confidence=0.5,
                categories=["error"],
                explanation=f"Analysis error: {str(e)}"
            )
    
    async def suggest_optimizations(self, server_data: dict) -> List[Dict[str, Any]]:
        """Suggest server optimizations based on current structure"""
        prompt = f"""
        Analyze this Discord server structure and suggest optimizations:
        {json.dumps(server_data, indent=2)}
        
        Provide suggestions in JSON format:
        {{
            "suggestions": [
                {{
                    "type": "channel|role|permission|organization",
                    "priority": "high|medium|low",
                    "title": "Suggestion title",
                    "description": "Detailed description",
                    "implementation": "How to implement this suggestion"
                }}
            ]
        }}
        
        Focus on: organization, permissions, engagement, security, user experience.
        """
        
        try:
            response = await self._make_request(prompt)
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return []
                
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            return data.get("suggestions", [])
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []
    
    async def generate_welcome_message(self, server_name: str, server_theme: str) -> str:
        """Generate a personalized welcome message"""
        prompt = f"""
        Create a warm, engaging welcome message for a Discord server.
        Server name: {server_name}
        Theme/Topic: {server_theme}
        
        Include:
        - Friendly greeting
        - Brief server description
        - Key rules or guidelines
        - Encouragement to participate
        - Use Discord formatting (bold, italic, emojis)
        
        Keep it concise but welcoming (max 300 words).
        """
        
        try:
            response = await self._make_request(prompt, max_tokens=500)
            return response
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            return f"Welcome to {server_name}! We're glad you're here. Please read the rules and enjoy your stay! 🎉"
    
    def _get_default_structure(self, description: str, server_type: str) -> ServerStructure:
        """Fallback server structure if AI generation fails"""
        return ServerStructure(
            name="New Server",
            description=description,
            categories=[
                {
                    "name": "📢 INFORMATION",
                    "position": 0,
                    "channels": [
                        {"name": "📋│rules", "type": "text", "description": "Server rules and guidelines"},
                        {"name": "📢│announcements", "type": "text", "description": "Important server announcements"},
                        {"name": "ℹ️│info", "type": "text", "description": "Server information and FAQ"}
                    ]
                },
                {
                    "name": "💬 GENERAL",
                    "position": 1,
                    "channels": [
                        {"name": "💬│general", "type": "text", "description": "General discussion"},
                        {"name": "🎵│music", "type": "voice", "description": "Music and voice chat"},
                        {"name": "🎮│gaming", "type": "text", "description": "Gaming discussions"}
                    ]
                }
            ],
            roles=[
                {"name": "Admin", "color": "#FF0000", "permissions": ["administrator"]},
                {"name": "Moderator", "color": "#00FF00", "permissions": ["manage_messages", "kick_members"]},
                {"name": "Member", "color": "#0000FF", "permissions": ["send_messages", "read_messages"]}
            ],
            permissions={
                "default_permissions": ["read_messages", "send_messages"],
                "admin_permissions": ["administrator"],
                "moderator_permissions": ["manage_messages", "kick_members"]
            },
            welcome_message="Welcome to our server! Please read the rules and enjoy your stay!",
            rules=[
                "Be respectful to all members",
                "No spam or excessive self-promotion", 
                "Keep discussions on-topic",
                "Follow Discord's Terms of Service"
            ]
        ) 