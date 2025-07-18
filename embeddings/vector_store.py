import numpy as np
from typing import List, Dict, Any, Optional
import os
import logging
import chromadb
from config.settings import CHROMADB_SETTINGS, SEARCH_SETTINGS

# logger for this module
logger = logging.getLogger(__name__)

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

    def load_documents(self, data_dir: str, chunker, embedder) -> Dict[str, Any]:
        """Индексирует документы в указанной папке и выводит статистику."""
        added = updated = skipped = 0  # счётчики файлов
        total_chunks_added = 0  # количество записей (векторов), которые были упакованы в коллекцию
        files_info: List[Dict[str, Any]] = []  # подробная информация по каждому файлу
        for lang in ['en', 'ru']:
            lang_dir = os.path.join(data_dir, lang)
            if not os.path.isdir(lang_dir):
                continue
            for filename in os.listdir(lang_dir):
                if not filename.endswith('.txt'):
                    continue
                # Файлы с акциями (promotions) не индексируются, идут прямо в системные инструкции
                if 'promotions' in filename.lower():
                    skipped += 1
                    files_info.append({'path': os.path.join(lang_dir, filename), 'status': 'skipped', 'chunks': 0})
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
                        files_info.append({
                            'path': file_path,
                            'status': 'skipped',
                            'chunks': 0
                        })
                        continue
                    # обновляем существующие записи
                    self.collection.delete(ids=ids_found)
                    updated += 1
                    status = 'updated'
                else:
                    added += 1
                    status = 'added'

                # Генерируем чанки и добавляем
                chunks = chunker.process_document(file_path, lang)
                for c in chunks:
                    c.metadata['mtime'] = mtime
                self.add_embeddings(embedder.embed_chunks(chunks))

                total_chunks_added += len(chunks)
                files_info.append({
                    'path': file_path,
                    'status': status,
                    'chunks': len(chunks)
                })

        return {
            'added': added,
            'updated': updated,
            'skipped': skipped,
            'chunks_added': total_chunks_added,
            'files': files_info,
        }

    # --- Поиск ------------------------------------------------------------------------------
    def _format_filters(self, language: Optional[str], doc_type: Optional[str]):
        """Формирует where-фильтр для ChromaDB.

        1. Если задан только один из параметров, возвращаем простой словарь вида
           {"language": "en"} или {"document_type": "terms"}.
        2. Если заданы оба – объединяем их при помощи $and, как того требует API.
        3. Если ни один не задан – возвращаем None.
        """
        if language and doc_type:
            return {'$and': [{'language': language}, {'document_type': doc_type}]}
        if language:
            return {'language': language}
        if doc_type:
            return {'document_type': doc_type}
        return None

    def search(self, query_embedding: np.ndarray, *, top_k: int = SEARCH_SETTINGS['default_top_k'],
               language: Optional[str] = None, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        where = self._format_filters(language, document_type)
        res = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where or {}  # type: ignore
        )
        threshold = SEARCH_SETTINGS['similarity_threshold']

        # --- Debug logging --------------------------------------------------
        logger.debug("VectorStore.search: top_k=%s, language=%s, doc_type=%s, threshold=%.2f", top_k, language, document_type, threshold)

        results = []
        # Если ChromaDB вернул None (например, при отсутствии результатов), подставляем пустой список
        documents = (res.get('documents') or [[]])[0]
        metadatas = (res.get('metadatas') or [[]])[0]
        distances = (res.get('distances') or [[]])[0]

        for idx, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            if doc is None: continue  # Skip empty
            similarity = 1 - dist
            if similarity < threshold: continue
            results.append({'content': doc, 'metadata': meta or {}, 'similarity': similarity})
            logger.debug("  #%d sim=%.3f section=%s preview=%s", idx+1, similarity, (meta or {}).get('section', '-'), doc[:100].replace('\n',' '))

        logger.debug("VectorStore.search: returned %d chunks after filtering", len(results))
        return results

    def search_by_text(self, query_text: str, embedder, **kwargs):
        emb = embedder.embed_text(query_text)
        return self.search(emb, **kwargs)

    # --- Статистика -------------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        return {'total_embeddings': self.collection.count()}
