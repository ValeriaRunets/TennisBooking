# Instagram Content Creator Hub for Notion
## Product Blueprint & Development Plan v2.0

> **Target:** Solo Instagram creators (1–10K followers)
> **Tiers:** Basic (Notion only) • Pro (Notion + integrations)
> **Date:** March 2026

---

## §1. Product Vision

### Concept

An all-in-one Notion template for Instagram creators: content planning, analytics, AI tools, visual feed planning, and **inspiration account analysis** — all in one workspace.

### Competitive Advantages

Most templates on the market are basic planners (calendar + drafts). Our product stands out with:

- **AI-Powered Analytics** — automatic analysis of engagement patterns by time, content type, and topic
- **Content Pillars** — a topic balance tracking system that no competitor offers
- **Feed Grid Preview** — visual Instagram grid simulation directly inside Notion
- **🆕 Inspiration Accounts** — a database of inspiring accounts where AI analyzes their strategy and generates ideas based on what works for the best
- **🆕 Visual Brief** — AI suggests not just a post topic, but a full visual brief: color palette, composition, and what should be in the image
- **Two Tiers** — Basic + Pro with integrations and automation
- **Built-in Onboarding** — users never feel lost

### Important Limitation: Notion AI

- Notion AI is only available on Business and Enterprise plans (from €19.50/month)
- Product listing must state: "AI features require Notion Business plan"
- The template must be fully functional WITHOUT AI — AI only enhances the experience

### Pricing Strategy

|  | Basic | Pro |
|---|---|---|
| **Price** | $19–29 | $39–49 |
| Content Planner | ✓ | ✓ |
| AI Features (custom autofill) | ✓ | ✓ |
| Inspiration Accounts + AI | ✓ | ✓ + auto-import |
| Visual Brief Generator | ✓ | ✓ |
| Feed Grid Preview | Notion Gallery | Gallery + embed |
| Instagram Integration | ✗ (manual input) | ✓ (Zapier/Make) |
| Auto-notifications | ✗ | ✓ |
| Onboarding Guide | ✓ | ✓ + video |

---

## §2. Database Architecture

A total of **8 interconnected databases**. Each has multiple views.

---

### Database 1: Content Hub (Main)

The central database where all posts live.

| Property | Type | Description |
|---|---|---|
| Title | Title | Post headline / topic |
| Status | Select | Idea → Draft → Ready → Published → Archive |
| Content Type | Select | Reels / Carousel / Single / Story / Live |
| Content Pillar | Relation → Pillars DB | Topic category / content pillar |
| Publish Date | Date | Scheduled publication date |
| Time Slot | Select | Posting time (09:00, 12:00, 18:00, 21:00) |
| Caption | Text | Post caption / copy |
| Hashtag Set | Relation → Hashtags DB | Linked hashtag group |
| Cover Image | Files & Media | Post visual / thumbnail |
| Likes / Comments / Saves / Shares | Number ×4 | Post engagement metrics |
| Reach / Impressions | Number ×2 | Post reach and impressions |
| Engagement Rate | Formula | (Likes+Comments+Saves+Shares) / Reach × 100 |
| 🆕 Visual Brief | Relation → Visual Briefs DB | Linked visual brief |
| 🆕 Inspired By | Relation → Inspiration DB | Which account/post inspired this |
| AI Score | AI Custom Autofill | AI-generated potential score |
| AI Summary | AI Summary | Auto-generated page summary |

**Views for Content Hub:**

- **Calendar** — primary view. Posts plotted by publish date, color-coded by status
- **Kanban** — board by status: Idea → Draft → Ready → Published
- **Instagram Grid** — 3-column gallery, filtered to Ready + Published — simulates the feed
- **Analytics Table** — sortable by Engagement Rate, filterable by content type
- **Top Posts** — gallery, sorted by likes desc, limit 9

---

### Database 2: Content Pillars

Topic categories / content pillars (3–5 per creator). The system tracks balance.

| Property | Type | Description |
|---|---|---|
| Name | Title | e.g. Travel, Recipes, Behind the Scenes |
| Color | Select | Color tag for calendar visual coding |
| Target % | Number | Desired share of total content |
| Actual % | Rollup + Formula | Real percentage of posts in this pillar |
| Average ER | Rollup | Average Engagement Rate across pillar posts |
| Posts | Relation → Content Hub | All posts tagged with this pillar |

