"""Time parser - provides time overlap scoring for temporal search.

This is an optional module that calculates time-based relevance scores.
"""

from datetime import datetime, timedelta
from typing import Optional, Union


def parse_time_string(time_str: str) -> Optional[datetime]:
    """Parse various time string formats to datetime.

    Supports:
    - ISO 8601: 2024-01-15, 2024-01-15T10:30:00
    - Relative: "yesterday", "last week", "3 days ago"
    - Month names: "Jan 15", "January 15, 2024"

    Args:
        time_str: Time string to parse

    Returns:
        datetime object or None if parsing fails
    """
    if not time_str:
        return None

    time_str = time_str.strip()

    # Try ISO format first
    try:
        # Handle Z suffix
        time_str = time_str.replace("Z", "+00:00")
        return datetime.fromisoformat(time_str)
    except (ValueError, AttributeError):
        pass

    # Try simple date formats
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d",
        "%B %d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue

    # Try relative time parsing
    now = datetime.now()
    time_str_lower = time_str.lower()

    if "yesterday" in time_str_lower:
        return now - timedelta(days=1)
    elif "last week" in time_str_lower:
        return now - timedelta(weeks=1)
    elif "last month" in time_str_lower:
        return now - timedelta(days=30)
    elif "ago" in time_str_lower:
        # Parse "X days/weeks/months ago"
        import re

        match = re.search(r"(\d+)\s+(day|week|month|year|hour|minute)s?\s+ago", time_str_lower)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit == "day":
                return now - timedelta(days=amount)
            elif unit == "week":
                return now - timedelta(weeks=amount)
            elif unit == "month":
                return now - timedelta(days=amount * 30)
            elif unit == "year":
                return now - timedelta(days=amount * 365)
            elif unit == "hour":
                return now - timedelta(hours=amount)
            elif unit == "minute":
                return now - timedelta(minutes=amount)

    return None


def time_overlap_score(
    filed_at: str, query_start: Union[str, datetime], query_end: Union[str, datetime]
) -> float:
    """Calculate time-based relevance score.

    Returns a score between 0 and 1 based on how close the filed_at
    date is to the query time range.

    Args:
        filed_at: The timestamp when the memory was filed (string or datetime)
        query_start: Start of the query time range
        query_end: End of the query time range

    Returns:
        Score from 0 (no overlap) to 1 (exact match)
    """
    # Parse all time strings
    if isinstance(filed_at, str):
        filed_dt = parse_time_string(filed_at)
    else:
        filed_dt = filed_at

    if isinstance(query_start, str):
        start_dt = parse_time_string(query_start)
    else:
        start_dt = query_start

    if isinstance(query_end, str):
        end_dt = parse_time_string(query_end)
    else:
        end_dt = query_end

    # If any parsing fails, return neutral score
    if not filed_dt or not start_dt or not end_dt:
        return 0.5  # Neutral score

    # Calculate overlap
    if filed_dt < start_dt:
        # Before the range - use exponential decay
        days_diff = (start_dt - filed_dt).days
        return max(0, 1.0 / (1.0 + days_diff * 0.1))
    elif filed_dt > end_dt:
        # After the range - use exponential decay
        days_diff = (filed_dt - end_dt).days
        return max(0, 1.0 / (1.0 + days_diff * 0.1))
    else:
        # Within range - return 1.0
        return 1.0


def get_time_bonus_weight(decay_rate: str = "medium") -> float:
    """Get recommended time bonus weight based on decay rate preference.

    Args:
        decay_rate: "fast", "medium", or "slow"

    Returns:
        Bonus weight (0.0 to 1.0)
    """
    rates = {
        "fast": 0.3,  # Strong preference for recent
        "medium": 0.2,  # Balanced
        "slow": 0.1,  # Slight preference for recent
    }
    return rates.get(decay_rate, 0.2)
