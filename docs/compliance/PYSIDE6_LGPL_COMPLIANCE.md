# PySide6 LGPL-3.0 Compliance Report

## ⚠️ CRITICAL: License Compliance Required

**Date**: 2025-10-08  
**Project**: AniVault  
**Issue**: PySide6 LGPL-3.0 License Compliance

---

## 📋 Summary

AniVault uses **PySide6** for GUI functionality, which is licensed under **LGPL-3.0** (GNU Lesser General Public License v3.0). This license has specific requirements that MUST be met before distribution.

**Current Status**: ⚠️ **NOT COMPLIANT** for binary distribution

---

## 🔍 LGPL-3.0 Requirements

### What LGPL-3.0 Requires:

1. **Source Code Availability**: Users must have access to the source code
2. **Dynamic Linking**: Application must dynamically link to LGPL libraries (NOT static linking)
3. **User Replacement**: Users must be able to replace the LGPL library with a modified version
4. **License Notice**: Must include LGPL license text and copyright notices
5. **Modification Rights**: Users must be informed of their right to modify the LGPL library

### What This Means for PyInstaller:

❌ **Single-file executables** (default PyInstaller mode) are **NOT LGPL-compliant**  
✅ **Directory-mode distribution** with separate DLLs **IS compliant**

---

## 🚨 Current Risk Analysis

### Risk Level: **CRITICAL** 🔴

| Risk | Impact | Compliance Status |
|------|--------|-------------------|
| PyInstaller single-file bundle | Violates LGPL dynamic linking requirement | ❌ Non-compliant |
| Missing LGPL license notices | License violation | ❌ Not implemented |
| No user replacement mechanism | Violates LGPL Section 4 | ❌ Not implemented |
| Static linking of PySide6 | License violation | ❌ Risk exists |

---

## ✅ Compliance Solutions

### Option A: Directory Mode Distribution (RECOMMENDED)

**PyInstaller directory mode** allows dynamic linking:

```python
# .spec file configuration
a = Analysis(
    ['src/anivault/cli/typer_app.py'],
    ...
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],  # ⚠️ Empty! Don't bundle everything
    exclude_binaries=True,  # ✅ Critical for LGPL compliance
    name='anivault',
    ...
)

coll = COLLECT(
    exe,
    a.binaries,  # ✅ Separate DLLs
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='anivault'
)
```

**Result**: `dist/anivault/` directory with:
```
anivault/
├── anivault.exe          # Main executable
├── PySide6/              # ✅ Separate DLLs (user-replaceable)
│   ├── Qt6Core.dll
│   ├── Qt6Gui.dll
│   └── Qt6Widgets.dll
├── python312.dll
└── ... (other dependencies)
```

---

### Option B: Commercial Qt License

**Purchase Qt for Python Commercial License**:
- Cost: ~$5,000/year per developer
- Benefit: No LGPL restrictions
- Allows: Single-file distribution, proprietary bundling

**NOT RECOMMENDED** for open-source projects

---

### Option C: Remove PySide6 (Alternative GUI)

Replace PySide6 with MIT-licensed alternatives:
- **tkinter** (built-in, limited features)
- **wxPython** (wxWindows License, permissive)
- **PyQt6** (GPL-3.0, incompatible with MIT)

**NOT RECOMMENDED** - PySide6 is best Qt binding

---

## 📝 Required Actions (Priority Order)

### 1. Update PyInstaller Configuration ✅

**File**: `anivault.spec` or build script

```python
# Change from:
exe = EXE(..., a.binaries, ..., onefile=True)  # ❌ WRONG

# Change to:
exe = EXE(..., exclude_binaries=True)  # ✅ CORRECT
coll = COLLECT(exe, a.binaries, ...)   # ✅ Separate DLLs
```

### 2. Add LGPL License Notices ✅

**File**: `LICENSE-THIRD-PARTY.txt` (create)

```text
================================================================================
Third-Party Software Licenses
================================================================================

This software uses the following third-party libraries:

1. PySide6 (Qt for Python)
   License: LGPL-3.0
   Copyright: The Qt Company Ltd.
   Source: https://www.qt.io/qt-for-python
   
   PySide6 is licensed under the GNU Lesser General Public License v3.0.
   The full text of the LGPL-3.0 license is available at:
   https://www.gnu.org/licenses/lgpl-3.0.html
   
   Users have the right to:
   - Use this software with PySide6
   - Replace PySide6 with a compatible version
   - Modify PySide6 and use the modified version
   
   PySide6 DLLs are distributed separately in the PySide6/ directory
   to comply with LGPL-3.0 dynamic linking requirements.

================================================================================
```

### 3. Update README.md ✅

Add LGPL compliance section:

```markdown
## 📄 License

AniVault is licensed under the **MIT License**.

### Third-Party Licenses

This software uses **PySide6** (Qt for Python), which is licensed under **LGPL-3.0**.
In compliance with LGPL-3.0:

- PySide6 libraries are **dynamically linked** (separate DLLs)
- Users can **replace** PySide6 with a modified version
- Full LGPL-3.0 license text: [LICENSE-THIRD-PARTY.txt](LICENSE-THIRD-PARTY.txt)

For more details, see [PySide6 LGPL Compliance](docs/compliance/PYSIDE6_LGPL_COMPLIANCE.md).
```

### 4. Add User Replacement Instructions ✅

**File**: `docs/compliance/PYSIDE6_REPLACEMENT.md` (create)

```markdown
# PySide6 Replacement Guide

## How to Replace PySide6 DLLs

In compliance with LGPL-3.0, users can replace PySide6 libraries:

### Step 1: Locate PySide6 Directory
```
anivault/
└── PySide6/  ← Here
    ├── Qt6Core.dll
    ├── Qt6Gui.dll
    └── Qt6Widgets.dll
```

### Step 2: Backup Original Files
```bash
cp -r anivault/PySide6 anivault/PySide6.backup
```

### Step 3: Replace with Custom Version
```bash
# Install your custom PySide6
pip install /path/to/custom-pyside6.whl

# Copy new DLLs
cp -r /path/to/custom/PySide6/* anivault/PySide6/
```

### Step 4: Test
```bash
./anivault/anivault.exe --version
```

## Supported PySide6 Versions

- Minimum: PySide6 6.5.0
- Tested: PySide6 6.7.0
- Maximum: PySide6 6.x (Qt6 compatible)
```

---

## 🧪 Compliance Verification Checklist

- [ ] PyInstaller configured for directory mode (`exclude_binaries=True`)
- [ ] PySide6 DLLs are separate files (not embedded in .exe)
- [ ] `LICENSE-THIRD-PARTY.txt` includes LGPL-3.0 full text
- [ ] README.md mentions LGPL compliance
- [ ] User replacement guide available (`docs/compliance/PYSIDE6_REPLACEMENT.md`)
- [ ] Distribution includes LGPL license file
- [ ] No static linking of PySide6 libraries
- [ ] Users informed of modification rights

---

## 📚 References

1. **LGPL-3.0 Full Text**: https://www.gnu.org/licenses/lgpl-3.0.html
2. **Qt Licensing**: https://www.qt.io/licensing/
3. **PySide6 License**: https://wiki.qt.io/Qt_for_Python
4. **PyInstaller LGPL Compliance**: https://github.com/pyinstaller/pyinstaller/wiki/FAQ

---

## ⚖️ Legal Disclaimer

This document provides guidance based on common LGPL-3.0 interpretations. 
**We are not lawyers**. For legal compliance advice, consult a qualified attorney 
specializing in software licensing.

---

**Last Updated**: 2025-10-08  
**Next Review**: Before public release

