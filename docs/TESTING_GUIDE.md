# Contro Discord Bot - Testing Instructions

## System Testing Guide

### 1. Registration System Testing

#### Command Testing:
```
/register
/profile @user
```

#### Embed Generation Testing:
1. Use `/register` command to open registration form
2. Fill out the registration form with test data
3. Verify the registration confirmation embed appears
4. Check that user receives appropriate roles
5. Use `/profile` to verify user data is stored correctly

#### Expected Results:
- Registration form modal should appear
- User should receive configured registration roles
- Profile embed should display user information
- Registration data should be saved to database

### 2. Ticket System Testing

#### Command Testing:
```
/ticket setup
/ticket create
```

#### Embed Generation and Interaction Testing:
1. Use `/ticket setup` to configure ticket system
2. Create ticket categories and support roles
3. Use `/ticket create` or ticket buttons to create a new ticket
4. Test ticket closing functionality
5. Verify ticket logging and archiving

#### Expected Results:
- Ticket channels should be created in designated category
- Support roles should have access to tickets
- Ticket embeds should show user information and level data (if enabled)
- Tickets should close/archive properly

### 3. Welcome System Testing

#### Manual Testing:
1. **Setup Testing:**
   - Go to server settings → Welcome/Goodbye
   - Click "Full Setup" or "Quick Setup"
   - Configure welcome channel and message
   - Test background selection and customization

2. **Functionality Testing:**
   - Have a test user join the server
   - Check welcome message appears in configured channel
   - Verify welcome image generates correctly
   - Test message variables (user mention, server name, etc.)

#### Commands for Testing:
```
/welcomer test
/welcomer setup
```

#### Expected Results:
- Welcome message should appear when user joins
- Welcome image should be generated with custom styling
- Message variables should be replaced correctly
- Background and text customization should work

### 4. Level System Testing

#### Command Testing:
```
/rank @user
/leaderboard
/level roles
```

#### Button Testing:
1. Go to server settings → Feature Management
2. Click "Toggle Leveling System" button
3. Verify system enables/disables correctly
4. Test level role assignment

#### XP Generation Testing:
1. Send messages in various channels
2. Join voice channels and stay active
3. Check XP gains with `/rank`
4. Verify level progression and role assignment

#### Expected Results:
- XP should be gained from messages and voice activity
- Level roles should be assigned automatically
- Leaderboard should show correct rankings
- Level cards should generate properly

### 5. Feature Toggle Testing

#### Button Testing in Feature Management:
1. Go to server settings → Feature Management → View Feature Status
2. Test each toggle button:
   - ✅ Toggle Welcome System
   - ✅ Toggle Leveling System  
   - ✅ Toggle Starboard
   - ✅ Toggle Auto Moderation
   - ✅ Toggle Logging
   - ✅ Toggle Ticket System
   - ✅ Toggle Community Features
   - ✅ Toggle Temp Channels

#### Expected Results:
- Each button should toggle the feature on/off
- Status should update immediately
- Features should actually be disabled when toggled off
- Commands related to disabled features should be unavailable

## Debugging Commands

### Check Bot Status:
```
/ping
/info
```

### Check System Status:
```
/server info
/settings view
```

### Database Verification:
- Check MongoDB collections for data persistence
- Verify user data is stored correctly
- Check feature toggle states

## Common Issues and Solutions

### If Registration Doesn't Work:
1. Check if registration system is enabled in feature toggles
2. Verify roles are properly configured
3. Check bot permissions for role assignment

### If Welcome System Doesn't Work:
1. Verify welcome channel is set
2. Check bot permissions in welcome channel
3. Ensure welcome system is enabled in feature toggles
4. Test image generation permissions

### If Level System Doesn't Work:
1. Check if leveling system is enabled in feature toggles
2. Verify XP channel restrictions
3. Check level role configuration
4. Test database connectivity

### If Buttons Don't Respond:
1. Check bot permissions for interaction responses
2. Verify cogs are loaded properly
3. Check for any error messages in logs
4. Restart bot if persistent issues

## Testing Checklist

- [ ] Registration form opens and submits successfully
- [ ] Ticket system creates and manages tickets properly
- [ ] Welcome messages generate with images
- [ ] Level system tracks XP and assigns roles
- [ ] All feature toggle buttons work correctly
- [ ] Profile and rank commands display data correctly
- [ ] Server settings panel loads all sections
- [ ] Database persistence works across restarts
- [ ] Error handling provides user-friendly messages
- [ ] All embeds display correctly with proper formatting

## Dev Mode Testing

To run the bot in development mode for testing:

```bash
python main.py dev
```

This will:
- Enable debug logging
- Use development environment variables
- Provide more verbose error messages
- Allow hot-reloading of certain features

## Production Testing Notes

Before deploying to production:
1. Test all systems with a clean database
2. Verify all environment variables are set correctly
3. Test with multiple users and concurrent operations
4. Monitor memory usage and performance
5. Verify all file permissions and directories exist
