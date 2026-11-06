"""
main_automation.py — Network Automation & Provisioning — Main Runner
====================================================================
This is the top-level entry point for the project.  It runs the full
automation workflow end-to-end:

    Step 1  →  Backup all device configs (pre-change snapshot)
    Step 2  →  Deploy the guest network to ALL devices simultaneously
    Step 3  →  Print a clear summary report

Run from the project root:
    python main_automation.py

Optional flags:
    --devices   config/devices.yaml   (alternative inventory file)
    --vlan      100                   (guest VLAN ID, default 100)
    --dry-run                         (render template but skip deploy)
"""

import argparse
import logging
import logging.handlers
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the scripts/ directory is importable regardless of where the script
# is launched from (fixes the "ModuleNotFoundError" when run from project root)
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from device_manager import load_devices_from_yaml   # noqa: E402
from config_backup import ConfigBackup               # noqa: E402
from config_deploy import ConfigDeploy               # noqa: E402


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "network_automation.log"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger: coloured console output + rotating log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:          # avoid duplicates if called more than once
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # Rotating file handler (10 MB × 5 files)
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guest network variables — edit these or pass via CLI flags
# ---------------------------------------------------------------------------

DEFAULT_GUEST_VLAN = {
    "guest_vlan_id":     100,
    "guest_vlan_name":   "GUEST_WIFI",
    "guest_gateway":     "192.168.100.1",
    "guest_network":     "192.168.100.0",
    "guest_subnet_mask": "255.255.255.0",
    "guest_wildcard":    "0.0.0.255",
    "dns_server":        "8.8.8.8",
}


# ---------------------------------------------------------------------------
# Helper: banner printing
# ---------------------------------------------------------------------------

def banner(text: str, width: int = 60) -> None:
    print("=" * width)
    print(f"  {text}")
    print("=" * width)


def step_header(n: int, text: str) -> None:
    print(f"\n[STEP {n}] {text}")
    print("-" * 50)


# ---------------------------------------------------------------------------
# Step 1: Backup all devices
# ---------------------------------------------------------------------------

def run_backup(devices_yaml: str) -> dict:
    """Back up all devices and return the results dict."""
    backup_manager = ConfigBackup(backup_dir="backups")
    return backup_manager.backup_all_devices(devices_yaml)


# ---------------------------------------------------------------------------
# Step 2: Deploy guest network to ONE device (called in a thread)
# ---------------------------------------------------------------------------

def _deploy_guest_to_device(device: dict, variables: dict, dry_run: bool) -> dict:
    """Deploy the guest_network.j2 template to a single device.

    Returns a dict with keys: host, success, elapsed, error.
    """
    host = device.get("host", "unknown")
    start = time.monotonic()

    if dry_run:
        logger.info(f"[DRY-RUN] Skipping actual SSH to {host}")
        return {"host": host, "success": True, "elapsed": 0.0, "error": None}

    try:
        deployer = ConfigDeploy(template_dir="config/templates")
        success = deployer.deploy_from_template(device, "guest_network.j2", variables)
        elapsed = time.monotonic() - start
        return {"host": host, "success": success, "elapsed": elapsed, "error": None}
    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.error(f"Exception deploying to {host}: {exc}")
        return {"host": host, "success": False, "elapsed": elapsed, "error": str(exc)}


# ---------------------------------------------------------------------------
# Step 2 (orchestrator): deploy to ALL devices simultaneously
# ---------------------------------------------------------------------------

