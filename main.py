import asyncio
import typer
import httpx
from rich.console import Console
from rich.prompt import IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Dict, List
import sys
import os
import json

app = typer.Typer()
console = Console()

BASE_URL = "http://localhost:8000"


async def fetch_leaderboards() -> Dict:
    """Fetch available leaderboards from the API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/leaderboards")
        if response.status_code != 200:
            console.print("[red]Failed to fetch leaderboards[/red]")
            sys.exit(1)
        return response.json()


async def fetch_available_gpus(leaderboard: str, runner: str) -> List[str]:
    """Fetch available GPUs for the given leaderboard and runner"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/{leaderboard}/{runner}/gpus")
        if response.status_code != 200:
            console.print("[red]Failed to fetch GPUs[/red]")
            sys.exit(1)
        return response.json()


async def submit_solution(
    leaderboard: str, runner: str, gpu: str, filepath: str
):
    """Submit a solution to a leaderboard"""
    with open(filepath, "r") as f:
        solution_content = f.read()

    filename = os.path.basename(filepath)

    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            f"{BASE_URL}/{leaderboard}/{runner}/{gpu}",
            files={"file": (filename, solution_content)},
            timeout=600.0,
        )
        if response.status_code != 200:
            console.print("[red]Failed to submit solution[/red]")
            return None

        return response.json()


@app.command()
def submit(
    filepath: str = typer.Argument(..., help="Path to the solution file to submit"),
):
    """Submit a solution file to a leaderboard"""
    asyncio.run(_submit(filepath))


async def _submit(filepath: str):
    """Async implementation of submit command"""
    try:
        if not os.path.exists(filepath):
            console.print(f"[red]Error: File '{filepath}' not found[/red]")
            sys.exit(1)


        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(
                description="Fetching available leaderboards...", total=None
            )
            leaderboards = await fetch_leaderboards()
            leaderboard_names = [x["name"] for x in leaderboards]

        console.print("\n[bold blue]Available Leaderboards:[/bold blue]")
        for idx, name in enumerate(leaderboard_names, 1):
            console.print(f"{idx}. {name}")

        leaderboard_idx = IntPrompt.ask(
            "\nSelect leaderboard number",
            choices=[str(i) for i in range(1, len(leaderboard_names) + 1)],
        )
        selected_leaderboard = leaderboard_names[leaderboard_idx - 1]

        runners = ["modal", "github"]
        console.print("\n[bold blue]Available Runners:[/bold blue]")
        for idx, runner in enumerate(runners, 1):
            console.print(f"{idx}. {runner}")

        runner_idx = IntPrompt.ask("\nSelect runner number", choices=["1", "2"])
        selected_runner = runners[runner_idx - 1]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Fetching available GPUs...", total=None)
            gpus = await fetch_available_gpus(selected_leaderboard, selected_runner)

        # Get GPU selection
        console.print("\n[bold blue]Available GPUs:[/bold blue]")
        for idx, gpu in enumerate(gpus, 1):
            console.print(f"{idx}. {gpu}")

        gpu_idx = IntPrompt.ask(
            "\nSelect GPU number", choices=[str(i) for i in range(1, len(gpus) + 1)]
        )
        selected_gpu = gpus[gpu_idx - 1]

        selected_leaderboard = selected_leaderboard.lower()
        selected_runner = selected_runner.lower()
        selected_gpu = selected_gpu.lower()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Submitting solution...", total=None)
            result = await submit_solution(
                selected_leaderboard, selected_runner, selected_gpu, filepath
            )

        if result is None:
            console.print("[red]Failed to submit solution[/red]")
            return

        formatted_result = json.dumps(result, indent=2)
        console.print("\n[bold blue]Result:[/bold blue]")
        console.print(formatted_result)

        console.print("[green]Solution submitted successfully![/green]")

    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        sys.exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
