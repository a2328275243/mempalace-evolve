# DreamSeed Python Wheelhouse

Put pre-downloaded Python wheels here when you want an offline-capable release.

Build or refresh this directory from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-python-wheelhouse.ps1
```

The installer prefers this directory when wheels are present. If it is empty, it
falls back to normal online `pip install` behavior.
