import re
from typing import List, Dict, Any
from dataclasses import dataclass
import os
import tiktoken
from config.settings import CHUNK_SETTINGS

@dataclass
class Chunk:
    """Представляет один чанк документа"""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    language: str
    document_type: str
    section: str = ""

class DocumentChunker:
    """Класс для разбиения документов на семантически связанные чанки"""
    
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding('cl100k_base')
        self.chunk_size = CHUNK_SETTINGS['chunk_size']
        self.overlap = CHUNK_SETTINGS['overlap']
        
    def split_by_sections(self, text: str, language: str = "en", doc_id: str = "", file_path: str = "") -> List[Chunk]:
        """Разбивает документ по секциям и создает чанки"""
        chunks = []
        
        # Разбиваем на секции по заголовкам
        sections = self._extract_sections(text)
        
        for section_title, section_content in sections:
            # Разбиваем секцию на чанки
            section_chunks = self._split_section(section_content, section_title)
            
            for i, chunk_content in enumerate(section_chunks):
                chunk = Chunk(
                    content=chunk_content,
                    metadata={
                        "section": section_title,
                        "chunk_index": i,
                        "total_chunks_in_section": len(section_chunks),
                        'doc_id': doc_id,
                        'category': self._detect_document_type(text),
                        'sport': section_title if 'sport' in section_title.lower() else '',  # Simple extraction
                        'path': file_path
                    },
                    chunk_id=f"{doc_id}_{section_title}_{i}",
                    language=language,
                    document_type=self._detect_document_type(text),
                    section=section_title
                )
                chunks.append(chunk)
        
        return chunks
    
    def _extract_sections(self, text: str) -> List[tuple]:
        """Извлекает секции из текста по заголовкам"""
        # Паттерны для заголовков (разные форматы)
        patterns = [
            r'^(\d+\.\s+[A-Z][^.\n]+)',  # 1. Section Title
            r'^(\d+\.\d+\s+[A-Z][^.\n]+)',  # 1.1 Subsection Title
            r'^([A-Z][A-Z\s]+)$',  # ALL CAPS TITLE
            r'^([A-Z][a-z\s]+:)$',  # Title:
        ]
        
        lines = text.split('\n')
        sections = []
        current_section = "Introduction"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Проверяем, является ли строка заголовком
            is_header = False
            for pattern in patterns:
                if re.match(pattern, line):
                    # Сохраняем предыдущую секцию
                    if current_content:
                        sections.append((current_section, '\n'.join(current_content)))
                    
                    current_section = line
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Добавляем последнюю секцию
        if current_content:
            sections.append((current_section, '\n'.join(current_content)))
        
        return sections
    
    def _split_section(self, content: str, section_title: str) -> List[str]:
        """Разбивает секцию на чанки по размеру"""
        tokens = self.tokenizer.encode(content)
        if len(tokens) <= self.chunk_size:
            return [self.tokenizer.decode(tokens)]
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(self.tokenizer.decode(chunk_tokens))
            start = end - self.overlap
        
        return chunks
    
    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """Находит хорошую точку для разрыва чанка"""
        # Ищем конец предложения в пределах overlap
        overlap_zone = text[end-self.overlap:end]
        
        # Приоритет: конец абзаца, затем конец предложения
        for i in range(len(overlap_zone) - 1, -1, -1):
            if overlap_zone[i] in ['\n\n', '\n']:
                return end - len(overlap_zone) + i + 1
        
        for i in range(len(overlap_zone) - 1, -1, -1):
            if overlap_zone[i] in ['.', '!', '?']:
                return end - len(overlap_zone) + i + 1
        
        return end
    
    def _detect_document_type(self, text: str) -> str:
        """Определяет тип документа по содержимому"""
        text_lower = text.lower()
        
        if 'sportsbook' in text_lower or 'betting' in text_lower:
            return 'sportsbook_rules'
        elif 'bonus' in text_lower or 'promotion' in text_lower:
            return 'bonus_rules'
        elif 'privacy' in text_lower or 'data' in text_lower:
            return 'privacy_policy'
        elif 'aml' in text_lower or 'money laundering' in text_lower:
            return 'aml_policy'
        elif 'terms' in text_lower or 'conditions' in text_lower:
            return 'terms'
        elif 'promotion' in text_lower:
            return 'promotions'
        else:
            return 'general'
    
    def process_document(self, file_path: str, language: str = "en") -> List[Chunk]:
        """Обрабатывает документ из файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(file_path)
        doc_id = os.path.splitext(filename)[0]

        return self.split_by_sections(content, language, doc_id, file_path)
    
    def process_all_documents(self, data_dir: str) -> List[Chunk]:
        """Обрабатывает все документы в директории"""
        all_chunks = []
        
        for lang in ['en', 'ru']:
            lang_dir = os.path.join(data_dir, lang)
            if not os.path.exists(lang_dir):
                continue
            
            for filename in os.listdir(lang_dir):
                if filename.endswith('.txt'):
                    if 'promotions' in filename:
                        continue
                    file_path = os.path.join(lang_dir, filename)
                    chunks = self.process_document(file_path, lang)
                    all_chunks.extend(chunks)
        
        return all_chunks
