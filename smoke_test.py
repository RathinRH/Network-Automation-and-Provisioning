"""
smoke_test.py — Project health check
Verifies imports, file existence, templates, rules, deps, and gitignore.
Run from project root: python smoke_test.py
"""
import os
import sys

sys.path.insert(0, "scripts")

results = []


def check(label, fn):
    try:
        msg = fn()
        results.append((label, "PASS" if msg is None else f"PASS ({msg})"))
    except Exception as e:
        results.append((label, f"FAIL: {e}"))


# ── 1. Core module imports ────────────────────────────────────────────────
check("IMPORT device_manager",    lambda: __import__("device_manager"))
check("IMPORT config_backup",     lambda: __import__("config_backup"))
check("IMPORT config_deploy",     lambda: __import__("config_deploy"))
check("IMPORT config_compliance", lambda: __import__("config_compliance"))
check("IMPORT notifications",     lambda: __import__("notifications"))
check("IMPORT flask",             lambda: __import__("flask"))
check("IMPORT jinja2",            lambda: __import__("jinja2"))
check("IMPORT yaml",              lambda: __import__("yaml"))

# ── 2. Device inventory loads ─────────────────────────────────────────────
def _load_devices():
    from device_manager import load_devices_from_yaml
    devices = load_devices_from_yaml("config/devices.yaml")
    assert len(devices) > 0, "No devices loaded"
    return f"{len(devices)} devices"
check("LOAD devices.yaml", _load_devices)

# ── 3. Compliance rules load ──────────────────────────────────────────────
def _load_rules():
    from config_compliance import ComplianceChecker
    checker = ComplianceChecker(rules_file="config/compliance_rules.json")
    assert len(checker.rules) == 15, f"Expected 15 rules, got {len(checker.rules)}"
    return "15 rules"
check("LOAD compliance_rules.json (15 rules)", _load_rules)

# ── 4. Jinja2 templates render correctly ─────────────────────────────────
def _render_guest():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("config/templates"))
    t = env.get_template("guest_network.j2")
    out = t.render(
        guest_vlan_id=100, guest_vlan_name="GUEST_WIFI",
        guest_gateway="192.168.100.1", guest_network="192.168.100.0",
        guest_subnet_mask="255.255.255.0", guest_wildcard="0.0.0.255",
        dns_server="8.8.8.8",
    )
    assert "vlan 100" in out
    assert "GUEST_WIFI" in out
    assert "ip dhcp pool" in out
    assert "ip access-list extended" in out
    return "VLAN + DHCP + ACL rendered"
check("RENDER guest_network.j2", _render_guest)

def _render_iface():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("config/templates"))
    t = env.get_template("interface_config.j2")
    out = t.render(
        interface_name="GigabitEthernet0/1", description="Test Port",
        ip_address=None, mode="access", vlan=10,
        spanning_tree=True, allowed_vlans=None,
    )
    assert "GigabitEthernet0/1" in out
    assert "switchport mode access" in out
    assert "spanning-tree portfast" in out
    return "access port + portfast rendered"
check("RENDER interface_config.j2", _render_iface)

# ── 5. All files referenced by README exist ───────────────────────────────
def _files_exist():
    required = [
        "main_automation.py", "test_connection.py",
        "requirements.txt", "LICENSE", ".gitignore",
        "scripts/device_manager.py", "scripts/config_backup.py",
        "scripts/config_deploy.py", "scripts/config_compliance.py",
        "scripts/notifications.py", "scripts/dashboard.py",
        "config/devices.yaml", "config/compliance_rules.json",
        "config/templates/guest_network.j2",
        "config/templates/interface_config.j2",
        "templates/dashboard.html",
        "tests/test_config_manager.py",
        "LEARNING_GUIDE.md", "QUICKSTART.md",
        "GNS3_SETUP.md", "NEW_FEATURES.md",
    ]
    missing = [f for f in required if not os.path.exists(f)]
    assert not missing, f"Missing files: {missing}"
    return f"all {len(required)} files present"
check("FILES EXIST (all README-referenced)", _files_exist)

# ── 6. .gitignore excludes secrets ────────────────────────────────────────
def _gitignore():
    with open(".gitignore") as f:
        gi = f.read()
    assert "config/devices.yaml" in gi
    assert "config/notifications.json" in gi
check("GITIGNORE excludes secrets", _gitignore)

# ── 7. requirements.txt has all 7 dependencies ───────────────────────────
def _reqs():
    with open("requirements.txt") as f:
        reqs = f.read().lower()
    deps = ["netmiko", "paramiko", "pyyaml", "jinja2", "flask", "requests", "pytest"]
    missing = [d for d in deps if d not in reqs]
    assert not missing, f"Missing deps: {missing}"
    return "7/7 deps present"
check("REQUIREMENTS.TXT (7 deps)", _reqs)

# ── 8. Version numbers in README match requirements.txt ──────────────────
def _versions():
    with open("requirements.txt") as f:
        reqs = f.read()
    with open("README.md") as f:
        readme = f.read()
    checks = [
        ("netmiko>=4.1.0", "4.1+"),
        ("paramiko>=3.0.0", "3.0+"),
        ("flask>=3.0.0", "3.0+"),
        ("pyyaml>=6.0", "6.0+"),
        ("jinja2>=3.1.0", "3.1+"),
        ("requests>=2.31.0", "2.31+"),
        ("pytest>=9.0", "9.0+"),
    ]
    for req_line, readme_ver in checks:
        assert req_line in reqs, f"requirements.txt missing: {req_line}"
        assert readme_ver in readme, f"README missing version: {readme_ver}"
    return "all versions consistent"
check("VERSION CONSISTENCY (requirements vs README)", _versions)

# ── 9. README has no placeholder text ────────────────────────────────────
def _no_placeholders():
    with open("README.md") as f:
        content = f.read()
    bad = ["yourusername", "git fork ", "5.0+", "4.8+"]
    found = [b for b in bad if b in content]
    assert not found, f"Found stale placeholder text: {found}"
    return "no placeholder text found"
check("README no stale placeholders", _no_placeholders)

def _no_placeholders_qs():
    with open("QUICKSTART.md") as f:
        content = f.read()
    # these were the specific stale strings — yourusername URL and wrong Step 3 command
    bad = ["yourusername", "network-automation-framework.git", "python examples/example_usage.py"]
    found = [b for b in bad if b in content]
    assert not found, f"Found stale text in QUICKSTART: {found}"
    return "no stale text"
check("QUICKSTART.md no stale text", _no_placeholders_qs)

# ── Print results ─────────────────────────────────────────────────────────
width = 62
print()
print("=" * width)
print("  SMOKE TEST RESULTS")
print("=" * width)

passed = 0
for name, status in results:
    ok = status.startswith("PASS")
    icon = "  [OK]" if ok else "  [!!]"
    if ok:
        passed += 1
    print(f"{icon}  {name}")
    if not ok:
        print(f"         {status}")

print("=" * width)
total = len(results)
print(f"  {passed}/{total} checks passed")
if passed == total:
    print("  ALL CLEAR — project is fully consistent with README")
else:
    print("  ISSUES FOUND — see [!!] lines above")
print("=" * width)
sys.exit(0 if passed == total else 1)
