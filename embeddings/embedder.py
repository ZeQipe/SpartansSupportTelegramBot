import numpy as np
from typing import List, Dict, Any, Optional
import json
import os
import openai
from openai import OpenAI
from config.settings import OPENAI_API_KEY, EMBEDDING_SETTINGS

client = OpenAI(api_key=OPENAI_API_KEY)

class Embedder:
    """Класс для создания эмбеддингов текста"""
    
    def __init__(self):
        self.model_name = EMBEDDING_SETTINGS['model_name']
        self.embedding_dim = EMBEDDING_SETTINGS['dimensions']
        
    def _create_embeddings(self, inputs):
        # If no key is provided, allow offline tests by returning zero vectors
        if not OPENAI_API_KEY:
            return [[0.0] * self.embedding_dim for _ in inputs]

        try:
            resp = client.embeddings.create(model=self.model_name, input=inputs)
            return [d.embedding for d in resp.data]
        except openai.NotFoundError:
            # Model not available for the account – fallback to ada-002
            fallback_model = "text-embedding-ada-002"
            resp = client.embeddings.create(model=fallback_model, input=inputs)
            return [d.embedding for d in resp.data]

    def embed_text(self, text: str) -> np.ndarray:
        """Создает эмбеддинг для одного текста"""
        return np.array(self._create_embeddings([text])[0])
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Создает эмбеддинги для списка текстов"""
        return np.array(self._create_embeddings(texts))
    
    def embed_chunks(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """Создает эмбеддинги для списка чанков"""
        # Извлекаем тексты из чанков
        texts = [chunk.content for chunk in chunks]
        
        # Создаем эмбеддинги
        embeddings = self.embed_texts(texts)
        
        # Формируем результат
        results = []
        for i, chunk in enumerate(chunks):
            # Добавляем language и document_type прямо в метаданные, чтобы Chroma могла фильтровать по ним
            enriched_meta = {**chunk.metadata, 'language': chunk.language, 'document_type': chunk.document_type}
            result = {
                'chunk_id': chunk.chunk_id,
                'content': chunk.content,
                'embedding': embeddings[i].tolist(),
                'metadata': enriched_meta,
                # Сохраняем дублирующие поля для удобства отладки, но основной фильтр будет работать по metadata
                'language': chunk.language,
                'document_type': chunk.document_type,
                'section': chunk.section
            }
            results.append(result)
        
        return results
    
    def save_embeddings(self, embeddings: List[Dict[str, Any]], file_path: str):
        """Сохраняет эмбеддинги в JSON файл"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings, f, ensure_ascii=False, indent=2)
    
    def load_embeddings(self, file_path: str) -> List[Dict[str, Any]]:
        """Загружает эмбеддинги из JSON файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_embedding_dimension(self) -> int:
        """Возвращает размерность эмбеддингов"""
        return self.embedding_dim
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Вычисляет косинусное сходство между двумя эмбеддингами"""
        return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
    
    def batch_similarity(self, query_embedding: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
        """Вычисляет сходство между запросом и списком эмбеддингов"""
        # Нормализуем эмбеддинги для косинусного сходства
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        return np.dot(embeddings_norm, query_norm)