> **View:** Gallery with progress bar (target % vs actual %)

---

### 🆕 Database 3: Inspiration Accounts

Users add accounts they admire. AI analyzes their strategy.

| Property | Type | Description |
|---|---|---|
| Account | Title | @username |
| Link | URL | instagram.com/username |
| Niche | Select | Same niche / Adjacent / Different industry |
| Followers | Number | Audience size |
| What I Like | Multi-select | Aesthetics / Caption tone / Formats / Engagement / Visual style |
| Color Palette | Text | Main feed colors (hex codes or description) |
| Posting Frequency | Select | Daily / 3–5x per week / 1–2x / Less |
| Top Formats | Multi-select | Reels / Carousel / Single / Stories / Mix |
| Notes | Text | Free-form observations |
| 🤖 AI Strategy Analysis | AI Custom Autofill | Analyzes notes and properties, identifies patterns |
| 🤖 AI Content Ideas | AI Custom Autofill | Generates post ideas based on the account's strategy |
| Inspired Posts | Relation → Content Hub | Posts created based on this account |

**Views:**

- **Gallery** — account cards with avatar and key metrics
- **Comparison Table** — all accounts side by side for quick strategy comparison

**How it works:**

1. User adds 5–10 accounts they admire
2. Fills in "What I Like", "Color Palette", "Top Formats", writes observations
3. **In Basic** — user manually researches accounts and fills in data
4. **In Pro** — via Make/Zapier + Instagram Scraper API, basic metrics (followers, posting frequency) can be auto-pulled
5. AI Custom Autofill analyzes everything it knows about each account and delivers:
   - Strategic analysis: what makes the account successful
   - 3–5 post ideas adapted to the user's own style

**AI prompt for Strategy Analysis:**
> "Analyze this Instagram account based on the filled-in data. Identify: 1) core content strategy, 2) posting patterns, 3) what specifically drives audience engagement, 4) how the user can adapt these techniques to their own style without copying."

**AI prompt for Content Ideas:**
> "Based on this inspiration account's strategy and my Content Pillars, suggest 3 post ideas I can adapt. For each idea, provide: topic, format (Reel/Carousel/Single), hook for the first line of the caption, and why it could work."

---

### 🆕 Database 4: Visual Briefs

A detailed visual brief for each post, with AI assistance in creation.

| Property | Type | Description |
|---|---|---|
| Name | Title | Short visual description |
| Linked Post | Relation → Content Hub | Which post this brief is for |
| Color Palette | Text | 3–5 hex codes or description (e.g. "warm peach + white + terracotta accent") |
| Mood | Select | Minimalist / Bright / Dark / Pastel / Energetic / Cozy |
| Composition | Select | Center subject / Flat lay / Text on background / Before–After / Grid / Portrait |
| Photo Elements | Text | What specifically should be in the image |
| Text Overlay | Text | If there's a text overlay — what to write |
| Font/Text Style | Select | Clean sans-serif / Handwritten / Bold statement / Minimal |
| Inspiration Reference | Relation → Inspiration DB | Visual reference from an inspiration account |
| Feed Compatibility | Select | Verified ✓ / Needs adjustment / Not checked |
| 🤖 AI Visual Suggestion | AI Custom Autofill | Full AI-generated visual brief |

**AI prompt for Visual Suggestion:**
> "Based on the post topic, its Content Pillar, the user's inspiration accounts, and their brand color palette, create a detailed visual brief: 1) Color palette — 3–5 specific colors with hex codes, 2) Composition — how to arrange elements, 3) What should be in the photo/image — specific objects, background, lighting, 4) Text overlay — if appropriate, what text and in what style, 5) Mood reference — which posts from Inspiration Accounts it should resemble. Ensure the post harmonizes with previous posts in the feed."

**Views:**

- **Gallery** — visual cards with preview and color palette
- **Kanban by status** — Not checked → Ready → Shot/Created

---

### Database 5: Ideas Bank

Quick idea capture on the go. One click converts any idea into a post.

