#!/usr/bin/env python3
"""
CodeGraph-Lite CLI Entry Point
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.database import GraphDatabase
from graph.builder import GraphBuilder
from search.engine import SearchEngine
from analysis.impact import ImpactAnalyzer
from analysis.context import ContextBuilder
from tui.dashboard import run_dashboard


def cmd_init(args):
    """Initialize CodeGraph in a project directory."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if codegraph_dir.exists() and not args.force:
        print(f"❌ CodeGraph already initialized at {codegraph_dir}")
        print("   Use --force to reinitialize")
        return 1
    
    codegraph_dir.mkdir(exist_ok=True)
    
    # Initialize database
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    db.initialize()
    
    print(f"✅ CodeGraph initialized at {codegraph_dir}")
    print(f"   Database: {codegraph_dir / 'codegraph.db'}")
    
    if args.index:
        print("\n📊 Indexing project...")
        builder = GraphBuilder(db)
        stats = builder.build(str(path))
        print(f"   Files indexed: {stats['files']}")
        print(f"   Nodes created: {stats['nodes']}")
        print(f"   Edges created: {stats['edges']}")
    
    return 0


def cmd_index(args):
    """Index all files in the project."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    builder = GraphBuilder(db)
    
    print(f"📊 Indexing {path}...")
    stats = builder.build(str(path), force=args.force)
    
    print(f"\n✅ Indexing complete!")
    print(f"   Files indexed: {stats['files']}")
    print(f"   Nodes created: {stats['nodes']}")
    print(f"   Edges created: {stats['edges']}")
    print(f"   Time: {stats['time']:.2f}s")
    
    return 0


def cmd_query(args):
    """Search for symbols in the codebase."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    search = SearchEngine(db)
    
    results = search.search(args.query, kind=args.kind, limit=args.limit)
    
    if not results:
        print(f"🔍 No results found for '{args.query}'")
        return 0
    
    print(f"🔍 Found {len(results)} results for '{args.query}':\n")
    
    for i, result in enumerate(results, 1):
        print(f"  {i}. [{result['kind']}] {result['name']}")
        print(f"     📁 {result['file']}:{result['line']}")
        if result.get('docstring'):
            print(f"     💬 {result['docstring'][:60]}...")
        print()
    
    return 0


def cmd_context(args):
    """Build context for a specific task."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    builder = ContextBuilder(db)
    
    print(f"🤖 Building context for: {args.task}\n")
    
    context = builder.build(args.task, max_nodes=args.max_nodes)
    
    print(f"📋 Context Summary:")
    print(f"   Entry points: {len(context['entry_points'])}")
    print(f"   Related symbols: {len(context['related'])}")
    print(f"   Code snippets: {len(context['snippets'])}")
    
    if context['entry_points']:
        print(f"\n🎯 Entry Points:")
        for ep in context['entry_points'][:5]:
            print(f"   • {ep['name']} ({ep['kind']}) - {ep['file']}:{ep['line']}")
    
    if context['related']:
        print(f"\n🔗 Related Symbols:")
        for r in context['related'][:10]:
            print(f"   • {r['name']} ({r['kind']})")
    
    return 0


def cmd_callers(args):
    """Find what calls a function."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    analyzer = ImpactAnalyzer(db)
    
    callers = analyzer.find_callers(args.symbol, limit=args.limit)
    
    if not callers:
        print(f"📞 No callers found for '{args.symbol}'")
        return 0
    
    print(f"📞 Callers of '{args.symbol}' ({len(callers)}):\n")
    
    for i, caller in enumerate(callers, 1):
        print(f"  {i}. {caller['name']} ({caller['kind']})")
        print(f"     📁 {caller['file']}:{caller['line']}")
    
    return 0


def cmd_callees(args):
    """Find what a function calls."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    analyzer = ImpactAnalyzer(db)
    
    callees = analyzer.find_callees(args.symbol, limit=args.limit)
    
    if not callees:
        print(f"📱 No callees found for '{args.symbol}'")
        return 0
    
    print(f"📱 Callees of '{args.symbol}' ({len(callees)}):\n")
    
    for i, callee in enumerate(callees, 1):
        print(f"  {i}. {callee['name']} ({callee['kind']})")
        print(f"     📁 {callee['file']}:{callee['line']}")
    
    return 0


def cmd_impact(args):
    """Analyze what code would be affected by changing a symbol."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    analyzer = ImpactAnalyzer(db)
    
    print(f"💥 Impact analysis for '{args.symbol}':\n")
    
    impact = analyzer.analyze_impact(args.symbol, depth=args.depth)
    
    print(f"📊 Impact Summary:")
    print(f"   Direct callers: {len(impact['direct_callers'])}")
    print(f"   Transitive callers: {len(impact['transitive_callers'])}")
    print(f"   Total affected: {impact['total_affected']}")
    print(f"   Risk level: {impact['risk_level']}")
    
    if impact['direct_callers']:
        print(f"\n🎯 Direct Callers:")
        for caller in impact['direct_callers'][:5]:
            print(f"   • {caller['name']} - {caller['file']}:{caller['line']}")
    
    return 0


