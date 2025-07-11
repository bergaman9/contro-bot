## [1.1.5] - 2025-07-11

Cleanup before rebase

## [1.1.4] - 2025-07-09

Merge refactor/modular-architecture into main

- Resolved version config conflict
- Integrated comprehensive modular architecture updates
- All new features and improvements merged successfully

## [1.1.3] - 2025-06-18

feat: Clean up bot commands and centralize configuration under /settings - Removed redundant commands (kayit, temp_channels, loggings, etc.) - Moved all configuration flows to unified /settings panel - Created command groups for leaderboard and server commands - Removed duplicate love command, kept only love_calculator - All admin/config commands now accessible via /settings interface - Cleaner command structure for better UX

# Changelog

## [1.1.2] - 2025-06-18

fix: resolve undefined modals, MongoDB connection, and API duplicate messages - Added all missing modal classes (SetEmbedColorModal, SetReportChannelModal, etc.) - Fixed MongoDB Atlas connection in centralized db_manager - Removed duplicate API server startup messages - Deleted unnecessary CHANGELOG files - Updated registration system with centralized database connection
