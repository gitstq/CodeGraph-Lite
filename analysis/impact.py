"""
Impact Analyzer - Analyzes the impact of code changes.
"""

from typing import List, Dict, Any, Set, Tuple
from collections import deque

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.database import GraphDatabase


class ImpactAnalyzer:
    """Analyzes the impact of code changes on the codebase."""
    
    def __init__(self, db: GraphDatabase):
        """Initialize the impact analyzer."""
        self.db = db
    
    def find_callers(self, symbol_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Find all direct callers of a symbol."""
        symbols = self.db.get_node_by_name(symbol_name)
        
        all_callers = []
        seen = set()
        
        for symbol in symbols:
            callers = self.db.get_callers(symbol['id'])
            for caller in callers:
                if caller['symbol_id'] not in seen:
                    seen.add(caller['symbol_id'])
                    all_callers.append(caller)
        
        return all_callers[:limit]
    
    def find_callees(self, symbol_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Find all direct callees of a symbol."""
        symbols = self.db.get_node_by_name(symbol_name)
        
        all_callees = []
        seen = set()
        
        for symbol in symbols:
            callees = self.db.get_callees(symbol['id'])
            for callee in callees:
                if callee['symbol_id'] not in seen:
                    seen.add(callee['symbol_id'])
                    all_callees.append(callee)
        
        return all_callees[:limit]
    
    def analyze_impact(self, symbol_name: str, depth: int = 3) -> Dict[str, Any]:
        """
        Analyze the full impact of changing a symbol.
        
        Args:
            symbol_name: Name of the symbol to analyze
            depth: Maximum depth for transitive analysis
            
        Returns:
            Impact analysis results
        """
        symbols = self.db.get_node_by_name(symbol_name)
        
        if not symbols:
            return {
                'symbol': symbol_name,
                'found': False,
                'direct_callers': [],
                'transitive_callers': [],
                'total_affected': 0,
                'risk_level': 'unknown',
            }
        
        # Collect all callers
        direct_callers = []
        transitive_callers = []
        all_affected: Set[str] = set()
        
        for symbol in symbols:
            # Get direct callers
            callers = self.db.get_callers(symbol['id'])
            for caller in callers:
                if caller['symbol_id'] not in all_affected:
                    all_affected.add(caller['symbol_id'])
                    direct_callers.append(caller)
            
            # Get transitive callers (BFS)
            self._find_transitive_callers(symbol['id'], depth, all_affected, transitive_callers)
        
        # Calculate risk level
        total_affected = len(all_affected)
        risk_level = self._calculate_risk_level(total_affected, len(direct_callers))
        
        return {
            'symbol': symbol_name,
            'found': True,
            'symbols': [s['id'] for s in symbols],
            'direct_callers': direct_callers[:20],
            'transitive_callers': transitive_callers[:20],
            'total_affected': total_affected,
            'direct_count': len(direct_callers),
            'transitive_count': len(transitive_callers),
            'risk_level': risk_level,
            'depth': depth,
        }
    
    def _find_transitive_callers(self, symbol_id: str, max_depth: int,
                                   all_affected: Set[str], result: List[Dict[str, Any]]):
        """Find transitive callers using BFS."""
        queue = deque([(symbol_id, 0)])
        visited = {symbol_id}
        
        while queue:
            current_id, current_depth = queue.popleft()
            
            if current_depth >= max_depth:
                continue
            
            callers = self.db.get_callers(current_id)
            
            for caller in callers:
                caller_id = caller['symbol_id']
                
                if caller_id not in visited:
                    visited.add(caller_id)
                    
                    if caller_id not in all_affected:
                        all_affected.add(caller_id)
                        caller['depth'] = current_depth + 1
                        result.append(caller)
                    
                    queue.append((caller_id, current_depth + 1))
    
    def _calculate_risk_level(self, total_affected: int, direct_count: int) -> str:
        """Calculate risk level based on impact."""
        if total_affected == 0:
            return 'low'
        elif total_affected <= 3:
            return 'low'
        elif total_affected <= 10:
            return 'medium'
        elif total_affected <= 30:
            return 'high'
        else:
            return 'critical'
    
    def find_dependencies(self, symbol_name: str) -> Dict[str, Any]:
        """Find all dependencies of a symbol."""
        symbols = self.db.get_node_by_name(symbol_name)
        
        if not symbols:
            return {'symbol': symbol_name, 'found': False}
        
        all_deps = {
            'imports': [],
            'calls': [],
            'extends': [],
            'implements': [],
        }
        
        for symbol in symbols:
            # Get edges from this symbol
            edges = self.db.get_edges_from(symbol['id'])
            
            for edge in edges:
                edge_type = edge['edge_type']
                target = edge['target_id']
                
                if edge_type in all_deps:
                    # Try to resolve target name
                    target_node = self.db.get_node(target)
                    if target_node:
                        all_deps[edge_type].append({
                            'name': target_node['name'],
                            'symbol_id': target,
                            'file': target_node['file'],
                        })
                    else:
                        all_deps[edge_type].append({
                            'name': target.split(':')[-1] if ':' in target else target,
                            'symbol_id': target,
                        })
        
        return {
            'symbol': symbol_name,
            'found': True,
            **all_deps,
        }
    
    def find_dependents(self, symbol_name: str) -> Dict[str, Any]:
        """Find all dependents of a symbol (who depends on it)."""
        symbols = self.db.get_node_by_name(symbol_name)
        
        if not symbols:
            return {'symbol': symbol_name, 'found': False}
        
        all_dependents = {
            'imported_by': [],
            'called_by': [],
            'extended_by': [],
            'implemented_by': [],
        }
        
        for symbol in symbols:
            # Get edges to this symbol
            edges = self.db.get_edges_to(symbol['id'])
            
            for edge in edges:
                edge_type = edge['edge_type']
                source = edge['source_id']
                
                # Map edge types to dependent types
                dep_type_map = {
                    'calls': 'called_by',
                    'imports': 'imported_by',
                    'extends': 'extended_by',
                    'implements': 'implemented_by',
                }
                
                dep_type = dep_type_map.get(edge_type)
                if dep_type and dep_type in all_dependents:
                    source_node = self.db.get_node(source)
                    if source_node:
                        all_dependents[dep_type].append({
                            'name': source_node['name'],
                            'symbol_id': source,
                            'file': source_node['file'],
                        })
        
        return {
            'symbol': symbol_name,
            'found': True,
            **all_dependents,
        }
    
    def get_change_set(self, symbol_names: List[str]) -> Dict[str, Any]:
        """Get the combined change set for multiple symbols."""
        combined_affected: Set[str] = set()
        details = {}
        
        for name in symbol_names:
            impact = self.analyze_impact(name)
            details[name] = impact
            
            if impact['found']:
                for caller in impact['direct_callers']:
                    combined_affected.add(caller['symbol_id'])
                for caller in impact['transitive_callers']:
                    combined_affected.add(caller['symbol_id'])
        
        return {
            'symbols': symbol_names,
            'total_affected': len(combined_affected),
            'affected_ids': list(combined_affected),
            'details': details,
        }
