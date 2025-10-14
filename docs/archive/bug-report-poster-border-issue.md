# Bug Report: Persistent Border on GroupCardWidget Poster Images

## 🐛 Problem Statement

**Issue**: Poster images in `GroupCardWidget` continue to display unwanted borders despite multiple QSS and Python code fixes.

**Severity**: Medium (Visual/UX issue)
**Component**: `GroupCardWidget` / Theme System
**Status**: Unresolved

---

## 📸 Visual Evidence

Screenshot shows persistent borders around poster images in all group cards, creating visual clutter that contradicts the intended modern flat design.

**Expected**: Clean, borderless poster images
**Actual**: 1px solid border visible around all poster images

---

## 🔍 Investigation History

### Attempt 1: QSS Theme File Modifications
**Action**: Added `border: none` to poster labels in theme files
```css
/* common.qss:505-521 */
QLabel#posterLabel { border: none; }
QLabel#posterInitial { border: none; }
QLabel#posterFolder { border: none; }
```
**Result**: ❌ Failed - Borders still visible
**Commit**: `a3f8b2c` - "style(gui): Remove borders from poster images"

---

### Attempt 2: Python Frame Style Removal
**Action**: Removed `setFrameStyle()` calls from `GroupCardWidget._setup_card()`
```python
# Removed:
# self.setFrameStyle(QFrame.Box | QFrame.Raised)
# self.setLineWidth(1)
```
**Result**: ❌ Failed - Borders still visible
**Commit**: `e8f3a1d` - "fix(gui): Remove hardcoded frame border"

---

### Attempt 3: Explicit NoFrame Setting
**Action**: Added explicit `setFrameShape(QFrame.NoFrame)` in Python
```python
self.setFrameShape(QFrame.NoFrame)
```
**Result**: ❌ Failed - Borders still visible
**Commit**: `f9b4e2a` - "fix(gui): Explicitly set NoFrame shape"

---

### Attempt 4: QSS Cascade Override for GroupCardWidget
**Action**: Added GroupCardWidget override immediately after QFrame rule
```css
/* common.qss:274-282 */
QFrame { border: 1px solid; }
GroupCardWidget { border: none; }  /* Override */
```
**Result**: ✅ Partial Success - Card borders removed
**But**: ❌ Poster borders still visible
**Commit**: `d7c5b3f` - "fix(gui): Override QFrame border for GroupCardWidget"

---

### Attempt 5: QSS Cascade Override for Poster Labels
**Action**: Added poster label overrides after QFrame rule
```css
/* common.qss:284-289 */
QLabel#posterLabel,
QLabel#posterInitial,
QLabel#posterFolder {
    border: none;
}
```
**Result**: ❌ Failed - Borders STILL visible
**Commit**: `5ae58ed` - "fix(gui): Override QFrame border for poster QLabels"

---

## 🤔 Root Cause Analysis

### Hypothesis 1: QSS Specificity Issue
**Theory**: QFrame rule has higher specificity than ID selectors
**Evidence**:
- QFrame rule at line 274 applies `border: 1px solid` globally
- ID selector overrides (`#posterLabel`) should have higher specificity
- But borders persist despite ID selector overrides

**Status**: ❓ Unlikely - CSS specificity rules suggest ID selectors should win

---

### Hypothesis 2: QSS Loading Order Issue
**Theory**: Theme files are loaded in incorrect order, causing overrides to be ineffective
**Evidence**:
- `@import` resolution in ThemeManager loads `common.qss` first
- `light.qss`/`dark.qss` loaded after common
- Overrides in common.qss should be effective

**Status**: ❓ Possible - Need to verify actual QSS loading order at runtime

---

### Hypothesis 3: Widget Hierarchy Issue
**Theory**: Borders are being drawn by a different widget, not the poster QLabel itself
**Evidence**:
- `GroupCardWidget` uses complex layout with nested widgets
- Poster may be wrapped in additional container widgets
- Container widgets might have borders

**Status**: ⚠️ **High Probability** - Need to inspect widget tree

---

### Hypothesis 4: Python Code Setting Borders Elsewhere
**Theory**: Border is set programmatically in code we haven't checked yet
**Evidence**:
- Only checked `_setup_card()` and `_create_poster_widget()`
- May be set in event handlers, update methods, or other functions
- May be inherited from parent class initialization

**Status**: ⚠️ **High Probability** - Need comprehensive code search

