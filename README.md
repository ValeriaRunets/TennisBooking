# TennisBooking Bot

A Telegram bot that monitors tennis court booking pages on [bookings.better.org.uk](https://bookings.better.org.uk) and sends instant notifications when your desired time slots become available.

## How It Works

1. You add a booking page URL and your preferred time range via Telegram commands.
2. The bot periodically checks the page using a headless Chromium browser (Playwright).
3. A 3-level adaptive parser extracts available slots from the dynamically rendered page:
   - **Level 1** — CSS selector matching (primary and fallback selectors)
   - **Level 2** — Heuristic DOM traversal to find time patterns
   - **Level 3** — Full HTML dump for manual debugging if parsing fails
4. When a matching slot is found, the bot sends a Telegram alert with a direct booking link.

Each slot is alerted **once** — you won't be re-notified every poll cycle while
it stays free, but if a slot gets booked and later frees up again, you'll get a
new alert. If a page repeatedly yields no slots at all (site layout changed, or
the date in the URL has passed), the bot warns you instead of failing silently.

State is persisted to a JSON file, so monitored links survive restarts.

## Available Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `/start` | `/start` | Display welcome message and available commands |
| `/help` | `/help` | Show help information |
| `/add` | `/add <URL> <HH:MM-HH:MM\|any> [label]` | Add a booking page to monitor |
| `/remove` | `/remove <id>` | Remove a monitored link by its ID |
| `/list` | `/list` | Show all monitored links |
| `/edit` | `/edit <id> <time\|url\|label> <value>` | Update a monitored link |
| `/check` | `/check <id>` | Manually check a specific link right now |
| `/pause` | `/pause` | Pause all monitoring |
| `/resume` | `/resume` | Resume monitoring |
| `/status` | `/status` | Show monitoring status and active link count |

### Examples

```
/add https://bookings.better.org.uk/location/islington-tennis-centre/highbury-tennis/2026-03-15/by-time 18:00-21:00 Islington Evening
/list
/check abc12345
/edit abc12345 time 19:00-22:00
/pause
/resume
```

## How to Run

Want it running 24/7 without your laptop? See [DEPLOY.md](DEPLOY.md) for two
free options: **GitHub Actions** (no server at all) or an Oracle Cloud
Always Free VM.

### Prerequisites

- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your numeric Telegram chat ID (for authorization)

### Option A: Docker (Recommended)

```bash
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN and AUTHORIZED_CHAT_ID

docker-compose up --build
```

### Option B: Python

```bash
pip install -r requirements.txt
playwright install chromium

export TELEGRAM_BOT_TOKEN=your_token
export AUTHORIZED_CHAT_ID=your_chat_id

python -m src.main          # interactive bot + periodic monitoring
python -m src.main --once   # single check cycle, then exit (for cron/CI)
```

### Option C: GitHub Actions (no server)

The monitor can run as a scheduled workflow (`.github/workflows/monitor.yml`)
using `--once` mode — completely free, no machine needed. Links are managed by
editing `data/state.json`. Setup guide: [DEPLOY.md](DEPLOY.md).

## Configuration

Environment variables (see `.env.example`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from @BotFather |
| `AUTHORIZED_CHAT_ID` | Yes | — | Numeric Telegram chat ID for authorization |
| `POLL_INTERVAL_MINUTES` | No | `15` | How often to check monitored links |
| `STATE_FILE_PATH` | No | `data/state.json` | Path to persistent state file |
| `BROWSER_DATA_DIR` | No | `browser_data/` | Playwright browser cache directory |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/
```

Tests run automatically in CI on every push (`.github/workflows/tests.yml`).

## Project Structure

```
src/
  main.py                  # Entry point
  bot/
    handlers.py            # Telegram command handlers
    formatters.py          # Message formatting
  models/
    types.py               # TimeSlot, MonitoredLink, AppState dataclasses
  scraper/
    browser.py             # Playwright browser management
    availability.py        # Fetch availability from URLs
    parser.py              # 3-level adaptive HTML parser
  monitor/
    state.py               # JSON state persistence
    checker.py             # Core monitoring logic (alert dedup, failure warnings)
    scheduler.py           # Periodic check scheduling
config/
  settings.py              # Environment variable loading
  selectors.json           # CSS selectors for scraping
tests/                     # Unit tests (pytest)
```
