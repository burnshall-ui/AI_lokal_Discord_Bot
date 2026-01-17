"""
EVE Discord Bot - V2 mit RAG + ESI
"""

import discord
from discord.ext import commands
import os
import aiohttp
import logging
import traceback
from typing import Optional
from rag_system import get_rag_system
from esi_client import get_esi_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('EVE-Bot')

# Configuration
TOKEN = os.getenv('DISCORD_BOT_TOKEN') or os.getenv('DISCORD_TOKEN')
OLLAMA_BASE = os.getenv('OLLAMA_BASE', 'http://localhost:11434')
OLLAMA_CHAT_URL = f"{OLLAMA_BASE}/api/chat"
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
conversation_history = {}
MAX_HISTORY = 10

# Initialize RAG & ESI
rag = get_rag_system()
esi = get_esi_client()

SYSTEM_PROMPT = """Du bist ein spezialisierter KI-Assistent für EVE Online Spieler.
Du hilfst bei allen Fragen zu EVE Online, nutzt deine Wissensdatenbank und Echtzeit-Daten für präzise Antworten.

Wichtig:
- Nutze den bereitgestellten Context aus der Knowledge Base
- Gib konkrete, hilfreiche Antworten mit EVE-Terminologie
- Wenn du Live-Daten (Preise, Status) hast, nutze sie
- Sei freundlich aber präzise
- Antworte auf English"""


@bot.event
async def on_ready():
    logger.info(f'{bot.user} ist online!')
    logger.info(f'RAG System: {rag.get_stats()}')
    await bot.change_presence(activity=discord.Game(name="EVE Online | !help"))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.startswith(COMMAND_PREFIX):
        await bot.process_commands(message)
        return
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        await handle_ai_message(message)


async def handle_ai_message(message):
    async with message.channel.typing():
        try:
            user_id = str(message.author.id)
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            
            clean_content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            
            # RAG: fetch relevant context
            rag_context = rag.search_knowledge(clean_content)
            logger.info(f"RAG Query: '{clean_content}' -> {len(rag_context)} Ergebnisse")

            # Build messages for LLM
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            # Add context if available
            if rag_context:
                # Format RAG results properly
                context_texts = []
                for i, doc in enumerate(rag_context, 1):
                    context_texts.append(f"[Quelle {i}] {doc['content']}")

                context_msg = f"""KNOWLEDGE BASE CONTEXT:
{chr(10).join(context_texts)}

Nutze die obigen Informationen aus der EVE Knowledge Base für deine Antwort."""

                messages.append({"role": "system", "content": context_msg})
                logger.info(f"RAG Context hinzugefügt: {len(rag_context)} Dokumente")
            
            # Conversation history
            for msg in conversation_history[user_id][-5:]:
                messages.append(msg)
            
            # User message
            messages.append({"role": "user", "content": clean_content})
            
            # LLM call with optimized parameters for fact mode
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.2,      # Niedriger für präzise Fakten
                    "top_p": 0.8,
                    "top_k": 40,
                    "repeat_penalty": 1.15,
                    "num_ctx": 2048,
                    "num_predict": 160       # Kurze, prägnante Antworten
                },
                "keep_alive": "1h"
            }
            
            logger.info(f"Calling Ollama with {len(messages)} messages")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(OLLAMA_CHAT_URL, json=payload, timeout=180) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        ai_response = data.get('message', {}).get('content', 'Keine Antwort.')
                        
                        # Update history
                        conversation_history[user_id].append({"role": "user", "content": clean_content})
                        conversation_history[user_id].append({"role": "assistant", "content": ai_response})
                        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]
                        
                        # Discord limit
                        if len(ai_response) > 2000:
                            ai_response = ai_response[:1997] + "..."
                        
                        await message.reply(ai_response)
                        logger.info(f"Response sent successfully")
                    else:
                        error_text = await resp.text()
                        logger.error(f"Ollama error {resp.status}: {error_text}")
                        await message.reply(f"Ollama Fehler (Status {resp.status})")
                        
        except Exception as e:
            error_msg = f"Error: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            try:
                await message.reply(f"Fehler: {type(e).__name__}")
            except:
                pass


