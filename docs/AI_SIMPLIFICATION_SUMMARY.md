# AI System Simplification Summary

## Changes Made

### 1. Removed AI Command Groups
- **Before**: `/ai ask`, `/ai credits`, `/ai settings`
- **After**: `/ask` (direct command)

### 2. Background Credit System
- Credits are still tracked and deducted in the background
- Users are no longer blocked from using AI when credits run out
- Credit system logs activity for future implementation
- No user-facing credit limit messages

### 3. Simplified User Experience
- Users can directly use `/ask [question]` command
- AI responses work seamlessly without credit barriers
- Credit management happens transparently

### 4. Maintained Features
- Streaming responses (if enabled)
- Reply-to-bot functionality for AI chat
- Server-specific settings and API keys
- Background credit tracking and daily resets
- Error handling and logging

## Benefits

1. **Simplified UX**: Users don't need to understand credit system
2. **No Barriers**: AI is always accessible to users
3. **Background Tracking**: Admin features preserved for future use
4. **Clean Commands**: Single `/ask` command instead of nested groups

## Files Modified

- `cogs/perplexity_chat.py` - Simplified command structure and credit handling

## Future Implementation

The credit system infrastructure remains intact and can be re-enabled later with:
- Admin commands to manage user credits
- Credit purchase/earning systems
- Server-specific credit limits
- Public credit display features
