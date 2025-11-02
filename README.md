# 🚀 EVE Online AI Discord Bot

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-green.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An intelligent Discord bot for EVE Online with **Retrieval-Augmented Generation (RAG)** powered by local LLM and a comprehensive knowledge base of 300+ documents.

---

## ✨ Features

- 🤖 **AI-Powered Chat** - Natural language conversations about EVE Online
- 📚 **332+ Document Knowledge Base** - EVE Uni Wiki articles + Static Data Export
- 🚀 **Ship Database** - 100+ ships with complete stats and descriptions
- ⚙️ **Module Database** - 200+ modules and items with technical details
- 💰 **Live Market Data** - Real-time prices via ESI API
- ⚡ **Redis Caching** - Fast response times
- 🔒 **Local LLM** - Complete privacy, runs on your own hardware
- 🐳 **Fully Dockerized** - Easy deployment and scaling

---

## 🎯 What Can It Do?

Ask questions like:

- *"What's the difference between a Frigate and a Cruiser?"*
- *"Show me the stats for an Astero"*
- *"How does capacitor management work?"*
- *"Best fitting for PvP Rifter?"*
- *"What are Abyssal Deadspace sites?"*
- *"Current price for Tritanium in Jita?"*

The bot uses RAG to provide accurate, contextual answers based on official EVE data and community knowledge.

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Discord Users  │
└────────┬────────┘
         │
         v
┌─────────────────────────────────┐
│   Discord Bot (Python)          │
│   - discord.py                  │
│   - Conversation Manager        │
│   - Command Handler             │
└────┬──────────────────┬─────────┘
     │                  │
     v                  v
┌──────────────┐   ┌──────────────┐
│   Ollama     │   │    Redis     │
│ (Local LLM)  │   │   (Cache)    │
└──────┬───────┘   └──────────────┘
       │
       v
┌──────────────────┐
│  ChromaDB (RAG)  │
│  332 Documents   │
│  - Wiki Articles │
│  - Ship Data     │
│  - Module Data   │
└──────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- [Ollama](https://ollama.ai/) installed locally
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))

### 1. Clone the Repository

```bash
git clone https://github.com/burnshall-ui/-AI_lokal_Discord_Bot.git
cd -AI_lokal_Discord_Bot
```

### 2. Setup Ollama

```bash
# Install models
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env and add your Discord Bot Token
nano .env
```

### 4. Start the Bot

```bash
# Start all services
docker compose up -d

# Check logs
docker logs eve-discord-bot -f
```

### 5. Load Knowledge Base

```bash
# Load EVE Uni Wiki articles (~32 documents)
docker exec eve-discord-bot python3 load_knowledge.py --wiki-only

# (Optional) Download and load SDE data
cd data
mkdir -p sde
cd sde
wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2
bunzip2 sqlite-latest.sqlite.bz2

# Load ships and modules (~300 documents)
docker exec eve-discord-bot python3 load_knowledge.py --sde-only
```

### 6. Invite Bot to Your Server

Use the OAuth2 URL from Discord Developer Portal with these scopes:
- `bot`
- `applications.commands`

Permissions needed: `Send Messages`, `Read Message History`, `Use Slash Commands`

---

## 📖 Usage

### Chat Commands

Mention the bot to start a conversation:
```
@Nostromo AI What is a Frigate?
```

### Bot Commands

- `!help` - Show all available commands
- `!status` - Bot status and stats
- `!rag` - RAG system statistics
- `!rag-reload` - Reconnect to ChromaDB
- `!clear` - Clear conversation history
- `!model [name]` - Change LLM model

### EVE Commands

- `!price <item>` - Get market price for an item
- `!ship <name>` - Get ship information
- `!server` - EVE Online server status

---

## 🔧 Configuration

### Environment Variables

All configuration is done via `.env` file. See `.env.example` for template.

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token | Required |
| `OLLAMA_BASE` | Ollama API endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM model for chat | `llama3.1:8b` |
| `OLLAMA_EMBEDDING_MODEL` | Model for embeddings | `nomic-embed-text` |
| `CHROMADB_HOST` | ChromaDB host | `localhost` |
| `CHROMADB_PORT` | ChromaDB port | `8000` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `COMMAND_PREFIX` | Bot command prefix | `!` |

---

## 📚 Knowledge Base Management

### Loading Wiki Articles

```bash
# Load all curated articles
docker exec eve-discord-bot python3 load_knowledge.py --wiki-only

# Load specific number of articles
docker exec eve-discord-bot python3 load_knowledge.py --wiki-only --wiki-limit 10
```

### Loading SDE Data

```bash
# Download SDE database (one-time)
cd data/sde
wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2
bunzip2 sqlite-latest.sqlite.bz2

# Load into ChromaDB
docker exec eve-discord-bot python3 load_knowledge.py --sde-only

# Custom amounts
docker exec eve-discord-bot python3 load_knowledge.py --sde-only --ships 50 --modules 100
```

### Load Both

```bash
docker exec eve-discord-bot python3 load_knowledge.py --both
```

---

## 🛠️ Development

### Project Structure

```
eve-discord-bot/
├── bot.py                  # Main bot application
├── rag_system.py          # ChromaDB RAG implementation
├── sde_loader.py          # Static Data Export loader
├── wiki_scraper.py        # EVE Uni Wiki scraper
├── load_knowledge.py      # Knowledge base management CLI
├── esi_client.py          # ESI API client
├── docker-compose.yml     # Docker services configuration
├── Dockerfile             # Bot container image
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

---

## 🧪 Troubleshooting

### Bot won't start

```bash
# Check logs
docker logs eve-discord-bot --tail 50

# Verify all services are running
docker ps

# Restart services
docker compose restart
```

### ChromaDB connection issues

```bash
# Reconnect via Discord
!rag-reload

# Or restart ChromaDB
docker restart eve-chromadb
```

### RAG not working

```bash
# Check ChromaDB status
docker exec eve-discord-bot python3 -c "from rag_system import get_rag_system; print(get_rag_system().get_stats())"

# Reload knowledge base
docker exec eve-discord-bot python3 load_knowledge.py --wiki-only
```

---

## 📊 Performance

- **Response Time**: 1-3 seconds for typical queries
- **Memory Usage**: ~500 MB (bot + ChromaDB + Redis)
- **Knowledge Base**: 332 documents, ~15 MB embedded
- **LLM**: Runs on host GPU/CPU (not in container)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **EVE University** - For the comprehensive wiki
- **CCP Games** - For EVE Online and the ESI API
- **Fuzzwork** - For SDE database conversions
- **Ollama** - For local LLM inference
- **ChromaDB** - For vector database and RAG
- **discord.py** - For Discord API integration

---

## ⚠️ Disclaimer

This is a third-party tool and is not affiliated with or endorsed by CCP Games. EVE Online and all associated logos and designs are the intellectual property of CCP hf.

---

**Made with ❤️ for the EVE Online community**

*Fly safe, capsuleers! o7*
