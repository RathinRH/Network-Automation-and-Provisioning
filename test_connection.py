"""
test_connection.py — Pre-flight SSH connectivity checker
=========================================================
Run this BEFORE main_automation.py to confirm every device in
devices.yaml is reachable and your credentials are correct.

Usage:
    python test_connection.py
    python test_connection.py --devices config/devices.yaml
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Allow running from project root
SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from device_manager import DeviceManager, load_devices_from_yaml  # noqa: E402

logging.basicConfig(
    level=logging.WARNING,          # suppress netmiko noise during test
    format="%(levelname)s: %(message)s",
)


def test_device(device: dict) -> dict:
    """Try to SSH into one device and run 'show version'."""
    host = device.get("host", "unknown")
    start = time.monotonic()

    dm = DeviceManager(device)
    connected = dm.connect()

    if not connected:
        return {"host": host, "ok": False, "elapsed": time.monotonic() - start,
                "error": "SSH connection failed — wrong IP, creds, or SSH not enabled"}

    try:
        output = dm.send_command("show version")
        elapsed = time.monotonic() - start
        # Grab first meaningful line from output
        first_line = next((l.strip() for l in (output or "").splitlines() if l.strip()), "")
        return {"host": host, "ok": True, "elapsed": elapsed,
                "detail": first_line[:80]}
    except Exception as exc:
        return {"host": host, "ok": False, "elapsed": time.monotonic() - start,
                "error": str(exc)}
    finally:
        dm.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Test SSH connectivity to all devices in inventory"
    )
    parser.add_argument("--devices", default="config/devices.yaml",
                        help="Path to device inventory YAML")
    args = parser.parse_args()

    devices = load_devices_from_yaml(args.devices)
    if not devices:
        print(f"❌  No devices found in {args.devices}")
        sys.exit(1)

    print("=" * 60)
    print("  SSH Connectivity Test")
    print(f"  Inventory : {args.devices}  ({len(devices)} device(s))")
    print("=" * 60)

    results = []
    for device in devices:
        host = device.get("host", "?")
        print(f"\n  Testing {host} ...", end="", flush=True)
        result = test_device(device)
        results.append(result)

        if result["ok"]:
            print(f"\r  ✅  {host}  ({result['elapsed']:.1f}s)")
            print(f"       {result.get('detail', '')}")
        else:
            print(f"\r  ❌  {host}  ({result['elapsed']:.1f}s)")
            print(f"       {result.get('error', 'Unknown error')}")

    # Summary
    ok    = sum(1 for r in results if r["ok"])
    total = len(results)
    print()
    print("=" * 60)
    print(f"  Result: {ok}/{total} devices reachable")

    if ok == total:
        print("  ✅  All good — you can run:  python main_automation.py")
    else:
        print("  ⚠️   Fix the failing devices first, then re-run this test.")
        print()
        print("  Common fixes:")
        print("   • Check IP address in config/devices.yaml")
        print("   • Verify SSH is enabled on the device (ip ssh version 2)")
        print("   • Confirm username/password are correct")
        print("   • Make sure your PC can ping the device IP")
    print("=" * 60)

    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()