def cmd_status(args):
    """Show index status and statistics."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    stats = db.get_stats()
    
    print("📊 CodeGraph Status\n")
    print(f"  📁 Project: {path}")
    print(f"  💾 Database: {codegraph_dir / 'codegraph.db'}")
    print(f"\n  📈 Statistics:")
    print(f"     Files indexed: {stats['files']}")
    print(f"     Total nodes: {stats['nodes']}")
    print(f"     Total edges: {stats['edges']}")
    
    if stats.get('nodes_by_kind'):
        print(f"\n  🏷️ Nodes by Kind:")
        for kind, count in sorted(stats['nodes_by_kind'].items(), key=lambda x: -x[1]):
            print(f"     • {kind}: {count}")
    
    if stats.get('files_by_lang'):
        print(f"\n  💻 Files by Language:")
        for lang, count in sorted(stats['files_by_lang'].items(), key=lambda x: -x[1]):
            print(f"     • {lang}: {count}")
    
    return 0


def cmd_tui(args):
    """Launch TUI dashboard."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    run_dashboard(str(codegraph_dir / "codegraph.db"), str(path))
    return 0


def cmd_export(args):
    """Export graph to various formats."""
    path = Path(args.path) if args.path else Path.cwd()
    codegraph_dir = path / ".codegraph"
    
    if not codegraph_dir.exists():
        print(f"❌ CodeGraph not initialized. Run 'codegraph init' first.")
        return 1
    
    db = GraphDatabase(str(codegraph_dir / "codegraph.db"))
    output_path = args.output or f"codegraph_export.{args.format}"
    
    if args.format == "json":
        data = db.export_json()
        with open(output_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(data, f, indent=2, ensure_ascii=False)
    elif args.format == "html":
        from utils.helpers import generate_html_report
        generate_html_report(db, output_path)
    elif args.format == "markdown":
        from utils.helpers import generate_markdown_report
        generate_markdown_report(db, output_path)
    else:
        print(f"❌ Unknown format: {args.format}")
        return 1
    
    print(f"✅ Exported to {output_path}")
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="codegraph",
        description="🔮 CodeGraph-Lite - Lightweight Terminal Code Knowledge Graph Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codegraph init                  Initialize in current directory
  codegraph init --index          Initialize and index immediately
  codegraph index                 Index all files
  codegraph query "authenticate"  Search for symbols
  codegraph context "fix login"   Build context for a task
  codegraph callers "UserService" Find callers of a symbol
  codegraph impact "processOrder" Analyze change impact
  codegraph tui                   Launch TUI dashboard
  codegraph export --format html  Export to HTML
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init command
    init_parser = subparsers.add_parser("init", help="Initialize CodeGraph in a project")
    init_parser.add_argument("path", nargs="?", help="Project path")
    init_parser.add_argument("--force", "-f", action="store_true", help="Force reinitialize")
    init_parser.add_argument("--index", "-i", action="store_true", help="Index after init")
    
    # index command
    index_parser = subparsers.add_parser("index", help="Index all files in the project")
    index_parser.add_argument("path", nargs="?", help="Project path")
    index_parser.add_argument("--force", "-f", action="store_true", help="Force full re-index")
    
    # query command
    query_parser = subparsers.add_parser("query", help="Search for symbols")
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument("--kind", "-k", help="Filter by symbol kind (function, class, method)")
    query_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results")
    query_parser.add_argument("--path", "-p", help="Project path")
    
    # context command
    context_parser = subparsers.add_parser("context", help="Build context for a task")
    context_parser.add_argument("task", help="Task description")
    context_parser.add_argument("--max-nodes", "-m", type=int, default=30, help="Max nodes")
    context_parser.add_argument("--path", "-p", help="Project path")
    
    # callers command
    callers_parser = subparsers.add_parser("callers", help="Find callers of a symbol")
    callers_parser.add_argument("symbol", help="Symbol name")
    callers_parser.add_argument("--limit", "-l", type=int, default=50, help="Max results")
    callers_parser.add_argument("--path", "-p", help="Project path")
    
    # callees command
    callees_parser = subparsers.add_parser("callees", help="Find callees of a symbol")
    callees_parser.add_argument("symbol", help="Symbol name")
    callees_parser.add_argument("--limit", "-l", type=int, default=50, help="Max results")
    callees_parser.add_argument("--path", "-p", help="Project path")
    
    # impact command
    impact_parser = subparsers.add_parser("impact", help="Analyze change impact")
    impact_parser.add_argument("symbol", help="Symbol name")
    impact_parser.add_argument("--depth", "-d", type=int, default=3, help="Analysis depth")
    impact_parser.add_argument("--path", "-p", help="Project path")
    
    # status command
    status_parser = subparsers.add_parser("status", help="Show index status")
    status_parser.add_argument("path", nargs="?", help="Project path")
    
    # tui command
    tui_parser = subparsers.add_parser("tui", help="Launch TUI dashboard")
    tui_parser.add_argument("path", nargs="?", help="Project path")
    
    # export command
    export_parser = subparsers.add_parser("export", help="Export graph")
    export_parser.add_argument("--format", "-f", choices=["json", "html", "markdown"], default="json")
    export_parser.add_argument("--output", "-o", help="Output file path")
    export_parser.add_argument("--path", "-p", help="Project path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Dispatch to command handler
    commands = {
        "init": cmd_init,
        "index": cmd_index,
        "query": cmd_query,
        "context": cmd_context,
        "callers": cmd_callers,
        "callees": cmd_callees,
        "impact": cmd_impact,
        "status": cmd_status,
        "tui": cmd_tui,
        "export": cmd_export,
    }
    
    handler = commands.get(args.command)
    if handler:
        return handler(args)
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
