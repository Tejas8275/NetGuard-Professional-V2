# 🛡️ NetGuard Professional V2

## Advanced Network Security & Monitoring Toolkit

NetGuard Professional V2 is a Python-based cybersecurity and network operations toolkit designed for network visibility, security assessment, device monitoring, and vulnerability awareness.

The application provides an interactive desktop GUI for performing network diagnostics, TCP scanning, risk analysis, system monitoring, VPN awareness, alerts, and security reporting.

---

## 📸 Screenshots

### Dashboard

![NetGuard Dashboard](screenshots/dashboard.png)

### Network Scanner

![Network Scanner](screenshots/scanner.png)

### Security Analysis

![Security Analysis](screenshots/security.png)

---

# 🚀 Features

## 🔍 Network Discovery

- Discover connected network devices
- Identify IP and MAC addresses
- Monitor active hosts
- View network information

---

## 🔐 Security Assessment

- TCP port scanning
- Open service detection
- Risk scoring
- Security level classification
- Vulnerability awareness

---

## 📡 Network Monitoring

- Real-time network statistics
- Latency monitoring
- Device health monitoring
- Connection analysis

---

## 🛡️ VPN Awareness

- Detect VPN-related network changes
- Analyze network interfaces
- Monitor connectivity changes

---

## 🚨 Alert System

- Security alerts
- Risk notifications
- Event tracking
- System warnings

---

## 📊 Reporting

- Security assessment reports
- Scan results
- Network analysis summaries

---

# 🏗️ Architecture

```
                 ┌──────────────────────┐
                 │      User Interface  │
                 │    Tkinter Desktop   │
                 └──────────┬───────────┘
                            │
                            ▼

                 ┌──────────────────────┐
                 │     Main Controller  │
                 │       main.py        │
                 └──────────┬───────────┘

                            │

        ┌───────────────────┼───────────────────┐
        │                   │                   │

        ▼                   ▼                   ▼


┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Networking  │     │  Security   │     │ Monitoring  │
│   Core      │     │   Engine    │     │   Engine    │
└─────────────┘     └─────────────┘     └─────────────┘

        │                   │                   │

        ▼                   ▼                   ▼


┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Scanner     │     │ Risk Engine │     │ Alert       │
│ Module      │     │             │     │ System      │
└─────────────┘     └─────────────┘     └─────────────┘


                            │

                            ▼

                 ┌──────────────────────┐
                 │ Storage & Reporting  │
                 └──────────────────────┘
```

---

# 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| GUI | Tkinter |
| Networking | Socket Programming |
| System Monitoring | psutil |
| Testing | PyTest |
| Version Control | Git/GitHub |

---

# 📂 Project Structure

```
NetGuard-Professional-V2

│
├── main.py
│
├── core/
│   ├── network_core.py
│   ├── scanner.py
│   ├── security.py
│   ├── alerts.py
│   └── storage.py
│
├── ui/
│
├── tests/
│
├── screenshots/
│
├── .github/
│
├── README.md
│
└── LICENSE
```

---

# ⚙️ Installation

Clone repository:

```bash
git clone https://github.com/Tejas8275/NetGuard-Professional-V2.git
```

Enter project directory:

```bash
cd NetGuard-Professional-V2
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶️ Running Application

Start NetGuard:

```bash
python main.py
```

---

# 🧪 Testing

Run tests:

```bash
pytest
```

---

# 🎯 Use Cases

- Cybersecurity learning
- Network administration practice
- Blue-team security research
- Local network analysis
- IT troubleshooting

---

# 🔒 Security Notice

NetGuard is designed for defensive security, education, and authorized network analysis only.

Always obtain permission before scanning networks or devices.

---

# 👨‍💻 Developer

**Tejas8275**

GitHub:

https://github.com/Tejas8275

---

# 📜 License

MIT License