def run_simultaneous_deploy(devices: list, variables: dict, dry_run: bool) -> list:
    """Push the guest network config to every device at the same time.

    Uses a thread pool so all SSH sessions open in parallel — the total
    elapsed time is roughly the slowest single device, not the sum.
    """
    if not devices:
        logger.warning("No devices found — nothing to deploy.")
        return []

    logger.info(
        f"Launching simultaneous deployment to {len(devices)} device(s) "
        f"[dry_run={dry_run}]"
    )

    results = []
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        future_to_host = {
            executor.submit(_deploy_guest_to_device, device, variables, dry_run): device["host"]
            for device in devices
        }

        for future in as_completed(future_to_host):
            result = future.result()
            results.append(result)
            status = "✅" if result["success"] else "❌"
            elapsed_str = f"{result['elapsed']:.1f}s" if not dry_run else "skipped"
            print(f"  {status} {result['host']} — {elapsed_str}")

    return results


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def print_summary(backup_results: dict, deploy_results: list) -> None:
    print()
    banner("AUTOMATION SUMMARY", width=60)

    # Backup summary
    b_ok  = backup_results.get("successful", 0)
    b_tot = backup_results.get("total", 0)
    b_icon = "✅" if b_ok == b_tot else "⚠️"
    print(f"\n  {b_icon} Backups   : {b_ok}/{b_tot} successful")

    # Deployment summary
    if deploy_results:
        d_ok  = sum(1 for r in deploy_results if r["success"])
        d_tot = len(deploy_results)
        d_icon = "✅" if d_ok == d_tot else "⚠️"
        print(f"  {d_icon} Deployment: {d_ok}/{d_tot} successful")

        # Per-device detail
        print()
        for r in sorted(deploy_results, key=lambda x: x["host"]):
            icon = "✅" if r["success"] else "❌"
            note = f"{r['elapsed']:.1f}s" if r["elapsed"] else "dry-run"
            err  = f" — {r['error']}" if r.get("error") else ""
            print(f"      {icon} {r['host']} ({note}){err}")

    print(f"\n  Logs saved → {LOG_FILE}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Network Automation — backup all devices and deploy guest network"
    )
    p.add_argument(
        "--devices", default="config/devices.yaml",
        help="Path to device inventory YAML (default: config/devices.yaml)"
    )
    p.add_argument(
        "--vlan", type=int, default=DEFAULT_GUEST_VLAN["guest_vlan_id"],
        help="Guest VLAN ID to deploy (default: 100)"
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Render the template and log actions but skip real SSH deploys"
    )
    p.add_argument(
        "--skip-backup", action="store_true",
        help="Skip the pre-change backup step"
    )
    p.add_argument(
        "--skip-deploy", action="store_true",
        help="Run backup only — no deployment"
    )
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    banner("Network Automation & Provisioning", width=60)
    print(f"  Started  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Inventory: {args.devices}")
    print(f"  VLAN     : {args.vlan}")
    if args.dry_run:
        print("  Mode     : DRY-RUN (no changes will be pushed)")

    # Load device inventory
    devices = load_devices_from_yaml(args.devices)
    if not devices:
        logger.error(f"No devices found in {args.devices}. Exiting.")
        sys.exit(1)
    print(f"  Devices  : {len(devices)} loaded\n")

    # -----------------------------------------------------------------------
    # Step 1 — Backup
    # -----------------------------------------------------------------------
    backup_results = {"successful": 0, "total": 0}

    if not args.skip_backup:
        step_header(1, "Backing up all device configs (pre-change snapshot)")
        backup_results = run_backup(args.devices)
        for d in backup_results.get("devices", []):
            icon = "✅" if d["status"] == "success" else "❌"
            print(f"  {icon} {d['host']} → backups/{d['host']}_<timestamp>.txt")
        print(
            f"\n  Backup complete: "
            f"{backup_results['successful']}/{backup_results['total']} successful"
        )
    else:
        step_header(1, "Backup SKIPPED (--skip-backup flag)")

    # -----------------------------------------------------------------------
    # Step 2 — Simultaneous guest network deployment
    # -----------------------------------------------------------------------
    deploy_results = []

    if not args.skip_deploy:
        # Build template variables (override VLAN ID if provided via CLI)
        variables = dict(DEFAULT_GUEST_VLAN)
        variables["guest_vlan_id"] = args.vlan

        step_header(2, f"Deploying guest network (VLAN {args.vlan}) to all devices simultaneously")
        if args.dry_run:
            print("  [DRY-RUN] Template will be rendered but NOT pushed to devices.")

        deploy_results = run_simultaneous_deploy(devices, variables, dry_run=args.dry_run)
        d_ok  = sum(1 for r in deploy_results if r["success"])
        print(
            f"\n  Provisioning complete: "
            f"{d_ok}/{len(deploy_results)} successful"
        )
    else:
        step_header(2, "Deployment SKIPPED (--skip-deploy flag)")

    # -----------------------------------------------------------------------
    # Final summary
    # -----------------------------------------------------------------------
    print_summary(backup_results, deploy_results)


if __name__ == "__main__":
    main()