| Property | Type | Description |
|---|---|---|
| Idea | Title | Short description |
| Source | Select | Trend / Follower asked / Competitor / Personal experience / Inspiration Account |
| Pillar | Relation → Pillars | Which content pillar it belongs to |
| Priority | Select | Hot / Normal / Later |
| Inspiration Ref | Relation → Inspiration DB | If the idea came from a specific account |
| AI Topic Suggestion | AI Custom Autofill | Suggests angles, formats, and visual concepts |

**AI prompt for Topic Suggestion (updated):**
> "Based on this idea, my Content Pillars, best-performing post analytics, and inspiration accounts, suggest 3 ways to execute it. For each: 1) Format (Reel/Carousel/Single), 2) Hook — first line of caption, 3) Visual concept — color palette, what's in the photo, style, 4) Why it will work (based on my engagement data)."

**Views:** Priority board + List grouped by pillar

---

### Database 6: Hashtag Sets

| Property | Type | Description |
|---|---|---|
| Set Name | Title | e.g. "Travel Vibes", "Food Flat Lay" |
| Hashtags | Text | Full hashtag list (copy-paste ready) |
| Category | Select | Niche / Broad / Community / Branded |
| Avg Post ER | Rollup | How effective this set is |

---

### Database 7: Collaborations

A lightweight CRM for partnerships and barters.

| Property | Type | Description |
|---|---|---|
| Brand / Partner | Title | Company name |
| Status | Select | Pitch / Negotiation / In Progress / Completed |
| Deadline | Date | Publication deadline |
| Deal Type | Select | Paid / Barter / Ambassadorship |
| Amount | Number | Deal value |
| Posts | Relation → Content Hub | Linked posts |

---

### Database 8: Weekly Stats

Aggregated account statistics by week.

| Property | Type | Description |
|---|---|---|
| Week | Date | Week start date |
| Followers | Number | Count at end of week |
| Growth | Formula | Difference from previous week |
| Reach / Profile Visits | Number ×2 | Total reach and visits |
| Best Post | Relation → Content Hub | Top-performing post of the week |
| AI Weekly Insight | AI Custom Autofill | Analysis: what worked, what didn't |

---

## §3. Dashboards

### Dashboard 1: Home Panel

The first thing the user sees when they open the template:

- This week's calendar (filtered view from Content Hub)
- Key metric cards: followers, weekly ER, posts published this month
- Pillars balance — mini gallery of Content Pillars with progress indicators
- Quick Add — button for instant post creation
- Upcoming collaborations (filtered: status ≠ Completed)
- 🆕 **Inspiration Feed** — latest notes and AI ideas from Inspiration Accounts

### Dashboard 2: Analytics & AI

- Published posts table with metrics (sortable by ER)
- Top 9 posts — gallery showcase
- Weekly Stats — table with trends
- AI Insight Block — embedded AI block with pre-written prompt
- Analysis by content type: which format delivers the best ER
- Analysis by posting time: when posts get the most engagement
- 🆕 **Inspiration Insights** — summary of patterns AI found across inspiration accounts

### Dashboard 3: Instagram Grid Preview

- **Basic:** Gallery view with 3-column grid, showing Cover Image as thumbnail. Filter: status = Ready + Published. Sort by date desc — simulates the feed
- **Pro:** Additionally includes an embedded Planoly/Later widget
- 🆕 **Brand Board** — section with brand color palette, mood board, and references from Inspiration Accounts. Also includes a Visual Briefs gallery for upcoming posts, so you can see how new posts will fit into the feed

---

## §4. AI Features (requires Notion Business)

All AI features are implemented through two mechanisms: AI Custom Autofill properties in databases and AI Blocks on pages.

### 4.1 AI Custom Autofill Properties

**Content Hub → AI Score**
> "Rate this post's potential on a 1–10 scale based on the caption, content type, Content Pillar, and patterns from my best-performing posts. Explain your reasoning and suggest improvements."

**Content Hub → AI Caption Improver**
> "Improve this caption: make it more engaging, add a compelling hook in the first line, include a clear CTA at the end. Preserve the author's original tone and voice."

