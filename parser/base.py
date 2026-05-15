"""
Base Parser Module
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from pathlib import Path


class SymbolKind(Enum):
    """Symbol kinds in code."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    MODULE = "module"
    INTERFACE = "interface"
    CONSTANT = "constant"
    PROPERTY = "property"
    DECORATOR = "decorator"


@dataclass
class Symbol:
    """Represents a code symbol."""
    name: str
    kind: SymbolKind
    file: str
    line: int
    end_line: int = 0
    column: int = 0
    docstring: Optional[str] = None
    signature: Optional[str] = None
    parent: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "kind": self.kind.value,
            "file": self.file,
            "line": self.line,
            "end_line": self.end_line,
            "column": self.column,
            "docstring": self.docstring,
            "signature": self.signature,
            "parent": self.parent,
            "decorators": self.decorators,
            "imports": self.imports,
            "calls": self.calls,
            "bases": self.bases,
            "metadata": self.metadata,
        }
    
    @property
    def id(self) -> str:
        """Generate unique ID for this symbol."""
        return f"{self.kind.value}:{self.file}:{self.name}:{self.line}"


@dataclass
class Edge:
    """Represents a relationship between symbols."""
    source: str
    target: str
    edge_type: str  # "calls", "imports", "extends", "implements", "contains"
    file: str = ""
    line: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.edge_type,
            "file": self.file,
            "line": self.line,
        }


class BaseParser(ABC):
    """Abstract base class for code parsers."""
    
    SUPPORTED_EXTENSIONS: List[str] = []
    
    def __init__(self):
        self.symbols: List[Symbol] = []
        self.edges: List[Edge] = []
        self.current_file: str = ""
    
    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        """Check if this parser can handle the file."""
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS
    
    @abstractmethod
    def parse(self, content: str, file_path: str) -> List[Symbol]:
        """
        Parse source code and extract symbols.
        
        Args:
            content: Source code content
            file_path: Path to the file
            
        Returns:
            List of extracted symbols
        """
        pass
    
    def parse_file(self, file_path: str) -> List[Symbol]:
        """Parse a file and extract symbols."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self.parse(content, file_path)
    
    def get_edges(self) -> List[Edge]:
        """Get extracted edges."""
        return self.edges
    
    def clear(self):
        """Clear parsed data."""
        self.symbols = []
        self.edges = []
        self.current_file = ""
    
    def _add_symbol(self, symbol: Symbol):
        """Add a symbol to the list."""
        self.symbols.append(symbol)
    
    def _add_edge(self, edge: Edge):
        """Add an edge to the list."""
        self.edges.append(edge)
