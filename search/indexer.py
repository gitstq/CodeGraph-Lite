"""
TF-IDF Indexer - Builds search index using TF-IDF algorithm.
"""

import math
import re
from typing import Dict, List, Set, Tuple
from collections import Counter
import sqlite3


class TFIDFIndexer:
    """TF-IDF based search indexer."""
    
    # Tokenization pattern
    TOKEN_PATTERN = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')
    
    # Stop words to ignore
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
        'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'just', 'if', 'else', 'elif', 'return', 'def', 'class',
        'import', 'from', 'self', 'cls', 'true', 'false', 'none', 'null',
    }
    
    def __init__(self, db: sqlite3.Connection):
        """Initialize the indexer."""
        self.db = db
        self.document_count = 0
        self.document_frequencies: Dict[str, int] = Counter()
    
    def build_index(self):
        """Build the search index from all nodes."""
        cursor = self.db.cursor()
        
        # Get all nodes with their text content
        cursor.execute("""
            SELECT n.symbol_id, n.name, n.docstring, n.signature, n.kind
            FROM nodes n
        """)
        
        nodes = cursor.fetchall()
        self.document_count = len(nodes)
        
        # Clear existing index
        cursor.execute("DELETE FROM search_index")
        
        # Build document frequencies
        self.document_frequencies = Counter()
        document_terms: Dict[str, Counter] = {}
        
        for row in nodes:
            symbol_id = row['symbol_id']
            text = self._get_text(row)
            terms = self._tokenize(text)
            
            document_terms[symbol_id] = Counter(terms)
            
            # Update document frequencies
            unique_terms = set(terms)
            for term in unique_terms:
                self.document_frequencies[term] += 1
        
        # Calculate TF-IDF and store in database
        for symbol_id, term_counts in document_terms.items():
            total_terms = sum(term_counts.values())
            
            for term, count in term_counts.items():
                tf = count / total_terms if total_terms > 0 else 0
                idf = self._calculate_idf(term)
                tfidf = tf * idf
                
                cursor.execute("""
                    INSERT INTO search_index (node_id, term, tf, idf)
                    VALUES (?, ?, ?, ?)
                """, (symbol_id, term, tf, idf))
        
        self.db.commit()
    
    def _get_text(self, row: sqlite3.Row) -> str:
        """Get searchable text from a node."""
        parts = []
        
        # Add name (most important)
        if row['name']:
            parts.append(row['name'])
            # Add camelCase/snake_case splits
            parts.extend(self._split_identifier(row['name']))
        
        # Add docstring
        if row['docstring']:
            parts.append(row['docstring'])
        
        # Add signature
        if row['signature']:
            parts.append(row['signature'])
        
        # Add kind
        if row['kind']:
            parts.append(row['kind'])
        
        return ' '.join(parts)
    
    def _split_identifier(self, identifier: str) -> List[str]:
        """Split identifier into parts (camelCase, snake_case)."""
        parts = []
        
        # Split on underscores
        for part in identifier.split('_'):
            if not part:
                continue
            
            # Split camelCase
            current = ''
            for char in part:
                if char.isupper() and current:
                    parts.append(current.lower())
                    current = char
                else:
                    current += char
            
            if current:
                parts.append(current.lower())
        
        return parts
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        tokens = self.TOKEN_PATTERN.findall(text.lower())
        
        # Filter stop words and short tokens
        return [t for t in tokens if t not in self.STOP_WORDS and len(t) > 1]
    
    def _calculate_idf(self, term: str) -> float:
        """Calculate IDF for a term."""
        df = self.document_frequencies.get(term, 0)
        if df == 0:
            return 0
        return math.log(self.document_count / df)
    
    def search(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        """
        Search for nodes matching the query.
        
        Returns list of (symbol_id, score) tuples.
        """
        query_terms = self._tokenize(query)
        
        if not query_terms:
            return []
        
        cursor = self.db.cursor()
        
        # Get all matching index entries
        placeholders = ','.join('?' * len(query_terms))
        cursor.execute(f"""
            SELECT node_id, term, tf, idf
            FROM search_index
            WHERE term IN ({placeholders})
        """, query_terms)
        
        # Aggregate scores by node
        scores: Dict[str, float] = Counter()
        
        for row in cursor.fetchall():
            node_id = row['node_id']
            term = row['term']
            tf = row['tf']
            idf = row['idf']
            
            # BM25-like scoring
            k1 = 1.5
            b = 0.75
            avg_dl = 100  # Approximate average document length
            
            score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (1)))
            scores[node_id] += score
        
        # Sort by score and return top results
        sorted_results = sorted(scores.items(), key=lambda x: -x[1])
        
        return sorted_results[:limit]
    
    def update_node(self, symbol_id: str, text: str):
        """Update index for a single node."""
        cursor = self.db.cursor()
        
        # Remove old entries
        cursor.execute("DELETE FROM search_index WHERE node_id = ?", (symbol_id,))
        
        # Tokenize and index
        terms = self._tokenize(text)
        term_counts = Counter(terms)
        total_terms = sum(term_counts.values())
        
        for term, count in term_counts.items():
            tf = count / total_terms if total_terms > 0 else 0
            idf = self._calculate_idf(term)
            
            cursor.execute("""
                INSERT INTO search_index (node_id, term, tf, idf)
                VALUES (?, ?, ?, ?)
            """, (symbol_id, term, tf, idf))
        
        self.db.commit()