# ===== COMMANDS =====

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="🚀 EVE Discord AI Bot", color=discord.Color.blue())
    embed.add_field(
        name="💬 Konversation", 
        value="Erwähne @Bot für KI-Antworten mit RAG-System", 
        inline=False
    )
    embed.add_field(
        name="📊 Info Commands",
        value="`!status` - Bot Status\n`!rag` - RAG System Stats\n`!rag-reload` - ChromaDB neu verbinden\n`!model` - LLM Model",
        inline=False
    )
    embed.add_field(
        name="🎮 EVE Commands", 
        value="`!price <item>` - Marktpreis\n`!ship <name>` - Schiff Info\n`!server` - Server Status", 
        inline=False
    )
    embed.add_field(
        name="🗑️ Utility", 
        value="`!clear` - History löschen", 
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command(name='status')
async def status_command(ctx):
    embed = discord.Embed(title="📊 Bot Status", color=discord.Color.green())
    embed.add_field(name="Status", value="✅ Online", inline=True)
    embed.add_field(name="Latenz", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Konversationen", value=len(conversation_history), inline=True)
    embed.add_field(name="LLM Model", value=OLLAMA_MODEL, inline=False)
    
    # RAG Stats
    rag_stats = rag.get_stats()
    if rag_stats.get('status') == 'connected':
        embed.add_field(
            name="RAG System", 
            value=f"✅ {rag_stats.get('documents', 0)} Dokumente", 
            inline=True
        )
    else:
        embed.add_field(name="RAG System", value="❌ Disconnected", inline=True)
    
    await ctx.send(embed=embed)


@bot.command(name='rag')
async def rag_command(ctx):
    """Shows RAG system stats."""
    stats = rag.get_stats()

    embed = discord.Embed(title="🧠 RAG System", color=discord.Color.purple())
    embed.add_field(name="Status", value=stats.get('status', 'unknown'), inline=True)
    embed.add_field(name="Dokumente", value=stats.get('documents', 0), inline=True)
    embed.add_field(name="Collection", value=stats.get('collection', 'N/A'), inline=True)
    embed.add_field(name="Embedding Model", value=stats.get('embedding_model', 'N/A'), inline=False)

    await ctx.send(embed=embed)


@bot.command(name='rag-reload')
async def rag_reload_command(ctx):
    """Attempts to reconnect to ChromaDB."""
    async with ctx.typing():
        success = rag.reconnect()
        if success:
            stats = rag.get_stats()
            await ctx.send(f"✅ ChromaDB erfolgreich verbunden!\n📊 Dokumente: {stats.get('documents', 0)}")
        else:
            await ctx.send("❌ ChromaDB Verbindung fehlgeschlagen. Siehe Logs für Details.")


@bot.command(name='clear')
async def clear_command(ctx):
    user_id = str(ctx.author.id)
    if user_id in conversation_history:
        del conversation_history[user_id]
        await ctx.send('✅ Conversation History gelöscht!')
    else:
        await ctx.send('ℹ️ Keine History vorhanden.')


@bot.command(name='model')
async def model_command(ctx, model_name: str = None):
    global OLLAMA_MODEL
    if model_name:
        OLLAMA_MODEL = model_name
        await ctx.send(f'✅ Model geändert zu: {OLLAMA_MODEL}')
    else:
        await ctx.send(f'ℹ️ Aktuelles Model: {OLLAMA_MODEL}')


# ===== ESI COMMANDS =====

@bot.command(name='price')
async def price_command(ctx, *, item_name: str):
    """Shows market price for an item in Jita."""
    async with ctx.typing():
        try:
            # Search item
            types = esi.search_type(item_name)
            if not types:
                await ctx.send(f"❌ Item '{item_name}' nicht gefunden")
                return
            
            # Use first match
            item = types[0]
            type_id = item['type_id']
            
            # Fetch market prices
            prices = esi.get_market_prices(type_id)
            if not prices:
                await ctx.send(f"❌ Keine Marktdaten für '{item['name']}'")
                return
            
            # Build embed
            embed = discord.Embed(
                title=f"💰 {item['name']}", 
                color=discord.Color.gold()
            )
            
            # Format prices
            buy_max = f"{prices['buy_max']:,.2f} ISK" if prices['buy_max'] > 0 else "N/A"
            sell_min = f"{prices['sell_min']:,.2f} ISK" if prices['sell_min'] > 0 else "N/A"
            
            embed.add_field(name="Jita Buy", value=buy_max, inline=True)
            embed.add_field(name="Jita Sell", value=sell_min, inline=True)
            embed.add_field(
                name="Volume", 
                value=f"Buy: {prices['buy_volume']:,}\nSell: {prices['sell_volume']:,}", 
                inline=False
            )
            embed.set_footer(text="Quelle: ESI API - The Forge Region")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Price command error: {e}")
            await ctx.send(f"❌ Fehler beim Abrufen der Preise: {type(e).__name__}")


@bot.command(name='ship')
async def ship_command(ctx, *, ship_name: str):
    """Shows info about a ship."""
    async with ctx.typing():
        try:
            # Search ship
            types = esi.search_type(ship_name)
            if not types:
                await ctx.send(f"❌ Schiff '{ship_name}' nicht gefunden")
                return
            
            ship = types[0]
            
            embed = discord.Embed(
                title=f"🚀 {ship['name']}", 
                description=ship.get('description', 'Keine Beschreibung'),
                color=discord.Color.blue()
            )
            
            # Stats from ESI
            if 'mass' in ship:
                embed.add_field(name="Masse", value=f"{ship['mass']:,} kg", inline=True)
            if 'volume' in ship:
                embed.add_field(name="Volume", value=f"{ship['volume']:,} m³", inline=True)
            if 'capacity' in ship:
                embed.add_field(name="Cargo", value=f"{ship['capacity']:,} m³", inline=True)
            
            embed.set_footer(text="Quelle: ESI API")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Ship command error: {e}")
            await ctx.send(f"❌ Fehler: {type(e).__name__}")


@bot.command(name='server')
async def server_command(ctx):
    """Shows EVE server status."""
    async with ctx.typing():
        try:
            status = esi.get_server_status()
            if not status:
                await ctx.send("❌ Konnte Server Status nicht abrufen")
                return
            
            embed = discord.Embed(
                title="🖥️ EVE Online Server", 
                color=discord.Color.green() if status.get('players', 0) > 0 else discord.Color.red()
            )
            
            embed.add_field(
                name="Status", 
                value="✅ Online" if status.get('players', 0) > 0 else "❌ Offline", 
                inline=True
            )
            embed.add_field(
                name="Spieler", 
                value=f"{status.get('players', 0):,}", 
                inline=True
            )
            embed.add_field(
                name="Version", 
                value=status.get('server_version', 'Unknown'), 
                inline=True
            )
            
            embed.set_footer(text="Quelle: ESI API")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Server command error: {e}")
            await ctx.send(f"❌ Fehler: {type(e).__name__}")


if __name__ == '__main__':
    if not TOKEN or TOKEN.strip() == "your_discord_bot_token_here":
        logger.error('❌ DISCORD_BOT_TOKEN fehlt!')
        exit(1)
    
    logger.info("🚀 Starting EVE Discord Bot V2...")
    bot.run(TOKEN)
