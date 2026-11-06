# 📖 Learning Guide — How This Project Works

This guide explains **every part of this project in plain English**, so you can understand what you built, explain it in an interview, or revisit it in the future.

---

## 🧠 The Big Picture (Read This First)

Imagine you manage 50 network routers. Without automation, you'd need to:
- SSH into each one manually (50 logins)
- Type `show running-config` to save each config (50 times)
- Type the same VLAN commands on every device (50 times)

**This project does all of that automatically with one Python command.**

```
python main_automation.py
```

That one command:
1. Opens SSH connections to ALL routers at the same time
2. Downloads and saves every router's config as a backup file
3. Pushes a new guest WiFi network config to all routers simultaneously

---

## 📂 File-by-File Explanation

### 1. `config/devices.yaml` — Your Device List

```yaml
devices:
  - device_type: cisco_ios
    host: 192.168.1.1
    username: admin
    password: your_password
```

**What it is:** A simple list of every router/switch the script will manage.
**Think of it as:** A contact list for your network devices.
**Why YAML?** It's human-readable — easier than a database or spreadsheet.

---

### 2. `scripts/device_manager.py` — The SSH Connection Engine

```python
class DeviceManager:
    def connect(self):    # Opens SSH into the device
    def send_command():   # Runs a show command (e.g. show version)
    def send_config():    # Pushes config commands (e.g. vlan 100)
    def disconnect():     # Closes the SSH session
```

**What it is:** A Python class that wraps **Netmiko** (a library that speaks Cisco/Juniper/Arista SSH).
**Think of it as:** A remote control for a network device — you tell it what to do, it does it over SSH.
**Key concept:** `ConnectHandler(**device_config)` — this is what actually opens the SSH session.

---

### 3. `scripts/config_backup.py` — The Backup System

```python
class ConfigBackup:
    def backup_device(device_config):       # Backs up ONE device
    def backup_all_devices(devices_yaml):   # Backs up ALL devices in the list
```

**What it does:**
1. Connects to a device via SSH
2. Runs `show running-config`
3. Saves the output to a `.txt` file with a timestamp

**Example output file:** `backups/192.168.1.1_20261106_173000.txt`

**Why it matters:** If a router crashes or someone accidentally deletes config, you can restore from this file. This is called **disaster recovery**.

---

### 4. `scripts/config_deploy.py` — The Config Pusher

```python
class ConfigDeploy:
    def deploy_commands(device, commands)         # Push raw CLI commands
    def deploy_from_template(device, template)    # Push from a Jinja2 template
    def deploy_from_file(device, file)            # Push from a .txt file
    def rollback_config(device, backup_file)      # Undo changes (use a backup)
```

**What it does:** Pushes configuration commands to a device — same as typing them manually but automated.

**Key concept — Jinja2 templates:** Instead of hardcoding every value, you write a template with variables:
```
vlan {{ guest_vlan_id }}       ← variable, filled in at runtime
 name {{ guest_vlan_name }}
```
Then Python fills in the values and sends the final config. This way one template works for 50 devices.

---

### 5. `config/templates/guest_network.j2` — The Guest WiFi Template

This is the template that gets rendered and pushed to every router. It creates:
- A new VLAN (e.g. VLAN 100)
- A gateway IP for guests (e.g. 192.168.100.1)
- A DHCP pool so guest devices get IP addresses automatically
- An ACL (firewall rule) that blocks guests from reaching your internal network

**Why it's powerful:** You write it once, and it deploys identically to 100 routers in seconds.

---

### 6. `main_automation.py` — The Main Script (Entry Point)

This is the script you actually run. It orchestrates everything:

```
Step 1: Load devices.yaml → get list of all devices
Step 2: Backup all devices (disaster recovery snapshot)
Step 3: Deploy guest network to ALL devices simultaneously
Step 4: Print a summary report
```

**Key concept — ThreadPoolExecutor (simultaneous = parallel):**
```python
with ThreadPoolExecutor(max_workers=len(devices)) as executor:
    # This launches ALL SSH sessions at the SAME TIME
    # Instead of: device1 (5s) → device2 (5s) → ... = 50 × 5s = 250s
    # You get:    all devices at once              = just 5s total
```

---

### 7. `scripts/config_compliance.py` — The Security Checker (Bonus Feature)

