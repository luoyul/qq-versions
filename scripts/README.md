# Scripts

Planned scripts:

- import an APK and read package metadata;
- calculate SHA-256 and update the catalog;
- validate Release asset names and checksums;
- generate the static download page.

## 7723 QQ downloader

Download selected historical QQ versions by their visible version number:

```powershell
.\scripts\Download-7723History.ps1 -Product qq -Versions 9.3.75,9.3.70
```

Use `-ListOnly` to inspect matches without downloading, `-All` to request every listed version, and `-WhatIf` to preview downloads. Existing non-empty APK files are hashed and skipped.

Scripts must never rewrite or patch an imported APK.
