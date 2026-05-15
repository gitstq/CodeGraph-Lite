"""
CodeGraph-Lite: Lightweight Terminal Code Knowledge Graph Engine
轻量级终端代码知识图谱引擎

A zero-dependency Python tool for building semantic code knowledge graphs.
"""

__version__ = "1.0.0"
__author__ = "CodeGraph-Lite Team"
__description__ = "Lightweight Terminal Code Knowledge Graph Engine"

from .cli import main
from .graph.database import GraphDatabase
from .graph.builder import GraphBuilder
from .search.engine import SearchEngine
from .analysis.impact import ImpactAnalyzer
from .analysis.context import ContextBuilder

__all__ = [
    "main",
    "GraphDatabase",
    "GraphBuilder",
    "SearchEngine",
    "ImpactAnalyzer",
    "ContextBuilder",
]
