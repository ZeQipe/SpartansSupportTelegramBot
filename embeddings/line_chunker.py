"""
Новая версия алгоритма разбиения (chunking), формирующая один вектор на одну строку.
Если строка превышает лимит токенов, она дополнительно режется на сегменты фиксированной длины с перекрытием.
Старый embeddings.chunker.DocumentChunker остаётся без изменений — при необходимости код может
перейти на LineChunker, сохранив прежний интерфейс (process_document / process_all_documents).
"""

# --------------- imports ------------------
from __future__ import annotations

import os
from typing import List, Dict, Any

import tiktoken

from config.settings import CHUNK_SETTINGS
from embeddings.chunker import Chunk  # переиспользуем общий dataclass


class LineChunker:
    """Разбивает документы построчно. 1 строка → 1 вектор.

    Длинные строки (> chunk_size токенов) нарезаются на сегменты фиксированной длины
    с перекрытием (overlap). Интерфейс аналогичен DocumentChunker, поэтому остальные
    компоненты (Embedder, VectorStore) можно использовать без изменений.
    """

    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.chunk_size: int = CHUNK_SETTINGS["chunk_size"]
        self.overlap: int = CHUNK_SETTINGS["overlap"]

    # ---------------------------------------------------------------------
    # Основные публичные методы
    # ---------------------------------------------------------------------
    def process_document(self, file_path: str, language: str = "en") -> List[Chunk]:
        """Читает файл и формирует список чанков (по строкам)."""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        filename = os.path.basename(file_path)
        doc_id = os.path.splitext(filename)[0]

        chunks: List[Chunk] = []
        for line_number, raw_line in enumerate(lines, 1):
            # Убираем лишние пробелы / переводы строк
            line = raw_line.strip()
            if not line:
                continue  # пропускаем пустые строки

            # Токенизируем строку и режем при необходимости
            tokens = self.tokenizer.encode(line)
            token_segments = self._split_tokens(tokens)
            total_segments = len(token_segments)

            for seg_index, seg_tokens in enumerate(token_segments):
                content = self.tokenizer.decode(seg_tokens)
                chunk_id = f"{doc_id}_L{line_number}_S{seg_index}"
                chunk_meta = {
                    "line_number": line_number,
                    "segment_index": seg_index,
                    "total_segments_in_line": total_segments,
                    "doc_id": doc_id,
                    "path": file_path,
                }

                chunk = Chunk(
                    content=content,
                    metadata=chunk_meta,
                    chunk_id=chunk_id,
                    language=language,
                    document_type=self._detect_document_type(content),
                    section=f"Line {line_number}",  # поле section оставим для совместимости
                )
                chunks.append(chunk)

        return chunks

    def process_all_documents(self, data_dir: str) -> List[Chunk]:
        """Обрабатывает все языковые поддиректории аналогично старому Chunker."""
        all_chunks: List[Chunk] = []
        for lang in ["en", "ru"]:
            lang_dir = os.path.join(data_dir, lang)
            if not os.path.isdir(lang_dir):
                continue
            for filename in os.listdir(lang_dir):
                if not filename.endswith(".txt"):
                    continue
                if "promotions" in filename:
                    # Эти файлы не индексируем — логика сохранена из DocumentChunker
                    continue
                file_path = os.path.join(lang_dir, filename)
                all_chunks.extend(self.process_document(file_path, lang))
        return all_chunks

    # ---------------------------------------------------------------------
    # Внутренние методы
    # ---------------------------------------------------------------------
    def _split_tokens(self, tokens: List[int]) -> List[List[int]]:
        """Нарезает список токенов на сегменты с заданным перекрытием."""
        if len(tokens) <= self.chunk_size:
            return [tokens]

        segments: List[List[int]] = []
        start = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            segments.append(tokens[start:end])
            # переходим к следующему сегменту с учётом overlap
            if end == len(tokens):
                break
            start = end - self.overlap
        return segments

    def _detect_document_type(self, text: str) -> str:
        """Выявляет тип документа по ключевым словам (та же логика, что и в DocumentChunker)."""
        text_lower = text.lower()
        if "sportsbook" in text_lower or "betting" in text_lower:
            return "sportsbook_rules"
        if "bonus" in text_lower or "promotion" in text_lower:
            return "bonus_rules"
        if "privacy" in text_lower or "data" in text_lower:
            return "privacy_policy"
        if "aml" in text_lower or "money laundering" in text_lower:
            return "aml_policy"
        if "terms" in text_lower or "conditions" in text_lower:
            return "terms"
        if "promotion" in text_lower:
            return "promotions"
        return "general" 