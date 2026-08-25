<div align="center">
  <h1>🚀 Contro Discord Bot Platform</h1>
  <p><b>An Advanced, Modular, and Interface-Driven Discord Bot Platform</b></p>
  
  [![Turkish](https://img.shields.io/badge/Language-T%C3%BCrk%C3%A7e-red)](README-tr.md)
  [![English](https://img.shields.io/badge/Language-English-blue)](#)
</div>

---

Contro is a modern, premium-focused Discord bot platform. It is designed to be fully modular, allowing communities to cherry-pick features and manage everything via a sleek Web Dashboard or directly within Discord using an innovative, interactive interface.

## 🌐 Next.js Web Dashboard

The Discord bot works in perfect harmony with a **Next.js 15 Web Dashboard**. 
Server admins can view real-time statistics, configure complex modules, and manage their subscription directly from their browser, all synchronized instantly with the bot.

👉 **[Visit the Web Dashboard: controapp.vercel.app](https://controapp.vercel.app/)**

## 🌟 Key Features

- **🧩 100% Modular Architecture:** Everything from Moderation to Leveling is a standalone feature. Turn on what you need, disable what you don't.
- **🎛️ Interface-First Management:** Forget typing long commands. Manage your entire server through intuitive dropdowns, buttons, and modals in the /settings panel.
- **💳 Premium & Crypto Ready:** Native support for premium tiers and crypto payments (BTC, ETH, USDC, USDT).
- **🛡️ Uncompromising Security:** Built with strict permission boundaries. Every action is gated, validated, and logged to ensure maximum security for large communities.
- **⚡ High Performance:** Engineered for efficiency. Uses background processing for heavy tasks, optimized database indexing (MongoDB), and RAM-efficient image generation.

## 🖼️ Dynamic Image Generation

Contro features a powerful, built-in image generator for Welcome and Goodbye events, rendering beautiful, custom-branded banners on the fly.

<div align="center">
  <img src="assets/welcome-banner.png" alt="Welcome Banner Example" width="45%">
  <img src="assets/goodbye-banner.png" alt="Goodbye Banner Example" width="45%">
</div>

## 🛠️ Modules & All Commands

Contro comes packed with over 20+ built-in modules. Below is the comprehensive list of commands and functions:

### ⚙️ Core & Administration
- /settings (or /admin): Opens the interactive management panel to configure all modules.
- /goal: Set persistent goals for the bot's background tasks.
- /schedule: Schedule recurring events and jobs.
- /ping: Check the bot's current latency and status.

### 🛡️ Moderation & Security
- /purge all count: or /clear amount:: Clean up channels effortlessly by deleting a bulk of messages.
- /ban add @user: Ban a user from the server.
- **Auto-Mod:** Robust filters to catch spam, profanity, and phishing links automatically.
- **Audit Logging:** Comprehensive tracking of all server actions.
- **Security Limits:** Prevents mass-banning, mass-kicking, and channel wiping by compromised admins.

### 🎮 Engagement & Community
- **Leveling (/rank, /leaderboard):** Reward active members with XP and custom role rewards based on text and voice activity.
- **Giveaways (/giveaway create prize: limit:):** Host and manage giveaways, complete with participant limits and role restrictions.
- **Role Menus (Reaction Roles):** Let users pick their own roles seamlessly via buttons and dropdowns.
- **Starboard:** Highlight the best messages in your community.
- **Custom Commands:** Create server-specific commands without writing code.

### 🎫 Support & Utility
- **Tickets (/ticket):** Advanced ticketing system with transcripts, claiming, and private threads.
- **Temp Channels (/vc limit <number>):** Dynamic voice channels that create themselves and delete when empty. Users can control their channel limits.
- **AI Chat (/imagine prompt:):** Integrate smart, AI-driven conversations and image generation directly into your server.

### 🎲 Fun & Extra
- /meme: Fetch the latest memes.
- /movie [name]: Get movie information and ratings.
- /play [song], /youtube: Play music or fetch YouTube videos.
- /bump: Bump your server on Disboard to attract new members.
- /poll create: Create interactive polls for your members.

---
*Note: This repository serves as a showcase. The core source code for Contro is maintained in a private repository to protect proprietary systems.*
