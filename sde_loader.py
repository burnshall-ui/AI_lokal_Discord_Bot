"""
EVE SDE (Static Data Export) loader.
Loads ship, module, and item data from SQLite into ChromaDB.
"""

import sqlite3
import logging
from typing import List, Dict, Optional
from rag_system import get_rag_system

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SDE-Loader")


class SDELoader:
    def __init__(self, sde_db_path: str = "data/sde/sqlite-latest.sqlite"):
        self.db_path = sde_db_path
        self.rag = get_rag_system()
        self.conn = None

    def connect(self):
        """Connects to the SDE SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"✅ Verbunden zu SDE DB: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"❌ SDE DB Verbindung fehlgeschlagen: {e}")
            return False

    def get_ship_types(self, limit: int = 100) -> List[Dict]:
        """Fetches ship types from the SDE."""
        if not self.conn:
            return []

        query = """
        SELECT
            typeID, typeName, description, mass, volume, capacity,
            groupID, marketGroupID, published
        FROM invTypes
        WHERE groupID IN (
            SELECT groupID FROM invGroups
            WHERE categoryID = 6  -- Ships category
        )
        AND published = 1
        LIMIT ?
        """

        cursor = self.conn.execute(query, (limit,))
        ships = []

        for row in cursor:
            ships.append({
                'typeID': row['typeID'],
                'typeName': row['typeName'],
                'description': row['description'] or '',
                'mass': row['mass'],
                'volume': row['volume'],
                'capacity': row['capacity']
            })

        logger.info(f"📦 {len(ships)} Schiffe aus SDE geladen")
        return ships

    def get_module_types(self, limit: int = 200) -> List[Dict]:
        """Fetches modules/items from the SDE."""
        if not self.conn:
            return []

        query = """
        SELECT
            typeID, typeName, description, mass, volume,
            groupID, marketGroupID
        FROM invTypes
        WHERE groupID IN (
            SELECT groupID FROM invGroups
            WHERE categoryID IN (7, 8, 16, 18)  -- Modules, Charges, Skills, Drones
        )
        AND published = 1
        LIMIT ?
        """

        cursor = self.conn.execute(query, (limit,))
        modules = []

        for row in cursor:
            modules.append({
                'typeID': row['typeID'],
                'typeName': row['typeName'],
                'description': row['description'] or '',
                'mass': row['mass'],
                'volume': row['volume']
            })

        logger.info(f"📦 {len(modules)} Module aus SDE geladen")
        return modules

    def format_ship_for_rag(self, ship: Dict) -> str:
        """Formats ship data for RAG."""
        text = f"""
SCHIFF: {ship['typeName']}
Typ-ID: {ship['typeID']}

{ship['description']}

TECHNISCHE DATEN:
- Masse: {ship['mass']:,.0f} kg
- Volumen: {ship['volume']:,.0f} m³
- Cargo: {ship['capacity']:,.0f} m³

Kategorie: EVE Online Raumschiff
Quelle: EVE SDE (Static Data Export)
"""
        return text.strip()

    def format_module_for_rag(self, module: Dict) -> str:
        """Formats module data for RAG."""
        text = f"""
ITEM: {module['typeName']}
Typ-ID: {module['typeID']}

{module['description']}

EIGENSCHAFTEN:
- Masse: {module['mass']:,.0f} kg
- Volumen: {module['volume']:,.0f} m³

Kategorie: EVE Online Item/Modul
Quelle: EVE SDE (Static Data Export)
"""
        return text.strip()

    def load_ships_to_chromadb(self, limit: int = 100) -> int:
        """Loads ships into ChromaDB."""
        ships = self.get_ship_types(limit)
        loaded = 0

        for ship in ships:
            doc_id = f"sde_ship_{ship['typeID']}"
            text = self.format_ship_for_rag(ship)

            metadata = {
                "source": "eve_sde",
                "type": "ship",
                "typeID": ship['typeID'],
                "typeName": ship['typeName']
            }

            if self.rag.add_document(doc_id, text, metadata):
                loaded += 1

        logger.info(f"✅ {loaded}/{len(ships)} Schiffe in ChromaDB geladen")
        return loaded

    def load_modules_to_chromadb(self, limit: int = 200) -> int:
        """Loads modules into ChromaDB."""
        modules = self.get_module_types(limit)
        loaded = 0

        for module in modules:
            doc_id = f"sde_module_{module['typeID']}"
            text = self.format_module_for_rag(module)

            metadata = {
                "source": "eve_sde",
                "type": "module",
                "typeID": module['typeID'],
                "typeName": module['typeName']
            }

            if self.rag.add_document(doc_id, text, metadata):
                loaded += 1

        logger.info(f"✅ {loaded}/{len(modules)} Module in ChromaDB geladen")
        return loaded

    def load_all(self, ships_limit: int = 100, modules_limit: int = 200):
        """Loads all SDE data into ChromaDB."""
        if not self.connect():
            logger.error("❌ Kann SDE DB nicht öffnen")
            return False

        logger.info("🚀 Starte SDE Import...")

        ships_loaded = self.load_ships_to_chromadb(ships_limit)
        modules_loaded = self.load_modules_to_chromadb(modules_limit)

        total = ships_loaded + modules_loaded
        logger.info(f"✅ SDE Import abgeschlossen: {total} Dokumente")

        self.conn.close()
        return True


if __name__ == "__main__":
    loader = SDELoader()

    print("=" * 60)
    print("EVE SDE LOADER")
    print("=" * 60)
    print()

    # Loads top 100 ships + top 200 modules
    success = loader.load_all(ships_limit=100, modules_limit=200)

    if success:
        print("\n✅ SDE Daten erfolgreich in ChromaDB geladen!")
        stats = loader.rag.get_stats()
        print(f"📊 Gesamt Dokumente: {stats.get('documents', 0)}")
    else:
        print("\n❌ SDE Import fehlgeschlagen")
        print("💡 Stelle sicher dass data/sde/sqlite-latest.sqlite existiert")
        print("   Download: https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2")
