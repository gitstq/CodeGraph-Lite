"""
JavaScript/TypeScript Code Parser
Uses regex-based parsing for simplicity (no external dependencies).
"""

import re
from typing import List, Dict, Optional, Set
from .base import BaseParser, Symbol, SymbolKind, Edge


class JavaScriptParser(BaseParser):
    """Parser for JavaScript/TypeScript source code using regex."""
    
    SUPPORTED_EXTENSIONS = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']
    
    # Regex patterns for JavaScript/TypeScript
    PATTERNS = {
        'function': re.compile(
            r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
            re.MULTILINE
        ),
        'arrow_function': re.compile(
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>',
            re.MULTILINE
        ),
        'class': re.compile(
            r'class\s+(\w+)(?:\s+extends\s+(\w+))?',
            re.MULTILINE
        ),
        'method': re.compile(
            r'(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*\{',
            re.MULTILINE
        ),
        'import': re.compile(
            r'import\s+(?:\{([^}]+)\}|\*\s+as\s+(\w+)|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]',
            re.MULTILINE
        ),
        'export': re.compile(
            r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)',
            re.MULTILINE
        ),
        'interface': re.compile(
            r'interface\s+(\w+)(?:\s+extends\s+(\w+))?',
            re.MULTILINE
        ),
        'type': re.compile(
            r'type\s+(\w+)\s*=',
            re.MULTILINE
        ),
        'const': re.compile(
            r'const\s+(\w+)\s*=',
            re.MULTILINE
        ),
        'call': re.compile(
            r'(\w+)\s*\(',
            re.MULTILINE
        ),
        'comment': re.compile(
            r'/\*\*[\s\S]*?\*/|//[^\n]*',
            re.MULTILINE
        ),
        'docstring': re.compile(
            r'/\*\*[\s\S]*?\*/',
            re.MULTILINE
        ),
    }
    
    def __init__(self):
        super().__init__()
        self.imports: Dict[str, str] = {}
        self.current_class: Optional[str] = None
    
    def parse(self, content: str, file_path: str) -> List[Symbol]:
        """Parse JavaScript/TypeScript source code."""
        self.clear()
        self.current_file = file_path
        self.imports = {}
        
        # Remove comments for cleaner parsing
        clean_content = self._remove_comments(content)
        
        # Collect imports first
        self._collect_imports(clean_content)
        
        # Parse classes
        self._parse_classes(clean_content, content)
        
        # Parse functions
        self._parse_functions(clean_content, content)
        
        # Parse interfaces (TypeScript)
        self._parse_interfaces(clean_content, content)
        
        # Parse exports
        self._parse_exports(clean_content, content)
        
        return self.symbols
    
    def _remove_comments(self, content: str) -> str:
        """Remove comments from code."""
        return self.PATTERNS['comment'].sub('', content)
    
    def _collect_imports(self, content: str):
        """Collect import statements."""
        for match in self.PATTERNS['import'].finditer(content):
            named_imports = match.group(1)
            namespace_import = match.group(2)
            default_import = match.group(3)
            module = match.group(4)
            
            if named_imports:
                for imp in named_imports.split(','):
                    imp = imp.strip()
                    if imp:
                        # Handle 'as' aliases
                        if ' as ' in imp:
                            parts = imp.split(' as ')
                            self.imports[parts[1].strip()] = f"{module}:{parts[0].strip()}"
                        else:
                            self.imports[imp] = f"{module}:{imp}"
            elif namespace_import:
                self.imports[namespace_import] = module
            elif default_import:
                self.imports[default_import] = f"{module}:default"
    
    def _parse_classes(self, clean_content: str, original_content: str):
        """Parse class definitions."""
        for match in self.PATTERNS['class'].finditer(clean_content):
            class_name = match.group(1)
            base_class = match.group(2)
            
            # Find class body
            class_start = match.start()
            class_body = self._extract_block(clean_content, match.end())
            
            # Get docstring
            docstring = self._get_docstring_before(original_content, class_start)
            
            symbol = Symbol(
                name=class_name,
                kind=SymbolKind.CLASS,
                file=self.current_file,
                line=self._get_line_number(clean_content, class_start),
                docstring=docstring,
                bases=[base_class] if base_class else [],
            )
            
            self._add_symbol(symbol)
            
            # Create extends edge
            if base_class:
                self._add_edge(Edge(
                    source=symbol.id,
                    target=f"class:{base_class}",
                    edge_type="extends",
                    file=self.current_file,
                ))
            
            # Parse methods within class
            self._parse_methods(class_body, class_name)
    
    def _parse_methods(self, class_body: str, class_name: str):
        """Parse methods within a class."""
        for match in self.PATTERNS['method'].finditer(class_body):
            method_name = match.group(1)
            
            # Skip keywords and special names
            if method_name in ('if', 'for', 'while', 'switch', 'catch', 'function', 'class', 'return'):
                continue
            
            # Skip if it looks like a function call (not a method definition)
            before = class_body[:match.start()]
            if before.rstrip().endswith('=') or before.rstrip().endswith(':'):
                continue
            
            args = match.group(2)
            signature = f"{method_name}({args})"
            
            symbol = Symbol(
                name=method_name,
                kind=SymbolKind.METHOD,
                file=self.current_file,
                line=self._get_line_number(class_body, match.start()),
                signature=signature,
                parent=class_name,
            )
            
            self._add_symbol(symbol)
            
            # Collect calls
            method_body = self._extract_block(class_body, match.end())
            self._collect_calls(method_body, symbol.id)
    
    def _parse_functions(self, clean_content: str, original_content: str):
        """Parse function definitions."""
        # Regular functions
        for match in self.PATTERNS['function'].finditer(clean_content):
            func_name = match.group(1)
            args = match.group(2)
            signature = f"{func_name}({args})"
            
            docstring = self._get_docstring_before(original_content, match.start())
            
            symbol = Symbol(
                name=func_name,
                kind=SymbolKind.FUNCTION,
                file=self.current_file,
                line=self._get_line_number(clean_content, match.start()),
                docstring=docstring,
                signature=signature,
            )
            
            self._add_symbol(symbol)
            
            # Collect calls
            func_body = self._extract_block(clean_content, match.end())
            self._collect_calls(func_body, symbol.id)
        
        # Arrow functions
        for match in self.PATTERNS['arrow_function'].finditer(clean_content):
            func_name = match.group(1)
            
            docstring = self._get_docstring_before(original_content, match.start())
            
            symbol = Symbol(
                name=func_name,
                kind=SymbolKind.FUNCTION,
                file=self.current_file,
                line=self._get_line_number(clean_content, match.start()),
                docstring=docstring,
            )
            
            self._add_symbol(symbol)
    
    def _parse_interfaces(self, clean_content: str, original_content: str):
        """Parse TypeScript interface definitions."""
        for match in self.PATTERNS['interface'].finditer(clean_content):
            interface_name = match.group(1)
            extends = match.group(2)
            
            docstring = self._get_docstring_before(original_content, match.start())
            
            symbol = Symbol(
                name=interface_name,
                kind=SymbolKind.INTERFACE,
                file=self.current_file,
                line=self._get_line_number(clean_content, match.start()),
                docstring=docstring,
                bases=[extends] if extends else [],
            )
            
            self._add_symbol(symbol)
    
    def _parse_exports(self, clean_content: str, original_content: str):
        """Parse export statements."""
        for match in self.PATTERNS['export'].finditer(clean_content):
            name = match.group(1)
            # Mark as exported in metadata
            for sym in self.symbols:
                if sym.name == name:
                    sym.metadata['exported'] = True
    
    def _collect_calls(self, body: str, caller_id: str):
        """Collect function calls from code body."""
        for match in self.PATTERNS['call'].finditer(body):
            call_name = match.group(1)
            
            # Skip common keywords
            if call_name in ('if', 'for', 'while', 'switch', 'catch', 'function', 'class', 'return', 'console', 'Math', 'JSON', 'Object', 'Array', 'String', 'Number', 'Boolean'):
                continue
            
            self._add_edge(Edge(
                source=caller_id,
                target=f"function:{call_name}",
                edge_type="calls",
                file=self.current_file,
                line=self._get_line_number(body, match.start()),
            ))
    
    def _extract_block(self, content: str, start: int) -> str:
        """Extract a code block (between { and })."""
        brace_count = 0
        block_start = -1
        in_string = False
        string_char = None
        
        for i, char in enumerate(content[start:], start):
            if char in ('"', "'", '`') and (i == 0 or content[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
            elif not in_string:
                if char == '{':
                    if brace_count == 0:
                        block_start = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and block_start >= 0:
                        return content[block_start+1:i]
        
        return ""
    
    def _get_line_number(self, content: str, pos: int) -> int:
        """Get line number for a position."""
        return content[:pos].count('\n') + 1
    
    def _get_docstring_before(self, content: str, pos: int) -> Optional[str]:
        """Get JSDoc comment before a position."""
        # Look for JSDoc comment before the position
        before = content[:pos].rstrip()
        
        match = self.PATTERNS['docstring'].search(before[-500:] if len(before) > 500 else before)
        if match:
            doc = match.group(0)
            # Clean up JSDoc format
            doc = re.sub(r'/\*\*|\*/|\s*\*\s?', ' ', doc)
            return doc.strip()
        
        return None
