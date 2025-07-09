# Resources Directory

This directory contains all static assets and configuration files for the Contro Bot.

## Directory Structure

```
resources/
├── data/               # Configuration and data files
│   ├── config/         # Configuration files
│   │   ├── format.json # Server formatting variables (roles, channels)
│   │   └── versions.json # Bot version history
│   ├── content/        # Dynamic content (per-server)
│   ├── contents/       # Default content templates
│   ├── database/       # Database exports and backups
│   │   └── bergaman9.csv # User data export
│   ├── templates/      # Server structure templates
│   └── temp/           # Temporary files (generated images, etc.)
├── fonts/              # Font files for image generation
│   ├── Gotham-Black.otf
│   └── GothamNarrow-Bold.otf
├── images/             # Image assets
│   ├── backgrounds/    # Welcome/goodbye card backgrounds
│   ├── icons/          # Bot icons and emojis
│   └── templates/      # Image templates
└── locales/            # Localization files
    ├── en/             # English translations
    └── tr/             # Turkish translations
```

## Usage

### Configuration Files
- `data/config/format.json`: Defines server-specific role and channel naming conventions
- `data/config/versions.json`: Tracks bot version updates and changelogs

### Content Management
- `data/contents/`: Contains default markdown files for commands like rules, announcements
- `data/content/`: Server-specific content overrides

### Image Generation
- `fonts/`: TrueType/OpenType fonts used for generating welcome cards
- `images/backgrounds/`: Background images for welcome/goodbye cards

### Temporary Storage
- `data/temp/`: Used for temporary file storage during image processing

## File Naming Conventions

- Backgrounds: `{type}_{color}.png` (e.g., `welcome_blue.png`, `byebye_red.png`)
- Content files: `{command_name}.md` (e.g., `rules.md`, `announcements.md`)
- Templates: `{template_name}_{language}.json` (e.g., `gaming_en.json`)

## Notes

- All paths in the code should reference these resources using relative paths from the project root
- The `temp` folder is automatically cleaned up periodically
- Ensure proper permissions are set for the bot to read/write to these directories
