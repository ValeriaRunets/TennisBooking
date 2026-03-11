"""Discover Better tennis venues by scraping bookings.better.org.uk."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.scraper.browser import BrowserManager

logger = logging.getLogger(__name__)

VENUES_CACHE_PATH = Path("data/venues_cache.json")
CACHE_MAX_AGE_DAYS = 7


async def scrape_all_tennis_venues(browser: BrowserManager) -> list[dict]:
    """Scrape bookings.better.org.uk for all venues with tennis activities.

    Returns list of dicts: {slug, display_name, activity_slug, postcode}.
    """
    page = None
    try:
        page = await browser.load_page(
            "https://bookings.better.org.uk/",
            wait_selector="a[href*='/location/']",
        )

        # Extract all unique location slugs from links
        venue_links = await page.eval_on_selector_all(
            "a[href*='/location/']",
            """elements => {
                const seen = new Set();
                const results = [];
                for (const el of elements) {
                    const href = el.getAttribute('href') || '';
                    const match = href.match(/\\/location\\/([^/]+)/);
                    if (match && !seen.has(match[1])) {
                        seen.add(match[1]);
                        results.push({
                            slug: match[1],
                            display_name: el.textContent.trim(),
                            href: href,
                        });
                    }
                }
                return results;
            }""",
        )

        logger.info("Found %d venue links on homepage", len(venue_links))
    except Exception:
        logger.exception("Failed to scrape venue homepage")
        return []
    finally:
        if page:
            await page.close()

    # Visit each venue to find tennis activities
    tennis_venues = []
    for venue in venue_links:
        slug = venue["slug"]
        activity = await _find_tennis_activity(browser, slug)
        if activity:
            tennis_venues.append(
                {
                    "slug": slug,
                    "display_name": venue["display_name"] or _slug_to_name(slug),
                    "activity_slug": activity["activity_slug"],
                    "postcode": activity.get("postcode"),
                }
            )
            logger.info("Tennis venue found: %s (%s)", slug, activity["activity_slug"])

    logger.info("Total tennis venues found: %d", len(tennis_venues))
    return tennis_venues


async def _find_tennis_activity(browser: BrowserManager, venue_slug: str) -> dict | None:
    """Check if a venue has tennis activities. Returns {activity_slug, postcode} or None."""
    page = None
    try:
        page = await browser.load_page(
            f"https://bookings.better.org.uk/location/{venue_slug}",
        )

        # Look for tennis-related activity links
        result = await page.evaluate(
            """() => {
                const links = document.querySelectorAll('a[href*="/location/"]');
                for (const link of links) {
                    const href = link.getAttribute('href') || '';
                    const text = link.textContent.toLowerCase();
                    // Match activity links like /location/slug/tennis-outdoor/...
                    const match = href.match(/\\/location\\/[^/]+\\/([^/]*tennis[^/]*)/i);
                    if (match) {
                        return { activity_slug: match[1] };
                    }
                    // Also check link text
                    if (text.includes('tennis')) {
                        const actMatch = href.match(/\\/location\\/[^/]+\\/([^/]+)/);
                        if (actMatch) {
                            return { activity_slug: actMatch[1] };
                        }
                    }
                }
                return null;
            }"""
        )

        if not result:
            return None

        # Try to extract postcode from the page
        postcode = await page.evaluate(
            """() => {
                const text = document.body.innerText;
                const match = text.match(/([A-Z]{1,2}\\d[A-Z\\d]?\\s*\\d[A-Z]{2})/i);
                return match ? match[1].toUpperCase() : null;
            }"""
        )

        if postcode:
            result["postcode"] = postcode

        return result

    except Exception:
        logger.debug("Could not check venue %s for tennis", venue_slug)
        return None
    finally:
        if page:
            await page.close()


def _slug_to_name(slug: str) -> str:
    """Convert a URL slug to a display name."""
    return slug.replace("-", " ").title()


def load_venue_cache() -> list[dict] | None:
    """Load cached venue data if it exists and is fresh enough."""
    if not VENUES_CACHE_PATH.exists():
        return None

    try:
        data = json.loads(VENUES_CACHE_PATH.read_text(encoding="utf-8"))
        scraped_at = datetime.fromisoformat(data["scraped_at"])
        age_days = (datetime.utcnow() - scraped_at).days
        if age_days > CACHE_MAX_AGE_DAYS:
            logger.info("Venue cache is %d days old (max %d), needs refresh", age_days, CACHE_MAX_AGE_DAYS)
            return None
        logger.info("Loaded %d venues from cache (age: %d days)", len(data["venues"]), age_days)
        return data["venues"]
    except Exception:
        logger.exception("Failed to load venue cache")
        return None


def save_venue_cache(venues: list[dict]) -> None:
    """Save venue data to cache file."""
    VENUES_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "scraped_at": datetime.utcnow().isoformat(),
        "venues": venues,
    }
    VENUES_CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Saved %d venues to cache", len(venues))
