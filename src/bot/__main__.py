"""Entry point for the bot application."""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from bot.launcher import main

if __name__ == "__main__":
    main() 