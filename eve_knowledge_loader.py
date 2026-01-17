"""
EVE knowledge loader.
Loads initial EVE Online data into ChromaDB.
"""

import os
import logging
import argparse
from typing import List, Dict
from rag_system import get_rag_system

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('KnowledgeLoader')


# ===== INITIAL KNOWLEDGE BASE =====
# This data is loaded on the first start
# TODO: Expand later with wiki scraper & SDE parser

INITIAL_DOCUMENTS = [
    # === SHIPS ===
    {
        'id': 'ship_astero',
        'text': '''Der Astero ist eine Sisters of EVE (SoE) Faction Exploration Frigate. 
        Er ist KEIN Tech 2 Schiff, sondern ein Faction Ship das Gallente und Amarr Technologie kombiniert. 
        Der Astero hat starke Bonusse für Scanning (+37.5% Scan Probe Strength pro Level Covert Ops) 
        und kann einen Covert Ops Cloaking Device nutzen. Er hat 3 High Slots, 4 Mid Slots, 4 Low Slots 
        und 50 Mbit/s Drohnen-Bandbreite (2 Light Drones + 3 Small Drones). Der Astero eignet sich 
        hervorragend für Exploration in Null-Sec und Wormholes, da er sowohl scannen als auch sich 
        verteidigen kann. Typische Fittings nutzen Sisters Core Scanner Probe Launcher, Covert Ops Cloak, 
        Combat Scanner Probes und Armor Tank mit Afterburner. Preis liegt bei ca. 40-60M ISK.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'ships',
            'type': 'frigate',
            'faction': 'sisters_of_eve',
            'title': 'Astero - SoE Faction Exploration Frigate'
        }
    },
    {
        'id': 'ship_stratios',
        'text': '''Der Stratios ist ein Sisters of EVE (SoE) Faction Cruiser, kein Tech 2 Schiff. 
        Als großer Bruder des Astero kombiniert er Gallente und Amarr Technologie. Der Stratios hat 
        5 High Slots, 6 Mid Slots, 6 Low Slots und 125 Mbit/s Drohnen-Bandbreite (5 Medium Drones 
        oder 5 Light + 5 Small). Er kann einen Covert Ops Cloak nutzen und hat starke Scan-Bonusse 
        (+37.5% Scan Probe Strength). Der Stratios ist sehr beliebt für Solo PvP in Wormholes und 
        kann sowohl als Kampfschiff als auch als Exploration-Schiff eingesetzt werden. Typische 
        Fittings kombinieren Armor Tank mit Medium Drones, Covert Ops Cloak und Afterburner/MWD. 
        Preis liegt bei ca. 200-300M ISK. Beliebtes Solo PvP Schiff wegen hoher Drohnen-DPS und 
        Tank-Kapazität.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'ships',
            'type': 'cruiser',
            'faction': 'sisters_of_eve',
            'title': 'Stratios - SoE Faction Cruiser'
        }
    },
    {
        'id': 'ship_gnosis',
        'text': '''Der Gnosis ist ein Sisters of EVE Faction Battlecruiser, der zum 10. Geburtstag 
        von EVE Online an alle Spieler verteilt wurde. Er ist KEIN normaler Battlecruiser sondern 
        ein spezielles Faction Ship. Der Gnosis hat 7 High Slots, 6 Mid Slots, 6 Low Slots und 
        125 Mbit/s Drohnen-Bandbreite (5 Medium Drones oder Mix). Besonderheit: Der Gnosis hat 
        Bonusse für ALLE Waffensysteme (Lasers, Hybrids, Projectiles) UND alle Drohnen-Typen, 
        was ihn extrem vielseitig macht. Er kann sowohl Shield als auch Armor getankt werden. 
        Der Gnosis eignet sich gut für PvE Content, Level 3/4 Missionen, und als Training-Schiff 
        für neue Spieler. Alle Charaktere die vor 2013 erstellt wurden, haben einen kostenlosen 
        Gnosis im Hangar. Preis liegt bei ca. 80-120M ISK wenn man ihn kaufen muss.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'ships',
            'type': 'battlecruiser',
            'faction': 'sisters_of_eve',
            'title': 'Gnosis - SoE Faction Battlecruiser'
        }
    },
    
    # === WORMHOLES ===
    {
        'id': 'wh_basics',
        'text': '''Wormholes sind temporäre Verbindungen zwischen verschiedenen Solarsystemen in EVE Online. 
        Sie werden in Klassen von C1 bis C6 eingeteilt, wobei höhere Klassen schwierigere NPCs und bessere 
        Belohnungen bieten. Jedes Wormhole hat eine maximale Masse und Lebensdauer. Die Masse bestimmt, 
        welche Schiffe durchfliegen können. Wormholes haben keine Local Chat-Funktion, was sie gefährlicher 
        macht. Sie sind beliebt für PvE (Site-Running), Gas-Harvesting, Ore-Mining und PvP. Wormhole-Klassen: 
        C1-C3 für Anfänger, C4-C5 für fortgeschrittene Spieler, C6 für erfahrene Corps.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'wormholes',
            'type': 'basics',
            'title': 'Wormhole Basics'
        }
    },
    {
        'id': 'wh_classes',
        'text': '''Wormhole-Klassen in EVE Online: C1 Wormholes haben die schwächsten NPCs und niedrigste 
        Belohnungen, geeignet für Frigates und Cruiser. C2 Wormholes haben mittlere Schwierigkeit. 
        C3 Wormholes benötigen Battlecruiser oder Battleships. C4 Wormholes haben Wolf-Rayet, Pulsar und 
        andere Effekte die Schiffe beeinflussen. C5 und C6 Wormholes haben die härtesten NPCs (Sleeper) 
        und besten Belohnungen, benötigen aber Capital Ships oder gut koordinierte Fleets. Jede Klasse 
        hat spezifische Static Connections zu anderen Wormhole-Klassen oder K-Space.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'wormholes',
            'type': 'classes',
            'title': 'Wormhole Klassen C1-C6'
        }
    },
    {
        'id': 'wh_effects',
        'text': '''Wormhole System-Effekte beeinflussen alle Schiffe im System: Wolf-Rayet (+Signatur, 
        -Shield, +Armor), Pulsar (+Shield, +Signatur, -Armor, -Capacitor), Cataclysmic Variable 
        (+Shield Boost, +Armor Rep, +Cap Recharge, -Cap Amount), Black Hole (+Missile Velocity, 
        +Speed, -Targeting, -Sig Radius), Magnetar (+Damage, +Explosion Radius/Velocity, -Targeting, 
        -Tracking), Red Giant (+Overheat Bonus, +Heat Damage). Diese Effekte sind wichtig für Fitting 
        und Taktik. Manche Effekte sind stark für PvP, andere für PvE.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'wormholes',
            'type': 'effects',
            'title': 'Wormhole System-Effekte'
        }
    },
    
    # === FITTING ===
    {
        'id': 'fitting_tank_types',
        'text': '''Es gibt drei Haupt-Tank-Typen in EVE Online: Shield Tank nutzt Shield Modules in 
        Mid Slots (Shield Extender, Shield Hardener, Shield Booster). Shield-Ships sind meist Caldari 
        und Minmatar. Armor Tank nutzt Armor Modules in Low Slots (Armor Plates, Armor Hardener, 
        Armor Repairer). Armor-Ships sind meist Gallente und Amarr. Hull Tank ist selten und nutzt 
        Hull-Module. Active Tank regeneriert HP aktiv (Booster/Repairer), Passive Tank hat viel Buffer 
        (Extender/Plates). Für PvP ist meist Buffer-Tank besser, für PvE oft Active Tank.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'fitting',
            'type': 'tank',
            'title': 'Tank Types - Shield vs Armor'
        }
    },
    {
        'id': 'fitting_dps',
        'text': '''DPS (Damage per Second) in EVE Online kommt von Turrets, Missiles oder Drones. 
        Turrets: Lasers (Amarr, beste Tracking), Hybrids (Gallente, mittlere Range), Projectiles 
        (Minmatar, keine Cap-Nutzung). Missiles: Rockets (kurz), Light/Heavy Missiles (mittel), 
        Torpedos (lange Range). Drones: Light (Frigates), Medium (Cruisers), Heavy/Sentry (Battleships). 
        Wichtige DPS-Faktoren: Tracking für Turrets, Application für Missiles, Bandbreite für Drones. 
        Optimal Range und Falloff beachten für maximalen DPS.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'fitting',
            'type': 'dps',
            'title': 'DPS - Damage Systems'
        }
    },
    
    # === PVP ===
    {
        'id': 'pvp_solo',
        'text': '''Solo PvP in EVE Online erfordert gute Kenntnisse von Schiffs-Countern und Situational 
        Awareness. Wichtige Aspekte: Schiffswahl (meist Frigates/Cruiser für Solo), Fitting mit Tank 
        und DPS, Overheat-Management, Transversal Velocity für Tracking, Range Control (Dictate Range). 
        Beliebte Solo-PvP Schiffe: Astero, Stratios, Svipul, Jackdaw, Garmur, Orthrus. Wichtig ist, 
        Fights zu wählen die man gewinnen kann - kenne dein Schiff und den Gegner. D-Scan ist essentiell.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'pvp',
            'type': 'solo',
            'title': 'Solo PvP Grundlagen'
        }
    },
    {
        'id': 'pvp_fleet',
        'text': '''Fleet PvP in EVE Online ist koordiniertes Kämpfen in Gruppen. Wichtige Rollen: 
        Fleet Commander (FC) leitet, Logi-Ships heilen, DPS-Ships machen Schaden, Tackle-Ships halten 
        Gegner fest, Scouts erkunden. Fleet-Comps: Alpha-Strike (hoher Burst-Damage), Brawl (Close-Range), 
        Kiting (Long-Range), Logi-Wing (Healer-Support). Wichtig: Voice Comms (Mumble/Discord), 
        Broadcasts nutzen, FC-Befehle befolgen, Target Calling. Anchor auf FC für Formation. 
        Beliebte Fleet-Doctrines: Muninn, Eagle, Cerberus, Jackdaw, Ferox.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'pvp',
            'type': 'fleet',
            'title': 'Fleet PvP Grundlagen'
        }
    },
    
    # === MARKET ===
    {
        'id': 'market_hubs',
        'text': '''Die wichtigsten Trade Hubs in EVE Online: Jita (The Forge) ist der größte Hub mit 
        den meisten Transaktionen und besten Preisen. Amarr ist der zweitgrößte Hub (Amarr Region). 
        Dodixie (Gallente Space), Rens (Minmatar Space) und Hek sind weitere wichtige Hubs. 
        Für Null-Sec/Wormholes sind lokale Staging-Systeme wichtig. Preise variieren zwischen Hubs - 
        Jita hat meist die besten Preise. Für Verkauf sind hohe Volume-Hubs besser, für Kauf kann 
        man in kleineren Hubs Schnäppchen finden.''',
        'metadata': {
            'source': 'eve_knowledge_base',
            'category': 'market',
            'type': 'hubs',
            'title': 'Trade Hubs in New Eden'
        }
    },
]


