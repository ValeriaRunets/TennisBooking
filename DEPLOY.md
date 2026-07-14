# Deploying for Free (24/7)

The bot only alerts you if it's running around the clock, so it needs an
always-on host. The best free option as of 2026 is **Oracle Cloud Always Free**:
a permanently free VM generous enough for headless Chromium, and the bot
deploys on it with `docker compose` exactly as it runs locally.

## Oracle Cloud Always Free

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

## Alternative: GitHub Actions cron ($0, no server)

If you'd rather not manage a VM at all, the checker could run as a scheduled
GitHub Actions workflow (every 15–30 min) that performs one check cycle and
exits. Trade-offs: it needs a small refactor to a one-shot mode, interactive
Telegram commands won't work (links are edited as a file in the repo),
cron firings are delayed by 5–15 min at busy times, and scheduled workflows
are auto-disabled after 60 days without repo activity. Free minutes are
unlimited on public repos and 2,000/month on private ones (roughly one check
per hour). See [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits).
