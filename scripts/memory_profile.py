#!/usr/bin/env python3
"""
Memory profiling script for AniVault CLI.
Compares memory usage between legacy and Typer CLI implementations.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import psutil


def run_command_and_profile(name: str, command: list[str]) -> dict:
    """Runs a command, profiles its memory and time, and returns results."""
    print(f"Profiling {name}...")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    max_memory_rss = 0
    start_time = time.perf_counter()

    try:
        # Monitor memory usage
        proc = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                mem_info = proc.memory_info()
                max_memory_rss = max(max_memory_rss, mem_info.rss)
            except psutil.NoSuchProcess:
                break
            time.sleep(0.01)  # Sample every 10ms

        # Get final memory info after process exits
        try:
            mem_info = proc.memory_info()
            max_memory_rss = max(max_memory_rss, mem_info.rss)
        except psutil.NoSuchProcess:
            pass

        stdout, stderr = process.communicate(timeout=30)
        end_time = time.perf_counter()
        duration = end_time - start_time

        print(f"✓ {name}")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Max Memory: {max_memory_rss / (1024 * 1024):.2f} MB")
        print(f"  Exit Code: {process.returncode}")

        return {
            "name": name,
            "command": " ".join(command),
            "exit_code": process.returncode,
            "duration": duration,
            "max_memory_rss": max_memory_rss,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        print(f"✗ {name} (Timeout)")
        return {
            "name": name,
            "command": " ".join(command),
            "exit_code": -1,  # Indicate timeout
            "duration": time.perf_counter() - start_time,
            "max_memory_rss": max_memory_rss,
            "stdout": stdout,
            "stderr": stderr,
            "error": "TimeoutExpired",
        }
    except Exception as e:
        print(f"✗ {name} (Error: {e})")
        return {
            "name": name,
            "command": " ".join(command),
            "exit_code": -1,
            "duration": time.perf_counter() - start_time,
            "max_memory_rss": max_memory_rss,
            "stdout": "",
            "stderr": str(e),
            "error": str(e),
        }


def main():
    """Main profiling function."""
    print("AniVault CLI Memory Profiling")
    print("=" * 50)

    # Define commands to profile
    commands = [
        {
            "name": "Current CLI (--version)",
            "command": [sys.executable, "-m", "anivault", "--version"],
        },
        {
            "name": "Typer CLI (--version)",
            "command": [sys.executable, "-m", "anivault.cli.typer_app", "--version"],
        },
        {
            "name": "Current CLI (--help)",
            "command": [sys.executable, "-m", "anivault", "--help"],
        },
        {
            "name": "Typer CLI (--help)",
            "command": [sys.executable, "-m", "anivault.cli.typer_app", "--help"],
        },
    ]

    results = []

    # Profile each command
    for cmd_info in commands:
        results.append(run_command_and_profile(cmd_info["name"], cmd_info["command"]))

    # Generate comparison report
    print("\nMemory Usage Comparison")
    print("=" * 50)

    if (
        len(results) >= 2
    ):  # Changed from 4 to 2 to handle cases where not all commands are found
        # Compare version commands
        current_version = next(
            (r for r in results if "Current" in r["name"] and "version" in r["name"]),
            None,
        )
        typer_version = next(
            (r for r in results if "Typer" in r["name"] and "version" in r["name"]),
            None,
        )

        if current_version and typer_version:
            print("Version Command Comparison:")
            print(
                f"  Current: {current_version['max_memory_rss'] / 1024 / 1024:.2f} MB",
            )
            print(f"  Typer:   {typer_version['max_memory_rss'] / 1024 / 1024:.2f} MB")

            memory_diff = (
                typer_version["max_memory_rss"] - current_version["max_memory_rss"]
            )
            memory_diff_percent = (
                memory_diff / current_version["max_memory_rss"]
            ) * 100

            print(
                f"  Difference: {memory_diff / 1024 / 1024:.2f} MB ({memory_diff_percent:+.1f}%)",
            )

            if memory_diff_percent > 10:
                print("  ⚠️  WARNING: Memory usage increased by more than 10%")
            else:
                print("  ✓ Memory usage within acceptable limits")
            print()

        # Compare help commands
        current_help = next(
            (r for r in results if "Current" in r["name"] and "help" in r["name"]),
            None,
        )
        typer_help = next(
            (r for r in results if "Typer" in r["name"] and "help" in r["name"]),
            None,
        )

        if current_help and typer_help:
            print("Help Command Comparison:")
            print(f"  Current: {current_help['max_memory_rss'] / 1024 / 1024:.2f} MB")
            print(f"  Typer:   {typer_help['max_memory_rss'] / 1024 / 1024:.2f} MB")

            memory_diff = typer_help["max_memory_rss"] - current_help["max_memory_rss"]
            memory_diff_percent = (memory_diff / current_help["max_memory_rss"]) * 100

            print(
                f"  Difference: {memory_diff / 1024 / 1024:.2f} MB ({memory_diff_percent:+.1f}%)",
            )

            if memory_diff_percent > 10:
                print("  ⚠️  WARNING: Memory usage increased by more than 10%")
            else:
                print("  ✓ Memory usage within acceptable limits")
            print()

    # Save detailed results to file
    output_file = Path("memory_profile_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