---

### Hypothesis 5: Qt Default Stylesheet Override
**Theory**: Qt's default platform stylesheet is overriding our custom QSS
**Evidence**:
- Qt applies platform-specific default styles
- Our stylesheet may not completely override defaults
- `QLabel` may have platform-specific border rendering

**Status**: ❓ Possible - Need to check Qt stylesheet debugging

---

## 🔬 Required Investigation Steps

### Step 1: Runtime Widget Inspection
```python
# Add to GroupCardWidget.__init__() or _setup_card()
import logging
logger = logging.getLogger(__name__)

# Log poster widget hierarchy
poster = self.findChild(QLabel, "posterLabel")
if poster:
    parent = poster.parent()
    logger.debug(f"Poster parent: {parent.__class__.__name__}")
    logger.debug(f"Poster frameShape: {poster.frameShape()}")
    logger.debug(f"Poster lineWidth: {poster.lineWidth()}")
    logger.debug(f"Poster styleSheet: {poster.styleSheet()}")
```

### Step 2: Comprehensive Code Search
```bash
# Search for any border-related code in GUI widgets
rg "setFrame|setLineWidth|setStyleSheet.*border|border.*:" \
   src/anivault/gui/widgets/ \
   --type py --context 5
```

### Step 3: QSS Debug Logging
```python
# In ThemeManager.apply_theme()
logger.debug("=== Final QSS Content ===")
logger.debug(qss_content)
logger.debug("=== End QSS Content ===")
```

### Step 4: Qt Inspector Tool
Use Qt's built-in widget inspector to identify which exact widget has the border:
```python
# Enable Qt widget inspector (add to app.py)
app.setAttribute(Qt.AA_DontUseNativeMenuBar)
app.setStyleSheet("QWidget { border: 1px solid red; }")  # Debug all widgets
```

---

## 📊 Testing Matrix

| Test Case | QSS Override | Python Code | Expected | Actual | Status |
|-----------|-------------|-------------|----------|--------|--------|
| Card border removal | ✅ Added | ✅ NoFrame | No border | No border | ✅ Pass |
| Poster border removal | ✅ Added | N/A | No border | **Has border** | ❌ Fail |
| Hover state | ✅ Added | N/A | Border on hover | Border on hover | ✅ Pass |
| Theme switch | ✅ Both themes | N/A | No border both themes | **Has border both** | ❌ Fail |

---

## 🎯 Next Actions

1. **[HIGH PRIORITY]** Add runtime widget inspection logging
2. **[HIGH PRIORITY]** Comprehensive grep for border-related code
3. **[MEDIUM]** Enable QSS debug logging in ThemeManager
4. **[MEDIUM]** Test with Qt widget inspector tool
5. **[LOW]** Compare with minimal reproducible example (isolated QLabel with poster)

---

## 📝 Additional Notes

### QSS Specificity Rules (Reminder)
```
Specificity Priority (highest to lowest):
1. Inline styles (setStyleSheet() on specific widget)
2. ID selectors (#posterLabel)
3. Class selectors (.QLabel)
4. Type selectors (QLabel)
5. Universal selectors (*)
```

### QSS Cascade Order (Current)
```
1. common.qss loaded via @import
   - QFrame { border: 1px solid; }         (Line 274)
   - GroupCardWidget { border: none; }     (Line 280)
   - QLabel#posterLabel { border: none; }  (Line 285)
2. light.qss / dark.qss loaded
   - QLabel#posterLabel colors            (Line 675/657)
```

### Potential Workaround (Nuclear Option)
If all else fails, use `!important` (anti-pattern, but effective):
```css
QLabel#posterLabel {
    border: none !important;
}
```

---

## 🔗 Related Files

- `src/anivault/gui/widgets/group_card_widget.py` (Widget implementation)
- `src/anivault/resources/themes/common.qss` (Common styles)
- `src/anivault/resources/themes/light.qss` (Light theme)
- `src/anivault/resources/themes/dark.qss` (Dark theme)
- `src/anivault/gui/themes/theme_manager.py` (Theme loading)

---

## 👥 Stakeholders

- **Reporter**: User
- **Investigator**: Yoon Do-hyun (CLI)
- **QA**: Choi Ro-geon
- **UI/UX**: Lina Hartman

---

**Last Updated**: 2025-10-12
**Report Version**: 1.0
**Status**: Open - Investigation Ongoing
