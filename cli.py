import asyncio
import json
import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.models import ScenarioConfig
from core.engine import SiteTesterEngine
from core.reporter import Reporter

console = Console()

async def run_scenario_file(file_path: str, headless: bool = True):
    if not os.path.exists(file_path):
        console.print(f"[bold red]錯誤:[/bold red] 找不到情境檔案 '{file_path}'")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenario = ScenarioConfig(**data)
    scenario.headless = headless

    console.print(Panel(
        f"[bold cyan]情境名稱:[/bold cyan] {scenario.title}\n"
        f"[bold cyan]目標網址:[/bold cyan] {scenario.target_url}\n"
        f"[bold cyan]步驟數量:[/bold cyan] {len(scenario.steps)} 個步驟",
        title="[bold yellow]網站測試啟動[/bold yellow]",
        expand=False
    ))

    engine = SiteTesterEngine(output_dir="reports")
    reporter = Reporter(output_dir="reports")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[yellow]正在執行測試步驟...", total=len(scenario.steps))

        async def step_cb(step_id, res):
            status_str = "[green]✓ 成功[/green]" if res.success else f"[red]✗ 失敗 ({res.error_message})[/red]"
            progress.console.print(f"  • {res.step_name} [{res.action}] -> {status_str} ({res.duration_ms} ms)")
            progress.advance(task)

        result = await engine.run_scenario(scenario, progress_callback=step_cb)

    # Print summary table
    table = Table(title=f"測試結果總覽 - {result.scenario_title}")
    table.add_column("指標", style="cyan")
    table.add_column("數值", style="bold")

    status_colored = "[bold green]PASS (通過)[/bold green]" if result.passed else "[bold red]FAIL (未通過)[/bold red]"
    table.add_row("最終結果", status_colored)
    table.add_row("總耗時", f"{result.duration_ms} ms")
    table.add_row("成功 / 總步驟", f"{result.passed_steps} / {result.total_steps}")
    table.add_row("JS Console 警報數", str(len(result.console_errors)))
    table.add_row("Network 失敗請求數", str(len(result.network_errors)))

    console.print(table)

    # Generate Reports
    json_path = reporter.save_json(result)
    html_path = reporter.generate_html(result)

    console.print(f"\n[bold green]✓ 測試報告已產出:[/bold green]")
    console.print(f"  • HTML 報告: [link={html_path}]{html_path}[/link]")
    console.print(f"  • JSON 資料: [link={json_path}]{json_path}[/link]")

def main():
    if len(sys.argv) < 2:
        console.print("[bold yellow]使用說明:[/bold yellow]")
        console.print("  python cli.py <scenario_file.json> [--headed]")
        console.print("  python cli.py list")
        return

    cmd = sys.argv[1]
    if cmd == "list":
        console.print("[bold cyan]現有範例情境檔:[/bold cyan]")
        scenarios_dir = "scenarios"
        if os.path.exists(scenarios_dir):
            for fname in os.listdir(scenarios_dir):
                if fname.endswith(".json"):
                    console.print(f"  • scenarios/{fname}")
        return

    headed = "--headed" in sys.argv
    asyncio.run(run_scenario_file(cmd, headless=not headed))

if __name__ == "__main__":
    main()
