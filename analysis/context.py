"""
Context Builder - Builds code context for AI tasks.
"""

from typing import List, Dict, Any, Set, Optional
from collections import Counter
import re

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.database import GraphDatabase
from search.engine import SearchEngine


class ContextBuilder:
    """Builds relevant code context for AI tasks."""
    
    def __init__(self, db: GraphDatabase):
        """Initialize the context builder."""
        self.db = db
        self.search = SearchEngine(db)
    
    def build(self, task: str, max_nodes: int = 30) -> Dict[str, Any]:
        """
        Build code context for a specific task.
        
        Args:
            task: Task description
            max_nodes: Maximum number of nodes to include
            
        Returns:
            Context with entry points, related symbols, and code snippets
        """
        # Extract keywords from task
        keywords = self._extract_keywords(task)
        
        # Find entry points using semantic search
        entry_points = self._find_entry_points(keywords, max_nodes // 3)
        
        # Find related symbols through graph traversal
        related = self._find_related_symbols(entry_points, max_nodes // 2)
        
        # Get code snippets
        snippets = self._get_code_snippets(entry_points + related)
        
        return {
            'task': task,
            'keywords': keywords,
            'entry_points': entry_points,
            'related': related,
            'snippets': snippets,
            'stats': {
                'entry_points': len(entry_points),
                'related': len(related),
                'snippets': len(snippets),
            }
        }
    
    def _extract_keywords(self, task: str) -> List[str]:
        """Extract keywords from task description."""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'fix', 'add', 'update', 'change', 'modify', 'implement', 'create',
            'remove', 'delete', 'refactor', 'improve', 'optimize', 'bug', 'issue',
        }
        
        # Tokenize
        tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', task.lower())
        
        # Filter and deduplicate
        keywords = []
        seen = set()
        
        for token in tokens:
            if token not in stop_words and len(token) > 2 and token not in seen:
                keywords.append(token)
                seen.add(token)
        
        return keywords
    
    def _find_entry_points(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """Find entry point symbols using keyword search."""
        entry_points = []
        seen_ids = set()
        
        # Search for each keyword
        for keyword in keywords:
            results = self.search.search(keyword, limit=limit // len(keywords) + 1)
            
            for result in results:
                if result['id'] not in seen_ids:
                    seen_ids.add(result['id'])
                    entry_points.append(result)
        
        # Sort by relevance score
        entry_points.sort(key=lambda x: -x.get('score', 0))
        
        return entry_points[:limit]
    
    def _find_related_symbols(self, entry_points: List[Dict[str, Any]], 
                               limit: int) -> List[Dict[str, Any]]:
        """Find related symbols through graph traversal."""
        related = []
        seen_ids = {ep['id'] for ep in entry_points}
        
        for entry in entry_points[:10]:  # Limit traversal depth
            # Get callees
            callees = self.db.get_callees(entry['id'])
            for callee in callees:
                if callee['symbol_id'] not in seen_ids:
                    seen_ids.add(callee['symbol_id'])
                    callee['relation'] = 'callee'
                    related.append(callee)
            
            # Get callers
            callers = self.db.get_callers(entry['id'])
            for caller in callers:
                if caller['symbol_id'] not in seen_ids:
                    seen_ids.add(caller['symbol_id'])
                    caller['relation'] = 'caller'
                    related.append(caller)
        
        # Score by frequency
        name_counts = Counter(r['name'] for r in related)
        for r in related:
            r['relevance'] = name_counts.get(r['name'], 1)
        
        # Sort by relevance
        related.sort(key=lambda x: -x.get('relevance', 0))
        
        return related[:limit]
    
    def _get_code_snippets(self, symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get code snippets for symbols."""
        snippets = []
        
        for symbol in symbols[:20]:
            file_path = symbol.get('file')
            if not file_path:
                continue
            
            try:
                snippet = self._read_code_snippet(
                    file_path,
                    symbol['line'],
                    symbol.get('end_line', symbol['line']),
                )
                
                if snippet:
                    snippets.append({
                        'symbol': symbol['name'],
                        'kind': symbol['kind'],
                        'file': file_path,
                        'line': symbol['line'],
                        'code': snippet,
                    })
            except Exception:
                pass
        
        return snippets
    
    def _read_code_snippet(self, file_path: str, start_line: int, 
                           end_line: int, context: int = 3) -> Optional[str]:
        """Read code snippet from file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Add context lines
            start = max(0, start_line - context - 1)
            end = min(len(lines), end_line + context)
            
            snippet_lines = lines[start:end]
            
            return ''.join(snippet_lines)
        except Exception:
            return None
    
    def build_for_symbol(self, symbol_name: str, include_code: bool = True) -> Dict[str, Any]:
        """Build context for a specific symbol."""
        symbols = self.db.get_node_by_name(symbol_name)
        
        if not symbols:
            return {'symbol': symbol_name, 'found': False}
        
        # Use the first match
        symbol = symbols[0]
        
        context = {
            'symbol': symbol_name,
            'found': True,
            'definition': symbol,
            'callers': self.db.get_callers(symbol['id']),
            'callees': self.db.get_callees(symbol['id']),
        }
        
        if include_code:
            context['code'] = self._read_code_snippet(
                symbol['file'],
                symbol['line'],
                symbol.get('end_line', symbol['line']),
            )
        
        return context
    
    def build_for_file(self, file_path: str) -> Dict[str, Any]:
        """Build context for a file."""
        cursor = self.db.conn.cursor()
        
        # Get all symbols in the file
        cursor.execute("""
            SELECT n.*, f.path as file_path
            FROM nodes n
            JOIN files f ON n.file_id = f.id
            WHERE f.path = ?
            ORDER BY n.line
        """, (file_path,))
        
        symbols = [self.db._row_to_node(row) for row in cursor.fetchall()]
        
        # Group by kind
        by_kind = {}
        for sym in symbols:
            kind = sym['kind']
            if kind not in by_kind:
                by_kind[kind] = []
            by_kind[kind].append(sym)
        
        # Get imports
        imports = []
        for sym in symbols:
            if sym['kind'] == 'import':
                imports.append(sym)
        
        return {
            'file': file_path,
            'symbols': symbols,
            'by_kind': by_kind,
            'imports': imports,
            'stats': {
                'total': len(symbols),
                'by_kind': {k: len(v) for k, v in by_kind.items()},
            }
        }