**🆕 Inspiration Accounts → AI Strategy Analysis**
> "Analyze this Instagram account based on the filled-in data: what the user likes about it, color palette, formats, notes. Identify: 1) core content strategy, 2) posting patterns, 3) what drives engagement, 4) how to adapt these techniques without copying. Be specific."

**🆕 Inspiration Accounts → AI Content Ideas**
> "Based on this inspiration account's strategy and my Content Pillars, suggest 3 post ideas. For each: topic, format (Reel/Carousel/Single), first-line hook, visual concept (colors, what's in the photo, mood), and why it could work."

**🆕 Visual Briefs → AI Visual Suggestion**
> "Create a detailed visual brief for this post: 1) Color palette — 3–5 colors with hex codes that harmonize with the brand palette, 2) Composition — how to arrange elements, 3) Photo elements — specific objects, background, lighting, 4) Text overlay — if appropriate, text and style, 5) Mood reference — what to aim for visually. Ensure the post harmonizes with previous posts in the feed."

**Ideas Bank → AI Topic Suggestion**
> "Based on the idea, Content Pillars, best-performing post analytics, and Inspiration Accounts, suggest 3 ways to execute it. For each: format, hook, visual concept (colors + what's in the photo + style), and why it will work."

**Weekly Stats → AI Weekly Insight**
> "Analyze this week's statistics and linked posts. Which content type performed best? At what time? What were the inspiration accounts doing this week? Suggest specific actions for next week."

### 4.2 AI Blocks on Pages

**Weekly Topic Generator**
> "Based on my Content Pillars, recent posts, engagement data, and Inspiration Account strategies, suggest 5 topics for next week. Consider pillar balance and which formats show the best ER. For each topic, include a visual recommendation: colors and what should be in the photo."

**Optimal Posting Time Analysis**
> "Analyze my published posts in Content Hub. Compare engagement rate by time and day of the week. What's the best time for each format?"

**Posting Frequency Recommendation**
> "Based on my publishing history and follower growth metrics, recommend the optimal posting frequency for each content type (Reels, Carousels, Stories)."

**🆕 Inspiration Accounts Summary Analysis**
> "Analyze all my inspiration accounts together. What common patterns emerge? Which formats dominate? Which color palettes are popular? What topics recur? Based on this: what should I try in my own content?"

---

## §5. How the Inspiration → Ideas → Visual Brief System Works

This is the key user flow that ties the new features together:

```
┌─────────────────────┐
│  INSPIRATION        │
│  ACCOUNTS           │
│  (5–10 accounts)    │
│                     │
│  → AI analyzes      │
│    each strategy    │
│  → AI suggests      │
│    post ideas       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  IDEAS BANK         │
│                     │
│  Ideas from:        │
│  • Inspiration      │
│  • Trends           │
│  • Followers        │
│  • Own thoughts     │
│                     │
│  → AI suggests      │
│    3 angles +       │
│    visual for each  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  CONTENT HUB        │
│  (post creation)    │
│                     │
│  Topic + Caption    │
│  + Pillar + Date    │
│                     │
│  → AI Score         │
│  → AI Caption       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  VISUAL BRIEF       │
│                     │
│  → AI generates:    │
│    • Color palette  │
│      (hex codes)    │
│    • Composition    │
│    • Photo elements │
│    • Text overlay   │
│    • Mood reference │
│                     │
│  → Feed             │
│    compatibility    │
│    check            │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  GRID PREVIEW       │
│                     │
│  Visual check:      │
│  how the new post   │
│  looks in the feed  │
└─────────────────────┘
```

---

## §6. Integrations & Automation (Pro)

### 6.1 Instagram → Notion (Zapier / Make)

| Tool | What It Does | Cost |
|---|---|---|
| Zapier | Trigger on new post → creates entry in Notion | Free tier (100 tasks/mo) |
| Make.com | Same + more flexible scenarios | Free tier (1,000 ops/mo) |
| Note API Connector | Direct import of Instagram Insights | $9/mo |

**Scenario 1:** New post on Instagram → creates entry in Content Hub with status "Published"

**Scenario 2:** Weekly metrics collection → updates Weekly Stats and post metrics

**Scenario 3:** Publish Date = today → notification via Slack/Email/Telegram. Alternative: Notion Calendar sync with Google Calendar

