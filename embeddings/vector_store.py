import numpy as np
from typing import List, Dict, Any, Optional
import os
import chromadb
from config.settings import CHROMADB_SETTINGS, SEARCH_SETTINGS

class VectorStore:
    """Работа с ChromaDB"""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMADB_SETTINGS['persist_directory'])
        self.collection = self.client.get_or_create_collection(
            name=CHROMADB_SETTINGS['collection_name'],
            metadata={'hnsw:space': 'cosine'}
        )

    # --- Индексация -------------------------------------------------------------------------
    def add_embeddings(self, embeddings_data: List[Dict[str, Any]]):
        ids        = [d['chunk_id']     for d in embeddings_data]
        embeddings = [d['embedding']    for d in embeddings_data]
        metadatas  = [d['metadata']     for d in embeddings_data]
        documents  = [d['content']      for d in embeddings_data]
        self.collection.upsert(ids=ids, embeddings=embeddings,
                                metadatas=metadatas, documents=documents)

    def load_documents(self, data_dir: str, chunker, embedder) -> Dict[str, int]:
        """Индексирует документы в указанной папке и выводит статистику."""
        added = updated = skipped = 0
        for lang in ['en', 'ru']:
            lang_dir = os.path.join(data_dir, lang)
            if not os.path.isdir(lang_dir):
                continue
            for filename in os.listdir(lang_dir):
                if not filename.endswith('.txt'):
                    continue
                file_path = os.path.join(lang_dir, filename)
                mtime = os.path.getmtime(file_path)

                existing = self.collection.get(where={'path': file_path}) or {}
                ids_found = existing.get('ids', [])
                if ids_found:
                    meta_list = existing.get('metadatas', [])
                    prev_mtime = meta_list[0].get('mtime') if meta_list else None
                    if prev_mtime == mtime:
                        skipped += 1
                        continue
                    # обновляем существующие записи
                    self.collection.delete(ids=ids_found)
                    updated += 1
                else:
                    added += 1

                chunks = chunker.process_document(file_path, lang)
                for c in chunks:
                    c.metadata['mtime'] = mtime
                self.add_embeddings(embedder.embed_chunks(chunks))
        return {'added': added, 'updated': updated, 'skipped': skipped}

    # --- Поиск ------------------------------------------------------------------------------
    def _format_filters(self, language: Optional[str], doc_type: Optional[str]):
        if not language and not doc_type:
            return None
        and_filters = []
        if language:
            and_filters.append({'language': language})
        if doc_type:
            and_filters.append({'document_type': doc_type})
        return {'$and': and_filters}

    def search(self, query_embedding: np.ndarray, *, top_k: int = SEARCH_SETTINGS['default_top_k'],
               language: Optional[str] = None, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        where = self._format_filters(language, document_type)
        res = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where or {}  # type: ignore
        )
        threshold = SEARCH_SETTINGS['similarity_threshold']

        results = []
        # Если ChromaDB вернул None (например, при отсутствии результатов), подставляем пустой список
        documents = (res.get('documents') or [[]])[0]
        metadatas = (res.get('metadatas') or [[]])[0]
        distances = (res.get('distances') or [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            if doc is None: continue  # Skip empty
            similarity = 1 - dist
            if similarity < threshold: continue
            results.append({'content': doc, 'metadata': meta or {}, 'similarity': similarity})
        return results

    def search_by_text(self, query_text: str, embedder, **kwargs):
        emb = embedder.embed_text(query_text)
        return self.search(emb, **kwargs)

    # --- Статистика -------------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        return {'total_embeddings': self.collection.count()}
