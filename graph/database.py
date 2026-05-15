"""
Graph Database - SQLite-based code knowledge graph storage.
"""

import sqlite3
import json
import time
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime


class GraphDatabase:
    """SQLite-based graph database for code symbols and relationships."""
    
    def __init__(self, db_path: str):
        """Initialize the database."""
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._ensure_db_dir()
    
    def _ensure_db_dir(self):
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def connect(self):
        """Connect to the database."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def initialize(self):
        """Initialize database schema."""
        self.connect()
        
        cursor = self.conn.cursor()
        
        # Files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                language TEXT,
                hash TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                line_count INTEGER DEFAULT 0
            )
        """)
        
        # Nodes table (symbols)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                file_id INTEGER NOT NULL,
                line INTEGER NOT NULL,
                end_line INTEGER DEFAULT 0,
                column INTEGER DEFAULT 0,
                docstring TEXT,
                signature TEXT,
                parent TEXT,
                decorators TEXT,
                bases TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        """)
        
        # Edges table (relationships)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                file_id INTEGER,
                line INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        """)
        
        # Search index table (TF-IDF vectors)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                term TEXT NOT NULL,
                tf REAL DEFAULT 0,
                idf REAL DEFAULT 0,
                UNIQUE(node_id, term)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_term ON search_index(term)")
        
        self.conn.commit()
    
    def add_file(self, path: str, language: str = None, hash: str = None, line_count: int = 0) -> int:
        """Add or update a file record."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO files (path, language, hash, line_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                language = excluded.language,
                hash = excluded.hash,
                line_count = excluded.line_count,
                indexed_at = CURRENT_TIMESTAMP
        """, (path, language, hash, line_count))
        
        cursor.execute("SELECT id FROM files WHERE path = ?", (path,))
        return cursor.fetchone()[0]
    
    def get_file_id(self, path: str) -> Optional[int]:
        """Get file ID by path."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM files WHERE path = ?", (path,))
        row = cursor.fetchone()
        return row[0] if row else None
    
    def add_node(self, symbol: Dict[str, Any], file_id: int) -> int:
        """Add a node (symbol) to the database."""
        cursor = self.conn.cursor()
        
        symbol_id = f"{symbol['kind']}:{symbol['file']}:{symbol['name']}:{symbol['line']}"
        
        cursor.execute("""
            INSERT INTO nodes (
                symbol_id, name, kind, file_id, line, end_line, column,
                docstring, signature, parent, decorators, bases, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol_id) DO UPDATE SET
                name = excluded.name,
                kind = excluded.kind,
                end_line = excluded.end_line,
                docstring = excluded.docstring,
                signature = excluded.signature,
                parent = excluded.parent,
                decorators = excluded.decorators,
                bases = excluded.bases,
                metadata = excluded.metadata
        """, (
            symbol_id,
            symbol['name'],
            symbol['kind'],
            file_id,
            symbol['line'],
            symbol.get('end_line', 0),
            symbol.get('column', 0),
            symbol.get('docstring'),
            symbol.get('signature'),
            symbol.get('parent'),
            json.dumps(symbol.get('decorators', [])),
            json.dumps(symbol.get('bases', [])),
            json.dumps(symbol.get('metadata', {})),
        ))
        
        return cursor.lastrowid
    
    def add_edge(self, source_id: str, target_id: str, edge_type: str, 
                 file_id: int = None, line: int = 0):
        """Add an edge (relationship) to the database."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO edges (source_id, target_id, edge_type, file_id, line)
            VALUES (?, ?, ?, ?, ?)
        """, (source_id, target_id, edge_type, file_id, line))
    
    def get_node(self, symbol_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by symbol ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT n.*, f.path as file_path
            FROM nodes n
            JOIN files f ON n.file_id = f.id
            WHERE n.symbol_id = ?
        """, (symbol_id,))
        
        row = cursor.fetchone()
        if row:
            return self._row_to_node(row)
        return None
    
    def get_node_by_name(self, name: str, kind: str = None) -> List[Dict[str, Any]]:
        """Get nodes by name."""
        cursor = self.conn.cursor()
        
        if kind:
            cursor.execute("""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.name = ? AND n.kind = ?
            """, (name, kind))
        else:
            cursor.execute("""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.name = ?
            """, (name,))
        
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    def search_nodes(self, query: str, kind: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search nodes by name (LIKE query)."""
        cursor = self.conn.cursor()
        
        search_term = f"%{query}%"
        
        if kind:
            cursor.execute("""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.name LIKE ? AND n.kind = ?
                ORDER BY n.name
                LIMIT ?
            """, (search_term, kind, limit))
        else:
            cursor.execute("""
                SELECT n.*, f.path as file_path
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.name LIKE ?
                ORDER BY n.name
                LIMIT ?
            """, (search_term, limit))
        
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    def get_edges_from(self, source_id: str, edge_type: str = None) -> List[Dict[str, Any]]:
        """Get edges from a node."""
        cursor = self.conn.cursor()
        
        if edge_type:
            cursor.execute("""
                SELECT * FROM edges WHERE source_id = ? AND edge_type = ?
            """, (source_id, edge_type))
        else:
            cursor.execute("""
                SELECT * FROM edges WHERE source_id = ?
            """, (source_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_edges_to(self, target_id: str, edge_type: str = None) -> List[Dict[str, Any]]:
        """Get edges to a node."""
        cursor = self.conn.cursor()
        
        if edge_type:
            cursor.execute("""
                SELECT * FROM edges WHERE target_id = ? AND edge_type = ?
            """, (target_id, edge_type))
        else:
            cursor.execute("""
                SELECT * FROM edges WHERE target_id = ?
            """, (target_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_callers(self, symbol_id: str) -> List[Dict[str, Any]]:
        """Get all callers of a symbol."""
        cursor = self.conn.cursor()
        
        # Find edges where target is this symbol
        cursor.execute("""
            SELECT e.source_id, e.line, n.name, n.kind, f.path as file
            FROM edges e
            JOIN nodes n ON e.source_id = n.symbol_id
            JOIN files f ON n.file_id = f.id
            WHERE e.target_id = ? AND e.edge_type = 'calls'
        """, (symbol_id,))
        
        callers = []
        for row in cursor.fetchall():
            callers.append({
                'symbol_id': row['source_id'],
                'name': row['name'],
                'kind': row['kind'],
                'file': row['file'],
                'line': row['line'],
            })
        
        return callers
    
    def get_callees(self, symbol_id: str) -> List[Dict[str, Any]]:
        """Get all callees of a symbol."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT e.target_id, e.line, n.name, n.kind, f.path as file
            FROM edges e
            LEFT JOIN nodes n ON e.target_id = n.symbol_id
            LEFT JOIN files f ON n.file_id = f.id
            WHERE e.source_id = ? AND e.edge_type = 'calls'
        """, (symbol_id,))
        
        callees = []
        for row in cursor.fetchall():
            callees.append({
                'symbol_id': row['target_id'],
                'name': row['name'] or row['target_id'].split(':')[-1] if ':' in row['target_id'] else row['target_id'],
                'kind': row['kind'],
                'file': row['file'],
                'line': row['line'],
            })
        
        return callees
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Files count
        cursor.execute("SELECT COUNT(*) FROM files")
        stats['files'] = cursor.fetchone()[0]
        
        # Nodes count
        cursor.execute("SELECT COUNT(*) FROM nodes")
        stats['nodes'] = cursor.fetchone()[0]
        
        # Edges count
        cursor.execute("SELECT COUNT(*) FROM edges")
        stats['edges'] = cursor.fetchone()[0]
        
        # Nodes by kind
        cursor.execute("""
            SELECT kind, COUNT(*) as count
            FROM nodes
            GROUP BY kind
            ORDER BY count DESC
        """)
        stats['nodes_by_kind'] = {row['kind']: row['count'] for row in cursor.fetchall()}
        
        # Files by language
        cursor.execute("""
            SELECT language, COUNT(*) as count
            FROM files
            WHERE language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
        """)
        stats['files_by_lang'] = {row['language']: row['count'] for row in cursor.fetchall()}
        
        return stats
    
    def clear_file(self, file_id: int):
        """Clear all nodes and edges for a file."""
        cursor = self.conn.cursor()
        
        # Get node IDs for this file
        cursor.execute("SELECT symbol_id FROM nodes WHERE file_id = ?", (file_id,))
        node_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete edges
        for node_id in node_ids:
            cursor.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))
        
        # Delete nodes
        cursor.execute("DELETE FROM nodes WHERE file_id = ?", (file_id,))
        
        # Delete search index
        for node_id in node_ids:
            cursor.execute("DELETE FROM search_index WHERE node_id = ?", (node_id,))
    
    def export_json(self) -> Dict[str, Any]:
        """Export the entire graph as JSON."""
        cursor = self.conn.cursor()
        
        # Export files
        cursor.execute("SELECT * FROM files")
        files = [dict(row) for row in cursor.fetchall()]
        
        # Export nodes
        cursor.execute("SELECT * FROM nodes")
        nodes = [dict(row) for row in cursor.fetchall()]
        
        # Export edges
        cursor.execute("SELECT * FROM edges")
        edges = [dict(row) for row in cursor.fetchall()]
        
        return {
            'files': files,
            'nodes': nodes,
            'edges': edges,
            'exported_at': datetime.now().isoformat(),
        }
    
    def _row_to_node(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a node dictionary."""
        return {
            'id': row['symbol_id'],
            'name': row['name'],
            'kind': row['kind'],
            'file': row['file_path'],
            'line': row['line'],
            'end_line': row['end_line'],
            'column': row['column'],
            'docstring': row['docstring'],
            'signature': row['signature'],
            'parent': row['parent'],
            'decorators': json.loads(row['decorators']) if row['decorators'] else [],
            'bases': json.loads(row['bases']) if row['bases'] else [],
            'metadata': json.loads(row['metadata']) if row['metadata'] else {},
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