**🆕 Scenario 4:** For Inspiration Accounts — periodic scraping of basic metrics (followers, posting frequency) via Instagram Scraper API + Make

### 6.2 Publishing Notifications

**Basic:** Notion Calendar sync with Google Calendar → reminders through standard calendar features

**Pro:** Zapier/Make scenario: if Content Hub has a post with date = today and status = "Ready" → send a reminder with caption and Visual Brief

---

## §7. Onboarding System

A built-in guide inside Notion — a dedicated "🚀 Start Here" page:

1. **Welcome** — brief overview of the template and what it offers
2. **Set Up Your Profile** — fill in Content Pillars, set goals, add your brand color palette
3. **🆕 Add Inspiration** — add 3–5 accounts you admire, fill in what appeals to you about them
4. **Create Your First Post** — step-by-step walkthrough with callouts
5. **🆕 Create a Visual Brief** — how to use AI to generate a visual brief
6. **Explore Views** — how to switch between calendar, kanban, grid
7. **Activate AI** — how to enable AI features (with a note about the Business plan requirement)
8. **(Pro) Set Up Integrations** — link to the PDF guide for Zapier/Make

Each step is a toggle block with a checkbox. The page can be deleted once setup is complete.

---

## §8. Design & Aesthetics

- **Color scheme** — minimalist palette with 2–3 accent colors (soft purple + sage green)
- **Custom icons** — consistent style for every page
- **Cover images** — branded headers for each section
- **Dividers** — visual separators between sections
- **Consistent layout** — uniform page structure throughout
- **🆕 Brand Board section** — a beautiful block with brand palette, mood board, and references that doubles as a selling point for the template itself

---

## §9. Development Roadmap

### Phase 1: Foundation (1–2 weeks)

1. Create all 8 databases with properties and relations
2. Configure views: calendar, kanban, gallery, table
3. Build 3 dashboards from linked views
4. Add formulas (Engagement Rate, follower growth, Pillar balance)
5. Populate with demo data (10–15 posts, 5 inspiration accounts, 5 visual briefs)

### Phase 2: AI & Design (1 week)

1. Configure all AI Custom Autofill properties with prompts
2. Add AI Blocks to dashboards
3. Test the flow: Inspiration → Ideas → Content → Visual Brief → Grid
4. Create cover images and icons
5. Polish visual design: colors, dividers, consistency

### Phase 3: Pro Version (1–2 weeks)

1. Set up and test Zapier/Make scenarios
2. Write a PDF integration guide with screenshots
3. Add embedded widgets for feed preview
4. Set up automatic Inspiration Accounts scraping
5. Configure Notion Calendar sync

### Phase 4: Launch & Marketing (1 week)

1. Create the "Start Here" onboarding page
2. Clean demo data for the Basic version
3. Prepare screenshots and mockups for the listing
4. Publish on Gumroad / Notion Marketplace
5. Create promotional content: video demo, Instagram posts

---

## §10. Template Structure Summary

| Page | Contents | Basic | Pro |
|---|---|---|---|
| 🏠 Dashboard | Home panel with key metrics | ✓ | ✓ |
| 📝 Content Hub | 5 views: calendar, kanban, grid, table, top | ✓ | ✓ |
| 🎨 Grid Preview | Feed preview + mood board + palette | ✓ | ✓ + embed |
| 🆕 ⭐ Inspiration | Inspiration accounts + AI analysis | ✓ | ✓ + auto |
| 🆕 🖼️ Visual Briefs | Visual briefs for posts | ✓ | ✓ |
| 💡 Ideas Bank | Idea capture with AI suggestions | ✓ | ✓ |
| 📊 Analytics | Statistics dashboard + AI Insights | ✓ | ✓ + auto |
| 🎯 Pillars | Content pillars + balance tracker | ✓ | ✓ |
| #️⃣ Hashtags | Hashtag sets + effectiveness tracking | ✓ | ✓ |
| 🤝 Collabs | Collaborations + CRM | ✓ | ✓ |
| ⚙️ Automations | Zapier/Make scenarios + PDF guide | ✗ | ✓ |
| 🚀 Start Here | Onboarding guide | ✓ | ✓ |

---

*— End of Blueprint v2.0 —*
