# 🛡️ NETGUARD Professional V2

Advanced Python desktop network troubleshooting and monitoring project for System Engineer / Networking / SOC preparation.

## Features
- Professional left sidebar
- Operations dashboard
- Internet, latency, packet-loss, DNS and gateway cards
- Full health scoring
- Live latency monitoring
- Real-time latency graph
- Automatic alerts
- Ping, DNS, TCP port, traceroute and netstat diagnostics
- Visual network path map
- Diagnostic history
- JSON and health-report export
- Professional themes
- Background threads so the GUI stays responsive
- Live clock
- Smart Network Insights: active adapter detection, IPv4 gateway preference, HTTPS-latency fallback, and explainable health reports
- VPN/WARP awareness: separates the physical adapter from Cloudflare WARP or supported VPN tunnels and records state changes

## Run in VS Code
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```
If `.venv` already exists, activate it and run `python main.py`.

## Quality checks

```powershell
python -m compileall -q .
python -m unittest discover -s tests -v
```

The GitHub Actions workflow runs these checks plus Ruff undefined-name/import checks on every push and pull request. Runtime, build, and development dependencies are pinned separately in `requirements.txt`, `requirements-build.txt`, and `requirements-dev.txt`.

## CV bullet
Developed a professional Python-based Network Operations and Troubleshooting Toolkit featuring real-time latency monitoring, packet-loss analysis, DNS/TCP diagnostics, traceroute automation, health scoring, alerting, visualization and exportable troubleshooting reports.

## Safety
Use diagnostics only on systems and networks you own or are authorized to test.

## Local account and data security

- On a new installation, create the first account during initial setup; it becomes the local administrator.
- The old shared built-in `admin` login is disabled. Existing registered accounts continue to work.
- Passwords use scrypt hashes with a unique salt. New passwords require 12+ characters with uppercase, lowercase, number, and symbol.
- Local users, history, alerts, and scan data are stored under `%LOCALAPPDATA%\NetGuard Professional` and writes are atomic.
- Earlier `~/.netguard_pro_users.json` and `~/.netguard_pro_data.json` files are automatically migrated on first use. Keep the Windows user account protected because operational data remains local to that user profile.

### Administrator password recovery

There is no default or recoverable administrator password. If an existing local administrator password is lost, sign in to the same Windows account that owns NetGuard's local data and run:

```powershell
python reset_admin_password.py
```

The command securely prompts for a new password, applies the existing password policy, writes only a new salted scrypt hash, and preserves the selected account's Administrator role. If more than one administrator exists, specify the intended account with `--username`.

If an older installation has local accounts but no Administrator account, use the explicit local recovery mode to promote a known existing account while resetting its password:

```powershell
python reset_admin_password.py --username YourExistingUser --promote-existing
```

This recovery mode is rejected unless no Administrator account exists; it never creates a hidden or default account.

## New scanner features
- Scan progress, discovered-device count, and cancellation
- MAC-address vendor labels for common devices
- Saved history, alerts, and recent scan data between app restarts
- IPv4 subnet input validation
- Named trusted scan baselines with MAC/IP-aware comparison against current authorized scans
- Configurable local retention for audit events and incidents (100–1000 records each)

## Build a Windows app
1. Install Python 3.13 on Windows with the Python Launcher enabled, then run `build_exe.bat` by double-clicking it or execute `./build_exe.bat` in PowerShell. The script explicitly selects `py -3.13` and keeps its isolated environment in `.build-venv-py313`.
2. The script creates an isolated build environment, installs pinned build dependencies, runs compilation and tests, then packages the executable.
3. After it completes, open `dist\\NetGuard_Professional_2_3_0.exe`. It also creates `dist\\NetGuard_Admin_Recovery.exe`, a visible console utility for the documented local administrator recovery flow.

Windows may display a SmartScreen warning for an unsigned personal application; code-sign the executable before wider distribution.

## Release verification

Use [RELEASE_GUIDE.md](RELEASE_GUIDE.md) before distributing a build. It covers the required automated checks, the two executable artifacts, a short manual acceptance test, and optional Windows code-signing once a valid certificate is available.

---

## Screenshots

Add application screenshots here:

```
screenshots/
 ├── dashboard.png
 ├── network_scan.png
 └── reports.png
```

## Demo

A GIF demonstration can be added here:

```
demo/netguard-demo.gif
```

## Project Structure

```
core/     -> networking and security logic
ui/       -> desktop interface components
assets/   -> application resources
main.py   -> application entry point
```

## License

Released under the MIT License.
