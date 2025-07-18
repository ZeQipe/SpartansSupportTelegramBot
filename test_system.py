#!/usr/bin/env python3
"""
Скрипт для тестирования компонентов TelSuppBot
"""

import os
import sys
import logging
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chunker():
    """Тестирует систему чанкинга"""
    logger.info("Testing LineChunker...")
    
    try:
        from embeddings.line_chunker import LineChunker
        
        chunker = LineChunker()
        logger.info("✓ LineChunker initialized successfully")
        
        # Тестируем на одном документе
        test_file = "data/en/terms.txt"
        if os.path.exists(test_file):
            chunks = chunker.process_document(test_file, "en")
            logger.info(f"✓ Created {len(chunks)} chunks from {test_file}")
            
            # Проверяем структуру чанков
            for i, chunk in enumerate(chunks[:3]):  # Первые 3 чанка
                logger.info(f"  Chunk {i+1}: {len(chunk.content)} chars, section: {chunk.section}")
        else:
            logger.warning(f"⚠ Test file {test_file} not found")
        
        return True
    except Exception as e:
        logger.error(f"✗ LineChunker test failed: {e}")
        return False

def test_embedder():
    """Тестирует систему эмбеддингов"""
    logger.info("Testing Embedder...")
    
    try:
        from embeddings.embedder import Embedder
        
        embedder = Embedder()
        logger.info("✓ Embedder initialized successfully")
        
        # Тестируем создание эмбеддинга
        test_text = "This is a test text for embedding generation."
        embedding = embedder.embed_text(test_text)
        logger.info(f"✓ Created embedding with dimension: {len(embedding)}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Embedder test failed: {e}")
        return False

def test_vector_store():
    """Тестирует векторное хранилище"""
    logger.info("Testing VectorStore...")
    
    try:
        from embeddings.vector_store import VectorStore
        from embeddings.embedder import Embedder
        
        embedder = Embedder()
        vector_store = VectorStore()
        logger.info("✓ VectorStore initialized successfully")
        
        # Тестируем поиск
        test_query = "minimum deposit"
        results = vector_store.search_by_text(test_query, embedder, top_k=3)
        logger.info(f"✓ Search returned {len(results)} results")
        
        return True
    except Exception as e:
        logger.error(f"✗ VectorStore test failed: {e}")
        return False

def test_search():
    """Тестирует систему поиска"""
    logger.info("Testing DocumentSearch...")
    
    try:
        from embeddings.search import DocumentSearch
        from embeddings.vector_store import VectorStore
        from embeddings.embedder import Embedder
        
        embedder = Embedder()
        vector_store = VectorStore()
        search = DocumentSearch(vector_store, embedder)
        logger.info("✓ DocumentSearch initialized successfully")
        
        # Тестируем поиск
        test_query = "bonus rules"
        results = search.search(test_query, language="en", top_k=3)
        logger.info(f"✓ Search returned {len(results)} results")
        
        return True
    except Exception as e:
        logger.error(f"✗ DocumentSearch test failed: {e}")
        return False

def test_deepseek_api():
    """Тестирует DeepSeek API"""
    logger.info("Testing DeepSeek API...")
    
    try:
        from llm.deepseek_api import DeepSeekAPI
        
        # Используем тестовый ключ
        api = DeepSeekAPI("test_key")
        logger.info("✓ DeepSeek API initialized successfully")
        
        # Тестируем подключение (без реального API ключа)
        logger.info("⚠ DeepSeek API connection test skipped (no real API key)")
        
        return True
    except Exception as e:
        logger.error(f"✗ DeepSeek API test failed: {e}")
        return False

def test_document_processing():
    """Тестирует полную обработку документов"""
    logger.info("Testing full document processing with LineChunker...")
    
    try:
        from embeddings.line_chunker import LineChunker
        from embeddings.embedder import Embedder
        from embeddings.vector_store import VectorStore
        
        # Инициализация компонентов
        chunker = LineChunker()
        embedder = Embedder()
        vector_store = VectorStore()
        
        # Обработка документов
        logger.info("Processing documents...")
        chunks = chunker.process_all_documents("data")
        logger.info(f"✓ Created {len(chunks)} chunks from all documents")
        
        if chunks:
            # Создание эмбеддингов
            logger.info("Creating embeddings...")
            embeddings_data = embedder.embed_chunks(chunks[:10])  # Первые 10 чанков для теста
            logger.info(f"✓ Created embeddings for {len(embeddings_data)} chunks")
            
            # Добавление в векторное хранилище
            vector_store.add_embeddings(embeddings_data)
            stats = vector_store.get_stats()
            logger.info(f"✓ Vector store contains {stats['total_embeddings']} embeddings")
            
            # Тестируем поиск
            test_query = "deposit"
            results = vector_store.search_by_text(test_query, embedder, top_k=3)
            logger.info(f"✓ Search returned {len(results)} results")
        
        # Create test doc
        test_dir = 'test_data'
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, 'test.txt'), 'w') as f: f.write('Test content')
        vector_store.load_documents(test_dir, chunker, embedder)
        results = vector_store.search_by_text('test', embedder, top_k=15)
        assert len(results) >=1 and results[0]['similarity'] >= 0.3
        
        return True
    except Exception as e:
        logger.error(f"✗ Document processing test failed: {e}")
        return False

def test_data_structure():
    """Проверяет структуру данных"""
    logger.info("Testing data structure...")
    
    required_files = [
        "data/en/terms.txt",
        "data/en/sportsbook_rules.txt",
        "data/en/bonus_rules.txt",
        "data/en/privacy_policy.txt",
        "data/en/aml_policy.txt",
        "data/en/promotions.txt",
        "data/ru/terms.txt",
        "data/ru/sportsbook_rules.txt",
        "data/ru/bonus_rules.txt",
        "data/ru/privacy_policy.txt",
        "data/ru/aml_policy.txt",
        "data/ru/promotions.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.warning(f"⚠ Missing files: {len(missing_files)}")
        for file_path in missing_files:
            logger.warning(f"  - {file_path}")
        return False
    else:
        logger.info("✓ All required data files found")
        return True

def main():
    """Основная функция тестирования"""
    logger.info("Starting TelSuppBot system tests...")
    
    tests = [
        ("Data Structure", test_data_structure),
        ("LineChunker", test_chunker),
        ("Embedder", test_embedder),
        ("VectorStore", test_vector_store),
        ("DocumentSearch", test_search),
        ("DeepSeek API", test_deepseek_api),
        ("Full Document Processing", test_document_processing)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Вывод результатов
    logger.info(f"\n{'='*50}")
    logger.info("TEST RESULTS:")
    logger.info("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status} - {test_name}")
        if success:
            passed += 1
    
    logger.info("="*50)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready to run.")
        return 0
    else:
        logger.warning("⚠ Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 