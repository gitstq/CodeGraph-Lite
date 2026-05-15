"""
Python Code Parser
Uses Python's built-in ast module for parsing.
"""

import ast
import re
from typing import List, Dict, Optional, Set
from .base import BaseParser, Symbol, SymbolKind, Edge


class PythonParser(BaseParser):
    """Parser for Python source code using AST."""
    
    SUPPORTED_EXTENSIONS = ['.py', '.pyw', '.pyi']
    
    def __init__(self):
        super().__init__()
        self.current_class: Optional[str] = None
        self.imports: Dict[str, str] = {}  # alias -> full_name
        self.all_calls: List[tuple] = []  # (caller_id, called_name, line)
    
    def parse(self, content: str, file_path: str) -> List[Symbol]:
        """Parse Python source code."""
        self.clear()
        self.current_file = file_path
        self.imports = {}
        self.all_calls = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        
        # First pass: collect imports
        self._collect_imports(tree)
        
        # Second pass: collect symbols
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self._process_function(node)
            elif isinstance(node, ast.ClassDef):
                self._process_class(node)
        
        # Third pass: resolve calls
        self._resolve_calls()
        
        return self.symbols
    
    def _collect_imports(self, tree: ast.AST):
        """Collect import statements."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    self.imports[name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    name = alias.asname or alias.name
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    self.imports[name] = full_name
    
    def _process_function(self, node, parent_class: Optional[str] = None):
        """Process a function definition."""
        # Determine if it's a method
        kind = SymbolKind.METHOD if parent_class else SymbolKind.FUNCTION
        
        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            dec_name = self._get_node_name(dec)
            if dec_name:
                decorators.append(dec_name)
        
        # Get signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        signature = f"{node.name}({', '.join(args)})"
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        # Collect function calls
        calls = self._collect_calls(node.body)
        
        symbol = Symbol(
            name=node.name,
            kind=kind,
            file=self.current_file,
            line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            column=node.col_offset,
            docstring=docstring,
            signature=signature,
            parent=parent_class,
            decorators=decorators,
            calls=calls,
        )
        
        self._add_symbol(symbol)
        
        # Record calls for edge creation
        caller_id = symbol.id
        for call in calls:
            self.all_calls.append((caller_id, call, node.lineno))
        
        return symbol
    
    def _process_class(self, node: ast.ClassDef):
        """Process a class definition."""
        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            dec_name = self._get_node_name(dec)
            if dec_name:
                decorators.append(dec_name)
        
        # Get bases
        bases = []
        for base in node.bases:
            base_name = self._get_node_name(base)
            if base_name:
                bases.append(base_name)
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        symbol = Symbol(
            name=node.name,
            kind=SymbolKind.CLASS,
            file=self.current_file,
            line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            column=node.col_offset,
            docstring=docstring,
            decorators=decorators,
            bases=bases,
        )
        
        self._add_symbol(symbol)
        
        # Create extends edges
        for base in bases:
            self._add_edge(Edge(
                source=symbol.id,
                target=f"class:{base}",
                edge_type="extends",
                file=self.current_file,
                line=node.lineno,
            ))
        
        # Process class body for methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._process_function(item, parent_class=node.name)
    
    def _collect_calls(self, body: List[ast.stmt]) -> List[str]:
        """Collect function calls from a body of code."""
        calls = []
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Call):
                call_name = self._get_node_name(node.func)
                if call_name:
                    calls.append(call_name)
        return list(set(calls))
    
    def _get_node_name(self, node: ast.AST) -> Optional[str]:
        """Get the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_node_name(node.value)
            if value:
                return f"{value}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Call):
            return self._get_node_name(node.func)
        return None
    
    def _resolve_calls(self):
        """Resolve call names to actual symbols and create edges."""
        for caller_id, called_name, line in self.all_calls:
            # Try to resolve the call
            resolved = self._resolve_name(called_name)
            if resolved:
                self._add_edge(Edge(
                    source=caller_id,
                    target=resolved,
                    edge_type="calls",
                    file=self.current_file,
                    line=line,
                ))
    
    def _resolve_name(self, name: str) -> Optional[str]:
        """Resolve a name to a symbol ID."""
        # Check if it's an imported name
        if name in self.imports:
            return f"function:{self.imports[name]}"
        
        # Check if it's a method call (self.xxx or cls.xxx)
        if '.' in name:
            parts = name.split('.')
            if parts[0] in ('self', 'cls') and len(parts) > 1:
                return f"method:{parts[1]}"
        
        # Return as function reference
        return f"function:{name}"
