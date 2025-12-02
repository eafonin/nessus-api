#!/usr/bin/env python3
"""Admin CLI for Dead Letter Queue management and queue statistics.

Phase 4.11: Admin tools for inspecting and managing failed tasks.

Usage:
    python -m tools.admin_cli stats --pool nessus
    python -m tools.admin_cli list-dlq --pool nessus --limit 20
    python -m tools.admin_cli inspect-dlq task_id --pool nessus
    python -m tools.admin_cli retry-dlq task_id --pool nessus
    python -m tools.admin_cli purge-dlq --pool nessus --confirm
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.queue import TaskQueue, get_all_pool_stats, get_queue_stats


def format_timestamp(ts_str: str | None) -> str:
    """Format ISO timestamp to readable format."""
    if ts_str is None:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return ts_str or "N/A"


def truncate(s: str, max_len: int = 50) -> str:
    """Truncate string to max length."""
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def cmd_stats(queue: TaskQueue, args) -> int:
    """Show queue statistics."""
    if args.all_pools:
        # Get stats for all common pools
        pools = ["nessus", "nessus_dmz", "nuclei"]
        stats = get_all_pool_stats(queue, pools)

        print("\n" + "=" * 60)
        print("Queue Statistics (All Pools)")
        print("=" * 60)
        print(f"Total Queue Depth:  {stats['total_queue_depth']}")
        print(f"Total DLQ Size:     {stats['total_dlq_size']}")
        print(f"Timestamp:          {stats['timestamp']}")
        print()

        print("Per-Pool Breakdown:")
        print("-" * 40)
        for ps in stats["pools"]:
            if ps["queue_depth"] > 0 or ps["dlq_size"] > 0:
                print(
                    f"  {ps['pool']:15} queue={ps['queue_depth']:3}  dlq={ps['dlq_size']:3}"
                )

    else:
        pool = args.pool
        stats = get_queue_stats(queue, pool)

        print("\n" + "=" * 60)
        print(f"Queue Statistics: {pool}")
        print("=" * 60)
        print(f"Queue Depth:  {stats['queue_depth']}")
        print(f"DLQ Size:     {stats['dlq_size']}")
        print(f"Timestamp:    {stats['timestamp']}")

        if stats["next_tasks"]:
            print()
            print("Next tasks in queue:")
            print("-" * 40)
            for i, task in enumerate(stats["next_tasks"], 1):
                print(
                    f"  {i}. {task.get('task_id', 'N/A')[:20]} - {task.get('scan_type', 'N/A')}"
                )

    print()
    return 0


def cmd_list_dlq(queue: TaskQueue, args) -> int:
    """List tasks in Dead Letter Queue."""
    pool = args.pool
    limit = args.limit

    tasks = queue.get_dlq_tasks(start=0, end=limit - 1, pool=pool)

    if not tasks:
        print(f"\nNo tasks in DLQ for pool: {pool}")
        return 0

    print("\n" + "=" * 80)
    print(f"Dead Letter Queue: {pool} ({len(tasks)} tasks)")
    print("=" * 80)

    # Header
    print(f"{'Task ID':<24} {'Type':<12} {'Error':<30} {'Failed At':<19}")
    print("-" * 80)

    for task in tasks:
        task_id = truncate(task.get("task_id", "?"), 24)
        scan_type = task.get("scan_type", "?")[:12]
        error = truncate(task.get("error", "?"), 30)
        failed_at = format_timestamp(task.get("failed_at"))

        print(f"{task_id:<24} {scan_type:<12} {error:<30} {failed_at:<19}")

    print("-" * 80)
    print(f"Total: {len(tasks)} tasks")
    print()

    return 0


def cmd_inspect_dlq(queue: TaskQueue, args) -> int:
    """Show detailed info for a DLQ task."""
    pool = args.pool
    task_id = args.task_id

    task = queue.get_dlq_task(task_id, pool=pool)

    if not task:
        print(f"\nTask '{task_id}' not found in DLQ for pool '{pool}'")
        return 1

    print("\n" + "=" * 60)
    print(f"DLQ Task: {task_id}")
    print("=" * 60)

    # Pretty print the task
    print(json.dumps(task, indent=2, default=str))

    print()
    return 0


def cmd_retry_dlq(queue: TaskQueue, args) -> int:
    """Move task from DLQ back to main queue."""
    pool = args.pool
    task_id = args.task_id

    # Confirm unless --yes flag
    if not args.yes:
        confirm = input(f"Retry task '{task_id}' from pool '{pool}'? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return 0

    success = queue.retry_dlq_task(task_id, pool=pool)

    if success:
        print(f"✅ Task '{task_id}' moved to main queue for retry")
        return 0
    else:
        print(f"❌ Failed to retry task '{task_id}' (not found or error)")
        return 1


def cmd_purge_dlq(queue: TaskQueue, args) -> int:
    """Clear all tasks from DLQ."""
    pool = args.pool

    if not args.confirm:
        print("Error: --confirm flag required for purge operation")
        print("Usage: admin_cli purge-dlq --pool nessus --confirm")
        return 1

    # Double confirm
    confirm = input(f"DANGER: Purge ALL tasks from DLQ for pool '{pool}'? [yes/NO]: ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return 0

    count = queue.clear_dlq(pool=pool)
    print(f"✅ Purged {count} tasks from DLQ for pool '{pool}'")

    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Nessus MCP Admin CLI - DLQ management and queue statistics"
    )
    parser.add_argument(
        "--redis-url",
        default=os.getenv("REDIS_URL", "redis://localhost:6379"),
        help="Redis URL (default: from REDIS_URL env or redis://localhost:6379)",
    )
    parser.add_argument(
        "--pool", default="nessus", help="Scanner pool name (default: nessus)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show queue statistics")
    stats_parser.add_argument(
        "--all-pools", action="store_true", help="Show stats for all pools"
    )

    # list-dlq command
    list_parser = subparsers.add_parser("list-dlq", help="List DLQ tasks")
    list_parser.add_argument(
        "--limit", type=int, default=20, help="Maximum tasks to show (default: 20)"
    )

    # inspect-dlq command
    inspect_parser = subparsers.add_parser("inspect-dlq", help="Inspect DLQ task")
    inspect_parser.add_argument("task_id", help="Task ID to inspect")

    # retry-dlq command
    retry_parser = subparsers.add_parser("retry-dlq", help="Retry DLQ task")
    retry_parser.add_argument("task_id", help="Task ID to retry")
    retry_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )

    # purge-dlq command
    purge_parser = subparsers.add_parser("purge-dlq", help="Purge all DLQ tasks")
    purge_parser.add_argument(
        "--confirm",
        action="store_true",
        required=True,
        help="Required flag to confirm purge operation",
    )

    args = parser.parse_args()

    # Connect to Redis
    try:
        queue = TaskQueue(redis_url=args.redis_url)
    except Exception as e:
        print(f"Error connecting to Redis: {e}")
        print(f"URL: {args.redis_url}")
        return 1

    try:
        # Dispatch to command handler
        if args.command == "stats":
            return cmd_stats(queue, args)
        elif args.command == "list-dlq":
            return cmd_list_dlq(queue, args)
        elif args.command == "inspect-dlq":
            return cmd_inspect_dlq(queue, args)
        elif args.command == "retry-dlq":
            return cmd_retry_dlq(queue, args)
        elif args.command == "purge-dlq":
            return cmd_purge_dlq(queue, args)
        else:
            parser.print_help()
            return 1
    finally:
        queue.close()


if __name__ == "__main__":
    sys.exit(main())
