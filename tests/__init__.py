"""Tests for CodeGraph-Lite."""

import unittest
import tempfile
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from codegraph_lite.parser.python_parser import PythonParser
from codegraph_lite.parser.js_parser import JavaScriptParser
from codegraph_lite.graph.database import GraphDatabase


class TestPythonParser(unittest.TestCase):
    """Test Python parser."""
    
    def setUp(self):
        self.parser = PythonParser()
    
    def test_parse_function(self):
        """Test parsing a simple function."""
        code = '''
def hello_world(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"
'''
        symbols = self.parser.parse(code, "test.py")
        
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].name, "hello_world")
        self.assertEqual(symbols[0].kind.value, "function")
        self.assertEqual(symbols[0].docstring, "Say hello.")
    
    def test_parse_class(self):
        """Test parsing a class."""
        code = '''
class UserService:
    """User service class."""
    
    def __init__(self, db):
        self.db = db
    
    def get_user(self, user_id):
        return self.db.query(User).get(user_id)
'''
        symbols = self.parser.parse(code, "test.py")
        
        # Should have class and methods
        self.assertTrue(any(s.name == "UserService" and s.kind.value == "class" for s in symbols))
        self.assertTrue(any(s.name == "__init__" and s.kind.value == "method" for s in symbols))
        self.assertTrue(any(s.name == "get_user" and s.kind.value == "method" for s in symbols))
    
    def test_parse_decorators(self):
        """Test parsing decorators."""
        code = '''
@app.route("/api")
@cache.memoize(timeout=60)
def api_endpoint():
    return {"status": "ok"}
'''
        symbols = self.parser.parse(code, "test.py")
        
        self.assertEqual(len(symbols), 1)
        self.assertIn("app.route", symbols[0].decorators)
        self.assertIn("cache.memoize", symbols[0].decorators)


class TestJavaScriptParser(unittest.TestCase):
    """Test JavaScript parser."""
    
    def setUp(self):
        self.parser = JavaScriptParser()
    
    def test_parse_function(self):
        """Test parsing a JavaScript function."""
        code = '''
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}
'''
        symbols = self.parser.parse(code, "test.js")
        
        self.assertTrue(any(s.name == "calculateTotal" and s.kind.value == "function" for s in symbols))
    
    def test_parse_class(self):
        """Test parsing a JavaScript class."""
        code = '''
class UserService {
    constructor(api) {
        this.api = api;
    }
    
    async getUser(id) {
        return this.api.get(`/users/${id}`);
    }
}
'''
        symbols = self.parser.parse(code, "test.js")
        
        self.assertTrue(any(s.name == "UserService" and s.kind.value == "class" for s in symbols))
    
    def test_parse_arrow_function(self):
        """Test parsing arrow functions."""
        code = '''
const fetchData = async (url) => {
    const response = await fetch(url);
    return response.json();
};
'''
        symbols = self.parser.parse(code, "test.js")
        
        self.assertTrue(any(s.name == "fetchData" for s in symbols))


class TestGraphDatabase(unittest.TestCase):
    """Test graph database."""
    
    def setUp(self):
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = GraphDatabase(self.db_path)
        self.db.initialize()
    
    def tearDown(self):
        self.db.close()
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_add_file(self):
        """Test adding a file."""
        file_id = self.db.add_file("test.py", "Python", "abc123", 100)
        
        self.assertIsNotNone(file_id)
        self.assertEqual(self.db.get_file_id("test.py"), file_id)
    
    def test_add_node(self):
        """Test adding a node."""
        file_id = self.db.add_file("test.py", "Python")
        
        symbol = {
            'name': 'test_func',
            'kind': 'function',
            'file': 'test.py',
            'line': 10,
            'docstring': 'Test function',
        }
        
        node_id = self.db.add_node(symbol, file_id)
        self.assertIsNotNone(node_id)
        
        # Retrieve node
        nodes = self.db.get_node_by_name('test_func')
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], 'test_func')
    
    def test_add_edge(self):
        """Test adding an edge."""
        file_id = self.db.add_file("test.py", "Python")
        
        symbol1 = {'name': 'func1', 'kind': 'function', 'file': 'test.py', 'line': 1}
        symbol2 = {'name': 'func2', 'kind': 'function', 'file': 'test.py', 'line': 10}
        
        self.db.add_node(symbol1, file_id)
        self.db.add_node(symbol2, file_id)
        
        self.db.add_edge(
            "function:test.py:func1:1",
            "function:test.py:func2:10",
            "calls",
            file_id,
            5
        )
        
        edges = self.db.get_edges_from("function:test.py:func1:1")
        self.assertEqual(len(edges), 1)
    
    def test_get_stats(self):
        """Test getting statistics."""
        file_id = self.db.add_file("test.py", "Python")
        
        for i in range(5):
            self.db.add_node({
                'name': f'func{i}',
                'kind': 'function',
                'file': 'test.py',
                'line': i * 10,
            }, file_id)
        
        stats = self.db.get_stats()
        
        self.assertEqual(stats['files'], 1)
        self.assertEqual(stats['nodes'], 5)


if __name__ == '__main__':
    unittest.main()
