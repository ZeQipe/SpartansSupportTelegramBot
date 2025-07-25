from embeddings.search import DocumentSearch

class ContextBuilder:
    """
    SINGLE RESPONSIBILITY: Context search and building
    
    Responsibilities:
    - Query preprocessing delegation
    - Multilingual context search (top_k=25)
    - Context text building and concatenation
    - Search statistics aggregation
    
    PRESERVE EXACT: Current search parameters and multilingual logic
    """
    
    def __init__(self, search: DocumentSearch):
        self.search = search
        
    def get_context_for_query(self, query: str, language: str) -> str:
        """
        EXACT COPY: Current logic from main.py handle_message
        processed_query = self.search.preprocess_query(message_text, query_language)
        contexts = self.search.get_multilingual_context(processed_query, top_k=25)
        doc_context_raw = contexts.get(query_language, '') or next(iter(contexts.values()), '')
        return doc_context_raw  # No email removal at this stage
        """
        processed_query = self.search.preprocess_query(query, language)
        contexts = self.search.get_multilingual_context(processed_query, top_k=25, language=language)  # Pass language to limit search
        doc_context_raw = contexts.get(language, '') or next(iter(contexts.values()), '')
        return doc_context_raw  # No email removal at this stage 