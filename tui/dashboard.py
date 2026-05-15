"""
TUI Dashboard - Rich-based terminal dashboard for CodeGraph.
"""

import time
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.prompt import Prompt, PromptType
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.database import GraphDatabase
from search.engine import SearchEngine
from analysis.impact import ImpactAnalyzer
from analysis.context import ContextBuilder


def run_dashboard(db_path: str, project_path: str):
    """Run the TUI dashboard."""
    if not RICH_AVAILABLE:
        print("❌ Rich library not installed. Install with: pip install rich")
        print("   Falling back to simple mode...")
        _run_simple_dashboard(db_path, project_path)
        return
    
    console = Console()
    
    # Connect to database
    db = GraphDatabase(db_path)
    db.connect()
    
    try:
        while True:
            console.clear()
            
            # Show header
            _show_header(console, project_path)
            
            # Show stats
            stats = db.get_stats()
            _show_stats(console, stats)
            
            # Show menu
            _show_menu(console)
            
            # Get user choice
            choice = Prompt.ask("\n[bold cyan]Enter command[/]", default="h")
            
            if choice.lower() == 'q':
                console.print("\n[yellow]Goodbye![/]")
                break
            elif choice.lower() == 'h':
                _show_help(console)
            elif choice.lower() == 's':
                _search_mode(console, db)
            elif choice.lower() == 'c':
                _context_mode(console, db)
            elif choice.lower() == 'i':
                _impact_mode(console, db)
            elif choice.lower() == 'x':
                _callers_mode(console, db)
            elif choice.lower() == 'e':
                _callees_mode(console, db)
            elif choice.lower() == 'f':
                _file_mode(console, db)
            else:
                console.print(f"\n[red]Unknown command: {choice}[/]")
                time.sleep(1)
    
    finally:
        db.close()


def _run_simple_dashboard(db_path: str, project_path: str):
    """Simple text-based dashboard fallback."""
    db = GraphDatabase(db_path)
    db.connect()
    
    try:
        while True:
            print("\n" + "=" * 60)
            print("🔮 CodeGraph-Lite Dashboard")
            print("=" * 60)
            print(f"Project: {project_path}")
            
            stats = db.get_stats()
            print(f"\n📊 Statistics:")
            print(f"   Files: {stats['files']}")
            print(f"   Nodes: {stats['nodes']}")
            print(f"   Edges: {stats['edges']}")
            
            print("\n📋 Commands:")
            print("  s - Search symbols")
            print("  c - Build context")
            print("  i - Impact analysis")
            print("  x - Find callers")
            print("  e - Find callees")
            print("  q - Quit")
            
            choice = input("\nEnter command: ").strip().lower()
            
            if choice == 'q':
                print("Goodbye!")
                break
            elif choice == 's':
                query = input("Search query: ").strip()
                results = db.search_nodes(query)
                print(f"\nFound {len(results)} results:")
                for r in results[:10]:
                    print(f"  [{r['kind']}] {r['name']} - {r['file']}:{r['line']}")
            elif choice == 'x':
                symbol = input("Symbol name: ").strip()
                analyzer = ImpactAnalyzer(db)
                callers = analyzer.find_callers(symbol)
                print(f"\nCallers of '{symbol}' ({len(callers)}):")
                for c in callers[:10]:
                    print(f"  {c['name']} - {c['file']}:{c['line']}")
            elif choice == 'e':
                symbol = input("Symbol name: ").strip()
                analyzer = ImpactAnalyzer(db)
                callees = analyzer.find_callees(symbol)
                print(f"\nCallees of '{symbol}' ({len(callees)}):")
                for c in callees[:10]:
                    print(f"  {c['name']} - {c.get('file', '?')}:{c.get('line', '?')}")
            
            input("\nPress Enter to continue...")
    
    finally:
        db.close()


def _show_header(console: Console, project_path: str):
    """Show dashboard header."""
    header = Panel(
        Text.from_markup(
            "[bold magenta]🔮 CodeGraph-Lite[/]\n"
            f"[dim]Project: {project_path}[/]"
        ),
        box=box.DOUBLE,
        style="bold blue",
    )
    console.print(header)


