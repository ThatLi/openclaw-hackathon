# 🦀 MrKrabs: The Zero-UI CCA Task Agent
**Built for the 2026 Agnes Hackathon**

### The Problem
CCA EXCO members waste hours manually syncing Telegram "noise" into spreadsheets and chasing members for deadlines.

### The Solution
MrKrabs is a "Zero-UI" agent that sits in the group chat, listens to natural conversation, and uses **Agnes 1.5 Pro** to implicitly extract tasks, deadlines, and owners—syncing them instantly to a structured CSV database.

### Technical Highlights
- **Engine:** Agnes 1.5 Pro (via ZenMux Gateway)
- **Zero-UI:** No slash commands required; works via natural language processing.
- **Database:** Local CSV for high-speed, rate-limit-safe logging.
