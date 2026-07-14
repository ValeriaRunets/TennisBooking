# Deploying for Free

The bot only alerts you if checks run around the clock, so it needs to live
somewhere other than your laptop. Two free options:

- **[GitHub Actions](#option-1-github-actions-recommended)** (recommended) —
  zero servers, zero accounts beyond GitHub. The monitor runs as a scheduled
  workflow. Trade-off: interactive Telegram commands (`/add`, `/list`, …)
  don't work; you manage links by editing one JSON file on GitHub.
- **[Oracle Cloud Always Free VM](#option-2-oracle-cloud-always-free-vm)** —
  a real 24/7 server, the bot runs exactly as it does locally, all Telegram
  commands work. Trade-off: cloud account with a credit card + a little
  server upkeep.

---

## Option 1: GitHub Actions (recommended)

### How it works

`.github/workflows/monitor.yml` runs on a schedule. Each run checks all
active links once (`python -m src.main --once`), sends any due Telegram
alerts, and commits the updated `data/state.json` back to the repository —
that file is both your link configuration and the bot's memory of what it
already alerted about.

### 1. Add secrets

GitHub repo → **Settings → Secrets and variables → Actions → New repository
secret**. Create two:

| Name | Value |
|------|-------|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `AUTHORIZED_CHAT_ID` | Your numeric Telegram chat ID (alerts go here) |

### 2. Configure your links

Edit `data/state.json` (on GitHub: open the file → pencil icon → commit):

```json
{
  "links": [
    {
      "id": "tue-evening",
      "url": "https://bookings.better.org.uk/location/islington-tennis-centre/highbury-tennis/2026-07-21/by-time",
      "time_start": "18:00",
      "time_end": "21:00",
      "label": "Islington Tuesday",
      "active": true,
      "created_at": ""
    }
  ],
  "monitoring_enabled": true
}
```

Field notes:

- `id` — any short unique string; it appears in alert messages.
- `time_start` / `time_end` — `"HH:MM"` strings, or `null` for "any time".
- `active` — set `false` to pause one link; `monitoring_enabled: false`
  pauses everything.
- The bot appends tracking fields (`notified_keys`, `consecutive_failures`)
  to links as it runs — leave them alone, or delete them to reset.
- **The URL contains a date.** When it passes, the bot will warn you in
  Telegram that the page yields nothing — edit the URL to a fresh date.

### 3. Enable and test

1. **Actions** tab → enable workflows if GitHub asks.
2. Select **Court monitor** → **Run workflow** to trigger a test run
   immediately. Watch the logs; you should get a Telegram message if a
   matching slot is free.
3. Done — the schedule takes over from here.

### 4. Schedule and free-minute budget

The default schedule is every 30 minutes, 05:00–21:30 UTC (roughly London
daytime). One run takes about 3–4 minutes of the free Linux-runner quota, so:

- **Public repo:** Actions minutes are free without limit — the default
  schedule costs nothing.
- **Private repo:** the free plan includes 2,000 min/month; the default
  schedule uses ~3,500. Drop to hourly by changing the cron in
  `.github/workflows/monitor.yml` to `"0 5-21 * * *"` (~1,800 min/month), or
  narrow the hours.

### Quirks to know

- **Cron is not exact.** Runs start 5–15 minutes late at busy times of day.
  Fine for this use case.
- **Auto-disable after 60 days.** GitHub pauses schedules in repos with no
  commit activity for 60 days, and emails you first. Any commit resets the
  clock (editing a link URL counts); re-enabling is one click in the
  Actions tab.
- **No interactive commands.** `/add`, `/list`, `/check` etc. need the
  long-running bot. You can still run it locally any time
  (`python -m src.main`) to manage links conversationally — commit the
  resulting `data/state.json` when done.
- **Parse failures leave evidence.** If a page yields nothing, the dumped
  HTML is attached to the workflow run as a `debug-dump` artifact
  (Actions → run page → Artifacts).

---

## Option 2: Oracle Cloud Always Free VM

A permanently free VM generous enough for headless Chromium; the bot deploys
with `docker compose` exactly as it runs locally, and all Telegram commands
work.

### 1. Create the account and VM

1. Sign up at [oracle.com/cloud/free](https://www.oracle.com/cloud/free/).
   A credit card is required for identity verification but is not charged on
   the Always Free tier.
2. In the console: **Compute → Instances → Create instance**.
3. Image: **Ubuntu 24.04**. Shape: **VM.Standard.A1.Flex** (Ampere ARM) —
   2 OCPUs / 12 GB RAM is plenty and stays within the free allowance
   (up to 4 OCPUs / 24 GB total).
   - If A1 capacity is unavailable in your region, retry later or at a
     different availability domain — it frees up regularly. The x86
     `VM.Standard.E2.1.Micro` (1 GB RAM) also works but needs swap enabled
     for Chromium.
4. Upload or generate an SSH key, create the instance, note its public IP.

### 2. Install Docker

```bash
ssh ubuntu@<public-ip>

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
# log out and back in so the group change applies
```

### 3. Deploy the bot

```bash
git clone https://github.com/ValeriaRunets/TennisBooking.git
cd TennisBooking

cp .env.example .env
nano .env   # set TELEGRAM_BOT_TOKEN and AUTHORIZED_CHAT_ID

# state.json is tracked in git for the Actions deploy; keep the VM's
# local copy out of git status noise:
git update-index --skip-worktree data/state.json

docker compose up -d --build
```

That's it. `restart: unless-stopped` in `docker-compose.yml` brings the bot
back up after crashes and VM reboots (Docker starts on boot by default).

### Day-to-day

```bash
docker compose logs -f --tail 100   # watch logs
docker compose restart              # restart the bot
git pull && docker compose up -d --build   # update to latest code
```

State lives in `./data/state.json` on the VM (mounted as a volume), so
monitored links survive updates and restarts.

### Notes

- Oracle may reclaim *idle* Always Free instances; this bot drives Chromium
  every poll cycle, so it doesn't look idle. Upgrading the account to
  Pay As You Go (still $0 while within Always Free limits) removes the
  reclamation policy entirely.
- No inbound ports are needed — the bot uses Telegram long polling, so the
  default "SSH only" security list is fine.