def _show_stats(console: Console, stats: Dict[str, Any]):
    """Show database statistics."""
    table = Table(title="📊 Statistics", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")
    
    table.add_row("Files", str(stats['files']))
    table.add_row("Nodes", str(stats['nodes']))
    table.add_row("Edges", str(stats['edges']))
    
    console.print(table)
    
    # Show nodes by kind
    if stats.get('nodes_by_kind'):
        kind_table = Table(title="🏷️ Nodes by Kind", box=box.SIMPLE)
        kind_table.add_column("Kind", style="yellow")
        kind_table.add_column("Count", style="green", justify="right")
        
        for kind, count in sorted(stats['nodes_by_kind'].items(), key=lambda x: -x[1])[:8]:
            kind_table.add_row(kind, str(count))
        
        console.print(kind_table)


def _show_menu(console: Console):
    """Show command menu."""
    menu = Panel(
        "[bold]Commands:[/]\n"
        "  [cyan]s[/] - Search symbols\n"
        "  [cyan]c[/] - Build context for task\n"
        "  [cyan]i[/] - Impact analysis\n"
        "  [cyan]x[/] - Find callers\n"
        "  [cyan]e[/] - Find callees\n"
        "  [cyan]f[/] - Browse file\n"
        "  [cyan]h[/] - Help\n"
        "  [cyan]q[/] - Quit",
        title="📋 Menu",
        box=box.ROUNDED,
    )
    console.print(menu)


def _show_help(console: Console):
    """Show help information."""
    help_text = Panel(
        "[bold]CodeGraph-Lite Help[/]\n\n"
        "[cyan]Search (s):[/] Find symbols by name or keyword\n"
        "  Example: 'authenticate', 'UserService', 'login'\n\n"
        "[cyan]Context (c):[/] Build AI context for a task\n"
        "  Example: 'fix login bug', 'add user validation'\n\n"
        "[cyan]Impact (i):[/] Analyze change impact\n"
        "  Shows who would be affected by changing a symbol\n\n"
        "[cyan]Callers (x):[/] Find who calls a function\n"
        "[cyan]Callees (e):[/] Find what a function calls\n\n"
        "[cyan]File (f):[/] Browse symbols in a file",
        title="❓ Help",
        box=box.ROUNDED,
    )
    console.print(help_text)
    Prompt.ask("\nPress Enter to continue")


def _search_mode(console: Console, db: GraphDatabase):
    """Interactive search mode."""
    query = Prompt.ask("[cyan]Search query[/]")
    
    if not query:
        return
    
    search = SearchEngine(db)
    results = search.search(query)
    
    if not results:
        console.print(f"\n[yellow]No results found for '{query}'[/]")
        Prompt.ask("Press Enter to continue")
        return
    
    table = Table(title=f"🔍 Results for '{query}'", box=box.ROUNDED)
    table.add_column("#", style="dim", width=3)
    table.add_column("Kind", style="yellow", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File", style="green")
    table.add_column("Line", style="magenta", justify="right")
    
    for i, r in enumerate(results[:20], 1):
        table.add_row(
            str(i),
            r['kind'],
            r['name'],
            r['file'],
            str(r['line']),
        )
    
    console.print(table)
    Prompt.ask("\nPress Enter to continue")


def _context_mode(console: Console, db: GraphDatabase):
    """Interactive context building mode."""
    task = Prompt.ask("[cyan]Task description[/]")
    
    if not task:
        return
    
    builder = ContextBuilder(db)
    context = builder.build(task)
    
    console.print(f"\n[bold]📋 Context for: {task}[/]")
    
    # Show entry points
    if context['entry_points']:
        console.print(f"\n[cyan]Entry Points ({len(context['entry_points'])}):[/]")
        for ep in context['entry_points'][:5]:
            console.print(f"  • [{ep['kind']}] {ep['name']} - {ep['file']}:{ep['line']}")
    
    # Show related symbols
    if context['related']:
        console.print(f"\n[cyan]Related Symbols ({len(context['related'])}):[/]")
        for r in context['related'][:10]:
            console.print(f"  • {r['name']} ({r.get('relation', 'related')})")
    
    Prompt.ask("\nPress Enter to continue")


def _impact_mode(console: Console, db: GraphDatabase):
    """Interactive impact analysis mode."""
    symbol = Prompt.ask("[cyan]Symbol name[/]")
    
    if not symbol:
        return
    
    analyzer = ImpactAnalyzer(db)
    impact = analyzer.analyze_impact(symbol)
    
    if not impact['found']:
        console.print(f"\n[yellow]Symbol '{symbol}' not found[/]")
        Prompt.ask("Press Enter to continue")
        return
    
    # Show impact summary
    console.print(f"\n[bold]💥 Impact Analysis for '{symbol}'[/]")
    
    risk_colors = {
        'low': 'green',
        'medium': 'yellow',
        'high': 'orange1',
        'critical': 'red',
    }
    risk_color = risk_colors.get(impact['risk_level'], 'white')
    
    console.print(f"\n  Risk Level: [{risk_color}]{impact['risk_level'].upper()}[/]")
    console.print(f"  Direct Callers: {impact['direct_count']}")
    console.print(f"  Transitive Callers: {impact['transitive_count']}")
    console.print(f"  Total Affected: {impact['total_affected']}")
    
    # Show direct callers
    if impact['direct_callers']:
        console.print(f"\n[cyan]Direct Callers:[/]")
        for c in impact['direct_callers'][:10]:
            console.print(f"  • {c['name']} - {c['file']}:{c['line']}")
    
    Prompt.ask("\nPress Enter to continue")


def _callers_mode(console: Console, db: GraphDatabase):
    """Interactive callers mode."""
    symbol = Prompt.ask("[cyan]Symbol name[/]")
    
    if not symbol:
        return
    
    analyzer = ImpactAnalyzer(db)
    callers = analyzer.find_callers(symbol)
    
    if not callers:
        console.print(f"\n[yellow]No callers found for '{symbol}'[/]")
        Prompt.ask("Press Enter to continue")
        return
    
    console.print(f"\n[bold]📞 Callers of '{symbol}' ({len(callers)}):[/]")
    
    for i, c in enumerate(callers[:20], 1):
        console.print(f"  {i}. [{c['kind']}] {c['name']} - {c['file']}:{c['line']}")
    
    Prompt.ask("\nPress Enter to continue")


def _callees_mode(console: Console, db: GraphDatabase):
    """Interactive callees mode."""
    symbol = Prompt.ask("[cyan]Symbol name[/]")
    
    if not symbol:
        return
    
    analyzer = ImpactAnalyzer(db)
    callees = analyzer.find_callees(symbol)
    
    if not callees:
        console.print(f"\n[yellow]No callees found for '{symbol}'[/]")
        Prompt.ask("Press Enter to continue")
        return
    
    console.print(f"\n[bold]📱 Callees of '{symbol}' ({len(callees)}):[/]")
    
    for i, c in enumerate(callees[:20], 1):
        console.print(f"  {i}. {c['name']} - {c.get('file', '?')}:{c.get('line', '?')}")
    
    Prompt.ask("\nPress Enter to continue")


def _file_mode(console: Console, db: GraphDatabase):
    """Interactive file browsing mode."""
    file_path = Prompt.ask("[cyan]File path (partial)[/]")
    
    if not file_path:
        return
    
    # Search for files
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT path FROM files WHERE path LIKE ? LIMIT 20
    """, (f'%{file_path}%',))
    
    files = [row['path'] for row in cursor.fetchall()]
    
    if not files:
        console.print(f"\n[yellow]No files found matching '{file_path}'[/]")
        Prompt.ask("Press Enter to continue")
        return
    
    if len(files) == 1:
        selected_file = files[0]
    else:
        console.print(f"\n[cyan]Found {len(files)} files:[/]")
        for i, f in enumerate(files, 1):
            console.print(f"  {i}. {f}")
        
        choice = Prompt.ask("Select file number", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                selected_file = files[idx]
            else:
                return
        except ValueError:
            return
    
    # Get symbols in file
    cursor.execute("""
        SELECT n.*, f.path as file_path
        FROM nodes n
        JOIN files f ON n.file_id = f.id
        WHERE f.path = ?
        ORDER BY n.line
    """, (selected_file,))
    
    symbols = [db._row_to_node(row) for row in cursor.fetchall()]
    
    console.print(f"\n[bold]📄 File: {selected_file}[/]")
    console.print(f"[dim]{len(symbols)} symbols[/]\n")
    
    for sym in symbols[:30]:
        console.print(f"  [{sym['kind']}] {sym['name']} :{sym['line']}")
    
    Prompt.ask("\nPress Enter to continue")
