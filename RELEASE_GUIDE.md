# NetGuard Professional release guide

Use this guide for a release from the existing project directory. Do not copy the project or create a ZIP as part of this process.

## Build

1. Run `build_exe.bat` from the project root on Windows.
2. Confirm it completes compilation, unit tests, Ruff, and both PyInstaller steps.
3. Confirm these files exist in `dist`:
   - `NetGuard_Professional_2_3_0.exe`
   - `NetGuard_Admin_Recovery.exe`

## Manual acceptance

1. Start `NetGuard_Professional_2_3_0.exe`, sign in with a local account, and open Settings.
2. Confirm saved health thresholds and local retention values load correctly.
3. Run an authorized Standard network scan, save it as a named baseline, run another completed Standard scan, and compare against the saved baseline.
4. Export a scan CSV and unified JSON report. Confirm the CSV has `Comparison Status` and JSON has `scan_comparison`.
5. Start `NetGuard_Admin_Recovery.exe` only when local administrator recovery needs testing; do not expose a password in a command line or screenshot.

## Code-signing (optional until a certificate is available)

The binaries are intentionally unsigned until the release owner supplies a trusted Windows code-signing certificate. With a suitable certificate installed in the Windows certificate store, sign each final EXE with the Windows SDK `signtool`, timestamping through the certificate provider's approved timestamp service. Then verify each signature with:

```powershell
signtool verify /pa /v .\dist\NetGuard_Professional_2_3_0.exe
signtool verify /pa /v .\dist\NetGuard_Admin_Recovery.exe
```

Never commit a certificate file, private key, password, or signing-provider token to this project. Record the signing identity and verification result in the release notes held by the release owner.
