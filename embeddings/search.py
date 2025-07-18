from typing import List, Dict, Any, Optional
import logging
from .vector_store import VectorStore
from .embedder import Embedder
import json
from config.settings import SEARCH_SETTINGS
from embeddings.preprocess_deepseek import split_text as split_deepseek
from embeddings.preprocess_simple import split_text as split_simple

# set up module logger
logger = logging.getLogger(__name__)

class DocumentSearch:
    """Система поиска по документам"""
    
    def __init__(self, vector_store: VectorStore, embedder: Embedder):
        self.vector_store = vector_store
        self.embedder = embedder
    
    def preprocess_query(self, query: str, language: str) -> str:
        if SEARCH_SETTINGS.get('preprocess_type', 'simple') == 'deepseek':
            return split_deepseek(query, language)
        else:
            return split_simple(query, language)
    
    def search(self, query: str, language: Optional[str] = None, 
               document_type: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск по запросу
        
        Args:
            query: Текстовый запрос
            language: Фильтр по языку ('en', 'ru')
            document_type: Фильтр по типу документа
            top_k: Количество результатов
            
        Returns:
            Список найденных документов с метаданными
        """
        processed_query = self.preprocess_query(query, language or 'en')
        query_embedding = self.embedder.embed_text(processed_query)
        results = self.vector_store.search(
            query_embedding,
            top_k=top_k,
            language=language,
            document_type=document_type,
        )

        # --- Console output of top chunks ---------------------------------
        if results:
            logger.info("Found %d chunks for query '%s' (lang=%s):", len(results), query, language)
            for i, r in enumerate(results[:min(top_k, 15)], 1):
                section = r.get('metadata', {}).get('section', '-')
                preview = r.get('content', '')[:120].replace('\n', ' ')
                sim = r.get('similarity', 0)
                logger.info("  %2d. [%s] %.3f %s", i, section, sim, preview)

        return results
    
    def search_multilingual(self, query: str, top_k: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Поиск на обоих языках
        
        Args:
            query: Текстовый запрос
            top_k: Количество результатов на язык
            
        Returns:
            Словарь с результатами по языкам
        """
        results = {}
        
        # Поиск на английском
        en_results = self.search(query, language='en', top_k=top_k)
        if en_results:
            results['en'] = en_results
        
        # Поиск на русском
        ru_results = self.search(query, language='ru', top_k=top_k)
        if ru_results:
            results['ru'] = ru_results
        
        return results
    
    def search_by_document_type(self, query: str, document_type: str, 
                               language: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск в конкретном типе документов
        
        Args:
            query: Текстовый запрос
            document_type: Тип документа для поиска
            language: Фильтр по языку
            top_k: Количество результатов
            
        Returns:
            Список найденных документов
        """
        return self.search(query, language, document_type, top_k)
    
    def get_context_for_llm(self, query: str, language: str = 'en', 
                           document_type: Optional[str] = None, top_k: int = 3) -> str:
        """
        Получает контекст для LLM на основе поиска
        
        Args:
            query: Запрос пользователя
            language: Язык для поиска
            document_type: Тип документа для фильтрации
            top_k: Количество чанков для контекста
            
        Returns:
            Форматированный контекст для LLM
        """
        results = self.search(query, language, document_type, top_k)
        
        if not results:
            return "Не найдено релевантной информации в документах."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            section = result.get('metadata', {}).get('section') or result.get('section', '-')
            content = result.get('content', '')
            context_parts.append(f"Источник {i} (раздел: {section}):\n{content}\n")
        
        return "\n".join(context_parts)
    
    def get_multilingual_context(self, query: str, top_k: int = 2) -> Dict[str, str]:
        """
        Получает контекст на обоих языках
        
        Args:
            query: Запрос пользователя
            top_k: Количество чанков на язык
            
        Returns:
            Словарь с контекстом по языкам
        """
        contexts = {}
        
        # Контекст на английском
        en_context = self.get_context_for_llm(query, 'en', top_k=top_k)
        if en_context != "Не найдено релевантной информации в документах.":
            contexts['en'] = en_context
        
        # Контекст на русском
        ru_context = self.get_context_for_llm(query, 'ru', top_k=top_k)
        if ru_context != "Не найдено релевантной информации в документах.":
            contexts['ru'] = ru_context
        
        return contexts
    
    def search_similar_sections(self, section_name: str, language: str = 'en', 
                               top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск похожих секций по названию
        
        Args:
            section_name: Название секции
            language: Язык для поиска
            top_k: Количество результатов
            
        Returns:
            Список похожих секций
        """
        return self.search(section_name, language, top_k=top_k)
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Возвращает статистику документов"""
        return self.vector_store.get_stats()
