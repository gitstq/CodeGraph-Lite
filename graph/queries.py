"""
Graph Queries - Common query operations.
"""

from typing import List, Dict, Any, Optional
from graph.database import GraphDatabase


class GraphQueries:
    """Common graph query operations."""
    
    def __init__(self, db: GraphDatabase):
        self.db = db
    
    def find_symbol(self, name: str, kind: str = None) -> List[Dict[str, Any]]:
        """Find symbols by name."""
        return self.db.get_node_by_name(name, kind)
    
    def find_callers(self, symbol_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Find all callers of a symbol."""
        symbols = self.db.get_node_by_name(symbol_name)
        if not symbols:
            return []
        
        all_callers = []
        visited = set()
        
        for symbol in symbols:
            self._find_callers_recursive(symbol['id'], depth, visited, all_callers, 0)
        
        return all_callers
    
    def _find_callers_recursive(self, symbol_id: str, max_depth: int, 
                                 visited: set, result: list, current_depth: int):
        """Recursively find callers."""
        if current_depth >= max_depth or symbol_id in visited:
            return
        
        visited.add(symbol_id)
        
        callers = self.db.get_callers(symbol_id)
        for caller in callers:
            caller['depth'] = current_depth + 1
            result.append(caller)
            self._find_callers_recursive(caller['symbol_id'], max_depth, visited, result, current_depth + 1)
    
    def find_callees(self, symbol_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Find all callees of a symbol."""
        symbols = self.db.get_node_by_name(symbol_name)
        if not symbols:
            return []
        
        all_callees = []
        visited = set()
        
        for symbol in symbols:
            self._find_callees_recursive(symbol['id'], depth, visited, all_callees, 0)
        
        return all_callees
    
    def _find_callees_recursive(self, symbol_id: str, max_depth: int,
                                 visited: set, result: list, current_depth: int):
        """Recursively find callees."""
        if current_depth >= max_depth or symbol_id in visited:
            return
        
        visited.add(symbol_id)
        
        callees = self.db.get_callees(symbol_id)
        for callee in callees:
            callee['depth'] = current_depth + 1
            result.append(callee)
            self._find_callees_recursive(callee['symbol_id'], max_depth, visited, result, current_depth + 1)
    
    def get_class_hierarchy(self, class_name: str) -> Dict[str, Any]:
        """Get class hierarchy (extends relationships)."""
        symbols = self.db.get_node_by_name(class_name, 'class')
        if not symbols:
            return {}
        
        result = {
            'class': class_name,
            'parents': [],
            'children': [],
            'methods': [],
        }
        
        for symbol in symbols:
            # Get bases (parents)
            for base in symbol.get('bases', []):
                result['parents'].append(base)
            
            # Get children (classes that extend this one)
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT n.name, n.symbol_id, f.path as file
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.bases LIKE ?
            """, (f'%{class_name}%',))
            
            for row in cursor.fetchall():
                result['children'].append({
                    'name': row['name'],
                    'symbol_id': row['symbol_id'],
                    'file': row['file'],
                })
            
            # Get methods
            cursor.execute("""
                SELECT name, signature, line
                FROM nodes
                WHERE parent = ? AND kind = 'method'
            """, (class_name,))
            
            for row in cursor.fetchall():
                result['methods'].append({
                    'name': row['name'],
                    'signature': row['signature'],
                    'line': row['line'],
                })
        
        return result
    
    def get_file_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        """Get all symbols in a file."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT n.*, f.path as file_path
            FROM nodes n
            JOIN files f ON n.file_id = f.id
            WHERE f.path = ?
            ORDER BY n.line
        """, (file_path,))
        
        return [self.db._row_to_node(row) for row in cursor.fetchall()]
    
    def get_dependencies(self, file_path: str) -> Dict[str, List[str]]:
        """Get file dependencies (imports)."""
        cursor = self.db.conn.cursor()
        
        # Get imports from this file
        cursor.execute("""
            SELECT e.target_id
            FROM edges e
            JOIN nodes n ON e.source_id = n.symbol_id
            JOIN files f ON n.file_id = f.id
            WHERE f.path = ? AND e.edge_type = 'imports'
        """, (file_path,))
        
        imports = [row['target_id'] for row in cursor.fetchall()]
        
        # Get files that import this file
        cursor.execute("""
            SELECT DISTINCT f.path
            FROM edges e
            JOIN nodes n ON e.target_id = n.symbol_id
            JOIN files f ON n.file_id = f.id
            WHERE e.edge_type = 'imports'
            AND n.symbol_id IN (
                SELECT symbol_id FROM nodes WHERE file_id = (
                    SELECT id FROM files WHERE path = ?
                )
            )
        """, (file_path,))
        
        imported_by = [row['path'] for row in cursor.fetchall()]
        
        return {
            'imports': imports,
            'imported_by': imported_by,
        }