Reads backup files and checks them against security rules like:
- ✅ SSH v2 must be enabled
- ✅ Telnet must NOT be enabled
- ✅ NTP server must be configured
- ✅ SNMP public community string must NOT exist

Outputs a compliance score like: `192.168.1.1: 90% compliant (9/10 rules passed)`

**Why it matters:** Audits and compliance (like PCI-DSS, ISO 27001) require proof that devices follow security standards.

---

### 8. `scripts/notifications.py` — Alerts (Bonus Feature)

Sends an email or Slack message when backups or deployments finish.

**How it works:**
- **Email:** Uses Python's built-in `smtplib` to connect to Gmail's SMTP server
- **Slack:** Sends an HTTP POST request to a Slack Webhook URL

---

### 9. `scripts/dashboard.py` — Web UI (Bonus Feature)

A Flask web app at `http://localhost:5000` that lets you:
- See all devices at a glance
- Trigger a backup with one click
- View backup files
- Check compliance scores
- Read live log output

**Flask** is a lightweight Python web framework — it handles HTTP requests and returns HTML pages.

---

### 10. `tests/test_config_manager.py` — Unit Tests

**What are unit tests?** Small scripts that automatically verify your code works correctly.

```python
def test_backup_device_success():
    # Pretend to connect to a fake device
    # Check that a backup file was created
    # Check the filename contains the device IP
```

**Why they matter:** You can change code confidently knowing tests will catch any breakage.

**31 tests, all passing ✅**

---

## 🔗 How Everything Connects

```
devices.yaml
     │
     ▼
device_manager.py  ←── SSH library (Netmiko)
     │
     ├──► config_backup.py   → saves to backups/
     │
     ├──► config_deploy.py   ← reads guest_network.j2 (Jinja2)
     │                          sends commands over SSH
     └──► config_compliance.py → reads backups, checks rules

main_automation.py          ← runs all of the above in order
test_connection.py          ← verifies SSH works before the main run
```

---

## 🛠️ Technologies Used & Why

| Technology | What It Is | Why Used Here |
|---|---|---|
| **Python** | Programming language | Versatile, huge networking library support |
| **Netmiko** | Python SSH library for network devices | Handles Cisco/Juniper/Arista quirks automatically |
| **Paramiko** | Low-level SSH library | Netmiko's engine underneath |
| **PyYAML** | Reads `.yaml` files | Human-readable device inventory |
| **Jinja2** | Template engine | Reusable config templates with variables |
| **Flask** | Micro web framework | Powers the web dashboard |
| **ThreadPoolExecutor** | Python concurrency tool | Runs SSH sessions in parallel (simultaneous) |
| **pytest** | Testing framework | Automated unit tests |

---

## 💡 Key Concepts to Remember

### SSH
Secure Shell — an encrypted protocol to remotely log into a device and run commands. All network engineers use this daily. Netmiko automates it.

### Jinja2 Templates
Like a Word mail merge — you write `Dear {{ name }}`, Python fills in the name. Here you write `vlan {{ vlan_id }}` and Python fills in `100`.

### Parallel vs Sequential
- **Sequential:** Do task A, wait, do task B, wait... (slow)
- **Parallel:** Do task A AND B AND C at the same time (fast)
- `ThreadPoolExecutor` makes code run in parallel.

### Infrastructure as Code (IaC)
Storing network configs in files/templates rather than typing them manually. This project is a basic example of IaC — the same concept used in Ansible, Terraform, etc.

---

## 🎤 How to Explain This in an Interview

> *"I built a Python-based network automation framework that uses Netmiko to SSH into Cisco routers and automate configuration management. It backs up running configs for disaster recovery, and uses Jinja2 templates with Python's ThreadPoolExecutor to simultaneously push config changes — like deploying a guest VLAN — across all devices in parallel instead of one at a time. I also added a Flask web dashboard, compliance checker, and Slack/email notifications, and wrote 31 unit tests with pytest."*

---

## 🚀 What to Learn Next (Build on This)

| Topic | What It Is | How It Relates |
|---|---|---|
| **Ansible** | Professional automation tool | Does what this project does, but at enterprise scale |
| **NAPALM** | Multi-vendor network library | Alternative to Netmiko |
| **Git/GitHub** | Version control | Track config changes over time |
| **Docker** | Containerization | Package this app to run anywhere |
| **REST APIs** | Web APIs | The dashboard already has one! |
| **Cisco DevNet** | Cisco developer platform | Free sandboxes to practice with real IOS |

