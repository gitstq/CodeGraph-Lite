"""
Search Engine - High-level search operations.
"""

from typing import List, Dict, Any, Optional
import sqlite3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.database import GraphDatabase
from search.indexer import TFIDFIndexer


class SearchEngine:
    """High-level search engine for code symbols."""
    
    def __init__(self, db: GraphDatabase):
        """Initialize the search engine."""
        self.db = db
        self.indexer = TFIDFIndexer(db.conn)
    
    def search(self, query: str, kind: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for symbols matching the query.
        
        Args:
            query: Search query
            kind: Filter by symbol kind (function, class, method, etc.)
            limit: Maximum number of results
            
        Returns:
            List of matching symbols with scores
        """
        # First, try exact name match
        exact_matches = self.db.search_nodes(query, kind, limit)
        
        if exact_matches:
            return exact_matches
        
        # Then, try semantic search using TF-IDF
        results = self.indexer.search(query, limit * 2)
        
        if not results:
            return []
        
        # Get full node details
        symbol_ids = [r[0] for r in results]
        scores = {r[0]: r[1] for r in results}
        
        cursor = self.db.conn.cursor()
        
        placeholders = ','.join('?' * len(symbol_ids))
        
        if kind:
            cursor.execute(f"""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.symbol_id IN ({placeholders}) AND n.kind = ?
            """, symbol_ids + [kind])
        else:
            cursor.execute(f"""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.symbol_id IN ({placeholders})
            """, symbol_ids)
        
        nodes = []
        for row in cursor.fetchall():
            node = self.db._row_to_node(row)
            node['score'] = scores.get(node['id'], 0)
            nodes.append(node)
        
        # Sort by score
        nodes.sort(key=lambda x: -x.get('score', 0))
        
        return nodes[:limit]
    
    def search_by_prefix(self, prefix: str, kind: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for symbols starting with prefix (for autocomplete)."""
        cursor = self.db.conn.cursor()
        
        if kind:
            cursor.execute("""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.name LIKE ? || '%' AND n.kind = ?
                ORDER BY n.name
                LIMIT ?
            """, (prefix, kind, limit))
        else:
            cursor.execute("""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.name LIKE ? || '%'
                ORDER BY n.name
                LIMIT ?
            """, (prefix, limit))
        
        return [self.db._row_to_node(row) for row in cursor.fetchall()]
    
    def search_in_file(self, file_path: str, query: str = None) -> List[Dict[str, Any]]:
        """Search for symbols in a specific file."""
        cursor = self.db.conn.cursor()
        
        if query:
            cursor.execute("""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE f.path = ? AND n.name LIKE ?
                ORDER BY n.line
            """, (file_path, f'%{query}%'))
        else:
            cursor.execute("""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE f.path = ?
                ORDER BY n.line
            """, (file_path,))
        
        return [self.db._row_to_node(row) for row in cursor.fetchall()]
    
    def get_similar_symbols(self, symbol_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find symbols similar to the given one."""
        # Get the symbol
        symbol = self.db.get_node(symbol_id)
        if not symbol:
            return []
        
        # Build search query from symbol's name and docstring
        query_parts = [symbol['name']]
        if symbol['docstring']:
            query_parts.append(symbol['docstring'])
        
        query = ' '.join(query_parts)
        
        # Search for similar symbols
        results = self.indexer.search(query, limit + 1)
        
        # Filter out the original symbol
        similar = []
        for sym_id, score in results:
            if sym_id != symbol_id:
                node = self.db.get_node(sym_id)
                if node:
                    node['score'] = score
                    similar.append(node)
        
        return similar[:limit]
    
    def build_index(self):
        """Build or rebuild the search index."""
        self.indexer.build_index()
    
    def get_search_suggestions(self, partial: str, limit: int = 5) -> List[str]:
        """Get search suggestions for partial input."""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT name
            FROM nodes
            WHERE name LIKE ? || '%'
            ORDER BY name
            LIMIT ?
        """, (partial, limit))
        
        return [row['name'] for row in cursor.fetchall()]