def load_initial_knowledge(force: bool = False) -> bool:
    """Loads the initial knowledge base."""
    logger.info("Lade initiale EVE Online Knowledge Base...")
    
    rag = get_rag_system()
    
    # Check if data already exists
    stats = rag.get_stats()
    if stats.get('documents', 0) > 0 and not force:
        logger.info(f"Knowledge Base hat bereits {stats['documents']} Dokumente")
        logger.info("Nutze --force um neu zu laden")
        return True
    
    # Add documents
    success = rag.add_documents(INITIAL_DOCUMENTS)
    
    if success:
        logger.info(f"✅ {len(INITIAL_DOCUMENTS)} Dokumente erfolgreich geladen")
        stats = rag.get_stats()
        logger.info(f"Knowledge Base Status: {stats}")
        return True
    else:
        logger.error("❌ Fehler beim Laden der Dokumente")
        return False


def add_custom_document(text: str, doc_id: str, category: str, title: str):
    """Adds a custom document to the knowledge base."""
    rag = get_rag_system()
    
    doc = {
        'id': doc_id,
        'text': text,
        'metadata': {
            'source': 'custom',
            'category': category,
            'title': title
        }
    }
    
    success = rag.add_documents([doc])
    if success:
        logger.info(f"✅ Custom Dokument '{title}' hinzugefügt")
    else:
        logger.error(f"❌ Fehler beim Hinzufügen von '{title}'")


def main():
    parser = argparse.ArgumentParser(description='EVE Knowledge Loader')
    parser.add_argument('--init', action='store_true', help='Initiale Knowledge Base laden')
    parser.add_argument('--force', action='store_true', help='Force reload auch wenn Daten vorhanden')
    parser.add_argument('--stats', action='store_true', help='Zeige Knowledge Base Stats')
    
    args = parser.parse_args()
    
    if args.stats:
        rag = get_rag_system()
        stats = rag.get_stats()
        print("\n=== Knowledge Base Stats ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
        print()
        return
    
    if args.init:
        load_initial_knowledge(force=args.force)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
