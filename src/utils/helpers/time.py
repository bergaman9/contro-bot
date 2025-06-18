"""Time and date utilities."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import time


def get_utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def format_dt(dt: datetime, style: str = 'f') -> str:
    """Format datetime for Discord timestamp.
    
    Styles:
    - 't': Short time (16:20)
    - 'T': Long time (16:20:30)
    - 'd': Short date (20/04/2021)
    - 'D': Long date (20 April 2021)
    - 'f': Short date/time (20 April 2021 16:20)
    - 'F': Long date/time (Tuesday, 20 April 2021 16:20)
    - 'R': Relative time (2 hours ago)
    """
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:{style}>"


def parse_time_string(time_str: str) -> Optional[timedelta]:
    """Parse time string like '1d2h30m' into timedelta."""
    time_regex = r'(\d+)([dhms])'
    total_seconds = 0
    
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    import re
    matches = re.findall(time_regex, time_str.lower())
    
    if not matches:
        return None
    
    for value, unit in matches:
        total_seconds += int(value) * units.get(unit, 0)
    
    return timedelta(seconds=total_seconds) if total_seconds > 0 else None


def humanize_timedelta(td: timedelta) -> str:
    """Convert timedelta to human readable string."""
    total_seconds = int(td.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds} second{'s' if total_seconds != 1 else ''}"
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds and not days:  # Only show seconds if less than a day
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    if len(parts) > 1:
        return ', '.join(parts[:-1]) + f" and {parts[-1]}"
    return parts[0] if parts else "0 seconds"


def is_expired(timestamp: Union[datetime, float], duration: timedelta) -> bool:
    """Check if a timestamp has expired based on duration."""
    if isinstance(timestamp, float):
        timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    elif timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    
    return get_utc_now() > timestamp + duration


class Timer:
    """Simple timer for measuring execution time."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else time.perf_counter()
        return end - self.start_time
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.elapsed * 1000 