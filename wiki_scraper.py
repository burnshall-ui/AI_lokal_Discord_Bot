"""
EVE University wiki scraper.
Loads key wiki articles and prepares them for ChromaDB.
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
from typing import List, Dict, Optional
from rag_system import get_rag_system

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Wiki-Scraper")


class EVEWikiScraper:
    def __init__(self):
        self.base_url = "https://wiki.eveuniversity.org"
        self.api_url = f"{self.base_url}/api.php"
        self.rag = get_rag_system()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EVE-Discord-Bot/1.0 (Educational Purpose)'
        })

    # Top EVE Uni wiki articles - curated list
    TOP_ARTICLES = [
        # Ships
        "Frigates", "Destroyers", "Cruisers", "Battlecruisers", "Battleships",
        "Interceptors", "Assault_Frigates", "Stealth_Bombers",
        "Astero", "Stratios", "Nestor",  # SOE ships
        "Pacifier", "Enforcer", "Marshal",  # Concord ships

        # Game mechanics
        "Fitting", "Capacitor", "Shield_tanking", "Armor_tanking",
        "Damage_types", "Electronic_warfare", "Targeting",
        "Navigation", "Warp_drive_operation",

        # Activities
        "Mining", "Exploration", "Mission_running",
        "Abyssal_Deadspace", "Incursions", "Faction_Warfare",
        "Wormholes", "Planetary_Interaction",

        # PvP
        "PvP", "Fleet_combat", "Solo_PvP", "Small_gang",
        "Tackle", "Scanning", "Bookmarks",

        # Economy
        "Trading", "Market", "Industry", "Manufacturing",
        "Planetary_commodities", "Moon_mining",

        # Skills
        "Skills_and_learning", "Skill_training", "Implants",
        "Neural_remapping",

        # New player
        "New_player_guide", "Career_Agents", "ISK_making_guide",
        "Ship_naming_guide", "Overview_guide"
    ]

    def get_article_content(self, title: str) -> Optional[Dict]:
        """Fetches a wiki article via API."""
        params = {
            'action': 'query',
            'titles': title,
            'prop': 'extracts|info',
            'explaintext': True,
            'exsectionformat': 'plain',
            'format': 'json',
            'inprop': 'url'
        }

        try:
            response = self.session.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            pages = data.get('query', {}).get('pages', {})
            page = next(iter(pages.values()))

            if 'missing' in page:
                logger.warning(f"Artikel '{title}' nicht gefunden")
                return None

            return {
                'title': page.get('title', title),
                'pageid': page.get('pageid'),
                'content': page.get('extract', ''),
                'url': page.get('fullurl', f"{self.base_url}/wiki/{title}")
            }

        except Exception as e:
            logger.error(f"Fehler beim Laden von '{title}': {e}")
            return None

    def clean_content(self, content: str, max_length: int = 4000) -> str:
        """Cleans and truncates wiki content."""
        # Remove extra blank lines
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = '\n'.join(lines)

        # Truncate if too long (for better RAG)
        if len(content) > max_length:
            content = content[:max_length] + "\n\n[...gekürzt, siehe Wiki für vollständigen Artikel...]"

        return content

    def format_for_rag(self, article: Dict) -> str:
        """Formats a wiki article for RAG."""
        text = f"""
EVE WIKI: {article['title']}

{self.clean_content(article['content'])}

Quelle: EVE University Wiki
Link: {article['url']}
Kategorie: Game Guide / Tutorial
"""
        return text.strip()

    def load_article_to_chromadb(self, title: str) -> bool:
        """Loads a single article into ChromaDB."""
        article = self.get_article_content(title)

        if not article or not article['content']:
            return False

        doc_id = f"wiki_{article['pageid']}"
        text = self.format_for_rag(article)

        metadata = {
            "source": "eve_wiki",
            "type": "guide",
            "title": article['title'],
            "url": article['url']
        }

        success = self.rag.add_document(doc_id, text, metadata)

        if success:
            logger.info(f"✅ Wiki: {article['title']}")
        else:
            logger.warning(f"⚠️  Wiki: {article['title']} - Upload fehlgeschlagen")

        return success

    def load_all(self, article_list: Optional[List[str]] = None, delay: float = 1.0):
        """Loads multiple articles into ChromaDB."""
        if article_list is None:
            article_list = self.TOP_ARTICLES

        logger.info(f"🚀 Starte Wiki-Scraping für {len(article_list)} Artikel...")

        loaded = 0
        failed = 0

        for i, title in enumerate(article_list, 1):
            logger.info(f"[{i}/{len(article_list)}] Lade: {title}")

            if self.load_article_to_chromadb(title):
                loaded += 1
            else:
                failed += 1

            # Be nice to the server
            if i < len(article_list):
                time.sleep(delay)

        logger.info(f"✅ Wiki-Scraping abgeschlossen: {loaded} erfolgreich, {failed} fehlgeschlagen")
        return loaded


if __name__ == "__main__":
    scraper = EVEWikiScraper()

    print("=" * 60)
    print("EVE WIKI SCRAPER")
    print("=" * 60)
    print(f"📚 Lade {len(scraper.TOP_ARTICLES)} Top-Artikel...")
    print()

    loaded = scraper.load_all()

    print()
    print("=" * 60)
    print(f"✅ {loaded} Wiki-Artikel in ChromaDB geladen!")

    stats = scraper.rag.get_stats()
    print(f"📊 Gesamt Dokumente in DB: {stats.get('documents', 0)}")
    print("=" * 60)
