"""
Graph Builder - Builds code knowledge graph from source files.
"""

import os
import hashlib
import time
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.base import Symbol, SymbolKind
from parser.python_parser import PythonParser
from parser.js_parser import JavaScriptParser
from graph.database import GraphDatabase


class GraphBuilder:
    """Builds code knowledge graph from source files."""
    
    # Supported languages and their parsers
    PARSERS = {
        '.py': PythonParser,
        '.pyw': PythonParser,
        '.pyi': PythonParser,
        '.js': JavaScriptParser,
        '.jsx': JavaScriptParser,
        '.ts': JavaScriptParser,
        '.tsx': JavaScriptParser,
        '.mjs': JavaScriptParser,
        '.cjs': JavaScriptParser,
    }
    
    # Directories to skip
    SKIP_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
        '.tox', '.eggs', 'dist', 'build', 'egg-info', '.mypy_cache',
        '.pytest_cache', '.idea', '.vscode', 'vendor', 'third_party',
    }
    
    # Files to skip
    SKIP_FILES = {
        '.DS_Store', 'Thumbs.db', '.gitignore', '.gitattributes',
        'package-lock.json', 'yarn.lock', 'poetry.lock',
    }
    
    def __init__(self, db: GraphDatabase):
        """Initialize the graph builder."""
        self.db = db
        self.parsers: Dict[str, object] = {}
        self._init_parsers()
    
    def _init_parsers(self):
        """Initialize parsers for each language."""
        for ext, parser_class in self.PARSERS.items():
            if ext not in self.parsers:
                self.parsers[ext] = parser_class()
    
    def build(self, project_path: str, force: bool = False) -> Dict[str, int]:
        """
        Build the code knowledge graph for a project.
        
        Args:
            project_path: Path to the project directory
            force: Force full re-index
            
        Returns:
            Statistics about the build
        """
        start_time = time.time()
        stats = {
            'files': 0,
            'nodes': 0,
            'edges': 0,
            'skipped': 0,
            'errors': 0,
            'time': 0,
        }
        
        project_path = Path(project_path).resolve()
        
        # Connect to database
        self.db.connect()
        
        # Find all source files
        source_files = self._find_source_files(project_path)
        
        print(f"📁 Found {len(source_files)} source files")
        
        # Process each file
        for file_path in source_files:
            try:
                result = self._process_file(file_path, project_path, force)
                stats['files'] += 1
                stats['nodes'] += result['nodes']
                stats['edges'] += result['edges']
            except Exception as e:
                print(f"  ⚠️ Error processing {file_path}: {e}")
                stats['errors'] += 1
        
        stats['time'] = time.time() - start_time
        
        # Commit all changes
        self.db.conn.commit()
        
        return stats
    
    def _find_source_files(self, project_path: Path) -> List[Path]:
        """Find all source files in the project."""
        source_files = []
        
        for root, dirs, files in os.walk(project_path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS and not d.startswith('.')]
            
            for file in files:
                if file in self.SKIP_FILES:
                    continue
                
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                
                if ext in self.PARSERS:
                    source_files.append(file_path)
        
        return source_files
    
    def _process_file(self, file_path: Path, project_path: Path, force: bool) -> Dict[str, int]:
        """Process a single source file."""
        result = {'nodes': 0, 'edges': 0}
        
        # Get file info
        relative_path = str(file_path.relative_to(project_path))
        ext = file_path.suffix.lower()
        
        # Calculate file hash
        file_hash = self._calculate_file_hash(file_path)
        
        # Check if file needs re-indexing
        file_id = self.db.get_file_id(relative_path)
        
        if file_id and not force:
            # Check if file has changed
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT hash FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            if row and row[0] == file_hash:
                # File unchanged, skip
                return result
        
        # Clear existing data for this file
        if file_id:
            self.db.clear_file(file_id)
        
        # Get language
        language = self._get_language(ext)
        
        # Count lines
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            line_count = sum(1 for _ in f)
        
        # Add file record
        file_id = self.db.add_file(relative_path, language, file_hash, line_count)
        
        # Parse the file
        parser = self.parsers.get(ext)
        if not parser:
            return result
        
        try:
            symbols = parser.parse_file(str(file_path))
        except Exception as e:
            raise RuntimeError(f"Parse error: {e}")
        
        # Add symbols to database
        for symbol in symbols:
            symbol_dict = symbol.to_dict()
            symbol_dict['file'] = relative_path
            
            self.db.add_node(symbol_dict, file_id)
            result['nodes'] += 1
        
        # Add edges
        edges = parser.get_edges()
        for edge in edges:
            # Resolve target symbol ID
            target_id = self._resolve_target(edge.target, symbols, relative_path)
            
            self.db.add_edge(
                source_id=edge.source,
                target_id=target_id,
                edge_type=edge.edge_type,
                file_id=file_id,
                line=edge.line,
            )
            result['edges'] += 1
        
        return result
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _get_language(self, ext: str) -> str:
        """Get language name from file extension."""
        lang_map = {
            '.py': 'Python',
            '.pyw': 'Python',
            '.pyi': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.mjs': 'JavaScript',
            '.cjs': 'JavaScript',
        }
        return lang_map.get(ext, 'Unknown')
    
    def _resolve_target(self, target: str, symbols: List[Symbol], file_path: str) -> str:
        """Resolve a target reference to a symbol ID."""
        # Check if target is already a full symbol ID
        if ':' in target and target.split(':')[0] in ['function', 'class', 'method', 'variable']:
            return target
        
        # Try to find the symbol in the current file
        for sym in symbols:
            if sym.name == target:
                return sym.id
        
        # Return as unresolved reference
        return f"unresolved:{target}"
    
    def sync(self, project_path: str) -> Dict[str, int]:
        """
        Sync changes since last index.
        
        This is a simplified version that does a full re-index.
        A more sophisticated implementation would use file modification times.
        """
        return self.build(project_path, force=False)
