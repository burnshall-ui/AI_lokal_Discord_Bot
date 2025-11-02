#!/usr/bin/env python3
"""
EVE Knowledge Base Loader - Master Script
Kombiniert SDE und Wiki-Daten für ChromaDB
"""

import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KnowledgeLoader")


def load_wiki_only(limit: int = None):
    """Lädt nur Wiki-Artikel"""
    from wiki_scraper import EVEWikiScraper

    scraper = EVEWikiScraper()

    if limit:
        articles = scraper.TOP_ARTICLES[:limit]
        logger.info(f"📚 Lade {limit} Wiki-Artikel...")
    else:
        articles = scraper.TOP_ARTICLES
        logger.info(f"📚 Lade ALLE {len(articles)} Wiki-Artikel...")

    loaded = scraper.load_all(article_list=articles)
    return loaded


def load_sde_only(ships: int = 100, modules: int = 200):
    """Lädt nur SDE-Daten"""
    from sde_loader import SDELoader

    loader = SDELoader()

    # Check ob SDE DB existiert
    if not Path(loader.db_path).exists():
        logger.error(f"❌ SDE Datenbank nicht gefunden: {loader.db_path}")
        logger.info("💡 Download: https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2")
        logger.info("   Entpacke mit: bunzip2 sqlite-latest.sqlite.bz2")
        logger.info(f"   Speichere als: {loader.db_path}")
        return False

    logger.info(f"📦 Lade SDE-Daten: {ships} Schiffe, {modules} Module")
    success = loader.load_all(ships_limit=ships, modules_limit=modules)

    return success


def load_both(wiki_limit: int = None, ships: int = 100, modules: int = 200):
    """Lädt Wiki UND SDE"""
    logger.info("🚀 FULL KNOWLEDGE BASE LOAD")
    logger.info("=" * 60)

    # 1. Wiki (schneller, keine Dependencies)
    logger.info("\n📚 PHASE 1: Wiki-Artikel")
    logger.info("-" * 60)
    wiki_loaded = load_wiki_only(limit=wiki_limit)

    # 2. SDE (braucht DB-File)
    logger.info("\n📦 PHASE 2: SDE-Daten")
    logger.info("-" * 60)
    sde_success = load_sde_only(ships=ships, modules=modules)

    # Stats
    logger.info("\n" + "=" * 60)
    logger.info("✅ KNOWLEDGE BASE LOADING COMPLETE")
    logger.info("=" * 60)

    from rag_system import get_rag_system
    rag = get_rag_system()
    stats = rag.get_stats()

    if stats['status'] == 'connected':
        print(f"\n📊 FINAL STATS:")
        print(f"   Total Documents: {stats['documents']}")
        print(f"   Collection: {stats['collection']}")
        print(f"   Embedding Model: {stats['embedding_model']}")
        print(f"   Host: {stats['host']}")
    else:
        print(f"\n⚠️  RAG Status: {stats['status']}")

    return wiki_loaded > 0 or sde_success


def main():
    parser = argparse.ArgumentParser(
        description='Lädt EVE Knowledge Base in ChromaDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Nur Wiki (schnell, 5 Artikel)
  python load_knowledge.py --wiki-only --wiki-limit 5

  # Nur Wiki (alle ~50 Artikel)
  python load_knowledge.py --wiki-only

  # Nur SDE
  python load_knowledge.py --sde-only

  # Beides (empfohlen)
  python load_knowledge.py --both

  # Custom
  python load_knowledge.py --both --wiki-limit 10 --ships 50 --modules 100
        """
    )

    parser.add_argument('--wiki-only', action='store_true',
                        help='Lädt nur Wiki-Artikel')
    parser.add_argument('--sde-only', action='store_true',
                        help='Lädt nur SDE-Daten')
    parser.add_argument('--both', action='store_true',
                        help='Lädt Wiki + SDE (empfohlen)')

    parser.add_argument('--wiki-limit', type=int, default=None,
                        help='Anzahl Wiki-Artikel (Standard: alle ~50)')
    parser.add_argument('--ships', type=int, default=100,
                        help='Anzahl Schiffe aus SDE (Standard: 100)')
    parser.add_argument('--modules', type=int, default=200,
                        help='Anzahl Module aus SDE (Standard: 200)')

    args = parser.parse_args()

    # Default wenn keine Option gewählt
    if not (args.wiki_only or args.sde_only or args.both):
        parser.print_help()
        print("\n⚠️  Keine Option gewählt!")
        print("💡 Empfehlung: python load_knowledge.py --wiki-only")
        sys.exit(1)

    # Execute
    try:
        if args.wiki_only:
            load_wiki_only(limit=args.wiki_limit)
        elif args.sde_only:
            load_sde_only(ships=args.ships, modules=args.modules)
        elif args.both:
            load_both(wiki_limit=args.wiki_limit, ships=args.ships, modules=args.modules)

    except KeyboardInterrupt:
        print("\n\n⚠️  Abgebrochen durch Benutzer")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fehler: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
