"""
RAG System für EVE Online Knowledge Base
"""
import os
import logging
import requests
import time
from typing import List, Dict

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

logger = logging.getLogger("RAG")

class EVERAGSystem:
    def __init__(self):
        self.chromadb_host = os.getenv("CHROMADB_HOST", "localhost")
        self.chromadb_port = int(os.getenv("CHROMADB_PORT", "8000"))
        self.collection_name = "eve_knowledge"
        self.ollama_base = os.getenv("OLLAMA_BASE", "http://localhost:11434")
        self.ollama_embed_url = f"{self.ollama_base}/api/embeddings"
        self.embedding_model = "nomic-embed-text"
        self.top_k = 3
        self.min_score = 0.6
        
        self.client = None
        self.collection = None

        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB package nicht installiert")
            return

        # Retry-Logik für ChromaDB Connection
        max_retries = 5
        retry_delay = 2  # Sekunden

        for attempt in range(max_retries):
            try:
                logger.info(f"ChromaDB Verbindungsversuch {attempt + 1}/{max_retries}...")

                self.client = chromadb.HttpClient(
                    host=self.chromadb_host,
                    port=self.chromadb_port
                )

                # Test connection
                self.client.heartbeat()
                logger.info(f"✅ ChromaDB verbunden: {self.chromadb_host}:{self.chromadb_port}")

                # Collection erstellen oder laden
                try:
                    self.collection = self.client.get_collection(name=self.collection_name)
                    count = self.collection.count()
                    logger.info(f"✅ Collection '{self.collection_name}' geladen: {count} Dokumente")
                except ValueError:
                    # Collection existiert nicht, erstelle sie
                    logger.info(f"Collection '{self.collection_name}' existiert nicht, erstelle neu...")
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        metadata={"description": "EVE Online Knowledge Base"}
                    )
                    logger.info(f"✅ Collection '{self.collection_name}' erstellt (leer)")

                # Erfolgreich verbunden
                break

            except Exception as e:
                logger.warning(f"Verbindungsversuch {attempt + 1} fehlgeschlagen: {e}")

                if attempt < max_retries - 1:
                    logger.info(f"Warte {retry_delay} Sekunden vor erneutem Versuch...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"❌ ChromaDB nicht erreichbar nach {max_retries} Versuchen")
                    self.client = None
                    self.collection = None
    
    def get_embedding(self, text: str):
        try:
            response = requests.post(
                self.ollama_embed_url,
                json={"model": self.embedding_model, "prompt": text},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("embedding")
            return None
        except:
            return None
    
    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        if not self.client or not self.collection:
            return False
        
        try:
            embedding = self.get_embedding(text)
            if not embedding:
                return False
            
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}]
            )
            logger.info(f"✅ Dokument '{doc_id}' hinzugefügt")
            return True
        except Exception as e:
            logger.error(f"Fehler: {e}")
            return False
    
    def search_knowledge(self, query: str) -> List[Dict]:
        if not self.client or not self.collection:
            return []
        
        try:
            count = self.collection.count()
            if count == 0:
                return []
            
            embedding = self.get_embedding(query)
            if not embedding:
                return []
            
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=min(self.top_k, count),
                include=["documents", "metadatas", "distances"]
            )
            
            if not results or not results["documents"] or not results["documents"][0]:
                return []
            
            docs = []
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                score = 1.0 - distance
                
                if score >= self.min_score:
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    docs.append({
                        "content": doc,
                        "score": score,
                        "metadata": metadata
                    })
            
            return docs
        except:
            return []
    
    def get_stats(self) -> Dict:
        if not self.client or not self.collection:
            return {"status": "disconnected", "message": "Bot läuft ohne RAG System"}

        try:
            count = self.collection.count()
            return {
                "status": "connected",
                "host": f"{self.chromadb_host}:{self.chromadb_port}",
                "collection": self.collection_name,
                "documents": count,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def reconnect(self) -> bool:
        """Versucht ChromaDB neu zu verbinden"""
        logger.info("Manueller Reconnect zu ChromaDB gestartet...")
        self.__init__()  # Re-initialize
        return self.client is not None and self.collection is not None

_rag_instance = None

def get_rag_system() -> EVERAGSystem:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = EVERAGSystem()
    return _rag_instance
