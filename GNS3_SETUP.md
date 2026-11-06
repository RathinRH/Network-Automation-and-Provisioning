# GNS3 Setup Guide for This Project

This guide walks you through setting up a GNS3 lab so the Python automation scripts can SSH into virtual Cisco routers — just like they would with real hardware.

---

## Why GNS3 and Not Packet Tracer?

| Feature | Packet Tracer | GNS3 |
|---|---|---|
| Free | ✅ | ✅ |
| SSH from real Python scripts | ❌ | ✅ |
| Netmiko compatible | ❌ | ✅ |
| Real IOS behaviour | Simulated | Real IOS image |

---

## Step 1 — Install GNS3

1. Go to **[https://www.gns3.com/software/download](https://www.gns3.com/software/download)**
2. Create a free account and download the **Windows installer**
3. Run the installer — accept all defaults  
   *(it installs GNS3, WinPcap/Npcap, and a local GNS3 VM option)*

> **Recommended:** When asked, also install **GNS3 VM** (runs inside VirtualBox or VMware). This gives better performance and IOS compatibility.

---

## Step 2 — Get a Cisco IOS Image

GNS3 needs a real Cisco IOS firmware file (`.bin` or `.image`). You have two options:

### Option A — Cisco IOSv (official, recommended)
- Requires a **Cisco Learning Network** or **DevNet** account (free)
- Download: [https://learningnetwork.cisco.com](https://learningnetwork.cisco.com)
- Look for **IOSv** or **IOSvL2** — these are the standard GNS3-compatible images

### Option B — Cisco IOS on Unix (IOU)
- Also available via Cisco DevNet sandbox (free, no download needed)
- Runs entirely in the cloud — no local image required

---

## Step 3 — Add the IOS Image to GNS3

1. Open GNS3
2. Go to **Edit → Preferences → IOS Routers**
3. Click **New** → Browse to your `.bin` file
4. Set RAM to **256 MB**, select the correct platform (e.g. `c7200`)
5. Click **Finish**

---

## Step 4 — Build the Lab Topology

1. Create a **New Project** in GNS3
2. Drag **2 routers** onto the canvas
3. Connect them with a cable
4. Add a **Cloud node** (this represents your PC's real network adapter)
5. Connect one router's interface to the Cloud node

```
[Your PC]
    │  (Cloud node — bridges to your PC's real NIC)
    │
[Router-1]  ──────  [Router-2]
```

---

## Step 5 — Configure SSH on Each Router

Right-click a router → **Console** → type these commands:

```
! Basic setup
Router> enable
Router# configure terminal

! Set hostname (optional but helpful)
Router(config)# hostname R1

! Assign an IP to the interface connected to your PC
R1(config)# interface GigabitEthernet0/0
R1(config-if)# ip address 192.168.1.1 255.255.255.0
R1(config-if)# no shutdown
R1(config-if)# exit

! Enable SSH
R1(config)# ip domain-name lab.local
R1(config)# crypto key generate rsa modulus 2048
R1(config)# ip ssh version 2

! Create a user account
R1(config)# username admin privilege 15 secret MyPassword123

! Allow SSH on VTY lines
R1(config)# line vty 0 4
R1(config-line)# login local
R1(config-line)# transport input ssh
R1(config-line)# exit

! Save config
R1(config)# end
R1# write memory
```

Repeat for **Router-2** using IP `192.168.1.2`.

---

## Step 6 — Test SSH from Your PC

Open a terminal and confirm you can reach the routers:

```bash
# Ping test
ping 192.168.1.1
ping 192.168.1.2

# SSH test (password: MyPassword123)
ssh admin@192.168.1.1
```

If SSH works manually, the Python scripts will work too.

---

## Step 7 — Update devices.yaml

Edit `config/devices.yaml` with your actual values:

```yaml
devices:
  - device_type: cisco_ios
    host: 192.168.1.1          # Router-1 IP
    username: admin
    password: MyPassword123
    secret: MyPassword123      # Same as enable secret
    port: 22

  - device_type: cisco_ios
    host: 192.168.1.2          # Router-2 IP
    username: admin
    password: MyPassword123
    port: 22
```

---

## Step 8 — Run the Project

```bash
# 1. Test SSH connectivity first
python test_connection.py

# 2. If all devices show ✅, run the full automation
python main_automation.py
```

Expected output when everything works:

```
============================================================
  Network Automation & Provisioning
============================================================
  Devices  : 2 loaded

[STEP 1] Backing up all device configs...
  ✅ 192.168.1.1 → backups/192.168.1.1_20261106_173000.txt
  ✅ 192.168.1.2 → backups/192.168.1.2_20261106_173001.txt
  Backup complete: 2/2 successful

[STEP 2] Deploying guest network (VLAN 100) simultaneously...
  ✅ 192.168.1.1 — 3.2s
  ✅ 192.168.1.2 — 3.5s
  Provisioning complete: 2/2 successful
============================================================
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ping` fails to router IP | Check GNS3 Cloud node is linked to the right NIC |
| `SSH connection refused` | Make sure `transport input ssh` is set on VTY lines |
| `Authentication failed` | Check username/password in `devices.yaml` matches router config |
| `crypto key generate` fails | Run `ip domain-name lab.local` first |
| GNS3 router won't start | Increase RAM allocation for the router in GNS3 preferences |

---

## Alternative: Cisco DevNet Sandbox (No Installation)

If you don't want to install GNS3, Cisco provides **free always-on sandboxes** with real IOS devices accessible over SSH:

1. Go to **[https://devnetsandbox.cisco.com](https://devnetsandbox.cisco.com)**
2. Reserve a **"IOS XE on CSR Recommended Code"** sandbox (free, 4-hour sessions)
3. Use the provided IP, username, and password in `devices.yaml`
4. Run `python test_connection.py` to verify, then `python main_automation.py`

This is the **fastest way to test with no setup**.

