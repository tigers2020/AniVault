# AniVault Technical Debt Backlog

> Last Updated: 2025-10-10
> Maintainer: Development Team
> Status: Active tracking

---

## 📊 Current Status

| Category | Violations | Priority | Effort | Status | Target Date |
|----------|------------|----------|--------|--------|-------------|
| ~~Benchmark Tests~~ | ~~3~~ | ~~P0~~ | ~~0.5d~~ | ✅ **DONE** | 2025-10-10 |
| ~~Error Handling~~ | ~~0~~ | ~~P1~~ | ~~0d~~ | ✅ **DONE** | 2025-10-10 |
| ~~GUI Mypy Errors~~ | ~~0~~ | ~~P2~~ | ~~0d~~ | ✅ **DONE** | (Previously) |
| **Validation Scripts** | **4 FP** | **P0** | **2-3w** | 📋 Backlog | TBD |
| **Magic Values** | **1,776** | **P1** | **2-3w** | 📋 Backlog | TBD |
| **Function Complexity** | **158** | **P2** | **3-4w** | 📋 Backlog | TBD |

**Total Active Debt**: 3 items (Validation Scripts, Magic Values, Function Complexity)

---

## 🎯 Issue #1: Validation Script False-Positive Reduction

### Overview
Improve code quality validation scripts to reduce false-positives and provide accurate, actionable feedback.

### Problem
- **Current FP Rate**: 83-100% (1,500+ false-positives)
- **Impact**: Noise in reports, developer fatigue, inaccurate tech debt estimates
- **Affected Scripts**: `validate_error_handling.py`, `validate_magic_values.py`

### Examples

#### Error Handling False-Positives
```python
# ✅ Normal control flow (currently flagged as error)
def _confirm_organization(console) -> bool:
    if not Confirm.ask("Proceed?"):
        return False  # User cancelled - NOT an error!
```

#### Magic Values False-Positives
```python
# ✅ Documentation (currently flagged as magic value)
api_key: str = Field(
    description="Your TMDB API key"  # Documentation string - NOT magic!
)
```

### Solution
- Add AST-based context detection
- Distinguish control flow from error handling
- Exclude documentation strings (docstrings, Field descriptions, logging, errors)
- Add configuration file for exclusion rules

### Deliverables
- [ ] Enhanced detection logic with context awareness
- [ ] `.validation-rules.toml` configuration file
- [ ] Test suite for validation scripts (90%+ coverage)
- [ ] Updated CI/pre-commit hooks

### Success Criteria
- False-positive rate < 10% (currently 83-100%)
- Validation reports are actionable
- Developer feedback: "Reports are now useful"

### References
- [Detailed Specification](./tech-debt/validation-script-improvements.md)
- [Magic Values Exclusion Summary](./magic_values_exclusion_summary.md)

**Priority**: 🔴 **P0 - High**
**Effort**: 2-3 weeks
**Owner**: TBD
**Labels**: `tooling`, `developer-experience`, `code-quality`

---

## 🎯 Issue #2: Magic Values Refactoring

### Overview
Replace hardcoded magic values with constants/enums from centralized locations.

### Current State
- **Total**: 1,776 violations (down from 3,130 - 43% reduction!)
- **Real Violations**: ~276 (after filtering false-positives)
- **Files**: 133

### Priority Categories

#### High Priority: Algorithm/Scoring (est. 50 violations)
```python
# ❌ BAD
confidence += 0.5  # Magic threshold
if score > 0.8:    # Magic cutoff

# ✅ GOOD
from anivault.shared.constants import MatchingConfig
confidence += MatchingConfig.CONFIDENCE_BOOST
if score > MatchingConfig.HIGH_CONFIDENCE_THRESHOLD:
```

**Impact**: Scoring logic is opaque, hard to tune
**Effort**: 1 week

#### Medium Priority: Configuration (est. 150 violations)
```python
# ❌ BAD
timeout = 30      # Magic timeout
max_retries = 3   # Magic retry count

# ✅ GOOD
from anivault.shared.constants import APIConfig
timeout = APIConfig.DEFAULT_TIMEOUT
max_retries = APIConfig.MAX_RETRIES
```

**Impact**: Configuration scattered across codebase
**Effort**: 1-2 weeks

#### Low Priority: Metadata (est. 76 violations)
```python
# ❌ BAD
__version__ = "0.1.0"  # Magic version

# ✅ GOOD (acceptable as-is, or extract if reused)
# This is actually fine for package metadata
```

**Impact**: Low (metadata is centralized)
**Effort**: 0.5 weeks

### Approach
1. **Week 1**: Improve validation script (see Issue #1)
2. **Week 2**: Refactor algorithm/scoring magic values
3. **Week 3**: Refactor configuration magic values
4. **Week 4**: Add pre-commit hooks to prevent new violations

### Deliverables
- [ ] Validation script excludes documentation (see Issue #1)
- [ ] `anivault/shared/constants/matching.py` for algorithm values
- [ ] `anivault/shared/constants/api.py` for API configuration
- [ ] Pre-commit hook enforces no new magic values
- [ ] Documentation updated with constant usage guidelines

### Success Criteria
- Real magic value violations < 100 (currently ~276)
- Algorithm/scoring magic values = 0
- Pre-commit prevents new violations
- Code is more maintainable and tunable

### References
- [Draft Analysis](./tech-debt/github-issues-draft.md#issue-1-magic-values-refactoring)
- [One Source of Truth Rule](../.cursor/rules/one_source_of_truth.mdc)

**Priority**: 🟡 **P1 - Medium**
**Effort**: 2-3 weeks (after validation script improvements)
**Owner**: TBD
**Labels**: `tech-debt`, `code-quality`, `refactoring`

---

## 🎯 Issue #3: Function Complexity Reduction

### Overview
Decompose 158 functions that exceed complexity threshold (>10).

### Current State
- **Total**: 158 violations (down from 164 - 3.7% reduction)
- **Threshold**: Complexity > 10, Mixed responsibilities
- **Files**: 133

### Top Offenders

| File | Function | Type | Complexity | Priority |
|------|----------|------|------------|----------|
| cli/json_formatter.py | safe_json_serialize | Complexity | 11 | High |
| cli/organize_handler.py | handle_organize_command | Mixed resp. | ~15 | Med |
| core/matching/engine.py | find_match | Mixed resp. | ~12 | Med |

### Sample Refactoring

#### Before (Complexity: 11)
```python
def safe_json_serialize(obj):
    if isinstance(obj, dict):
        if "results" in obj:
            for item in obj["results"]:
                if isinstance(item, BaseModel):
                    # ...50+ lines of nested logic
```

#### After (Complexity: 4)
```python
def safe_json_serialize(obj):
    if isinstance(obj, dict):
        return _serialize_dict(obj)
    # ...delegated logic

def _serialize_dict(data: dict) -> dict:
    """Helper for dict serialization."""
    if "results" in data:
        return _serialize_results(data)
    # ...focused logic
```

### Approach
1. Extract nested logic → helper functions
2. Apply Single Responsibility Principle
3. Use Strategy/Factory patterns for complex conditionals
4. Add unit tests for extracted functions

### Deliverables
- [ ] Top 20 most complex functions refactored
- [ ] Average complexity < 8 (currently ~10)
- [ ] Unit tests for all extracted helpers
- [ ] Documentation on complexity guidelines

### Success Criteria
- Functions with complexity > 10: < 50 (currently 158)
- Average complexity < 7
- All refactored code has unit tests
- No regressions (existing tests still pass)

### References
- [Draft Analysis](./tech-debt/github-issues-draft.md#issue-2-function-complexity-reduction)
- [Python Development Standards](../.cursor/rules/02_python_development.mdc)

**Priority**: 🟢 **P2 - Low-Medium**
**Effort**: 3-4 weeks
**Owner**: TBD
**Labels**: `tech-debt`, `code-quality`, `refactoring`

---

## 📈 Progress Tracking

### Completed ✅
- **Benchmark Tests** (2025-10-10): 3 test failures fixed, CI unblocked
- **Error Handling** (2025-10-10): 0 real violations (144 were false-positives)
- **GUI Mypy Errors** (Previously): 115 errors resolved

### Active Backlog 📋
1. **Validation Scripts** (P0 - High)
2. **Magic Values** (P1 - Medium) - Depends on #1
3. **Function Complexity** (P2 - Low-Med)

### Metrics Over Time

| Date | Benchmark | Error | GUI Mypy | Magic Values | Function Complexity |
|------|-----------|-------|----------|--------------|---------------------|
| 2025-10-01 | 3 ❌ | 148 ⚠️ | 115 ❌ | 3,130 ⚠️ | 164 ⚠️ |
| 2025-10-10 | **0** ✅ | **0** ✅ | **0** ✅ | 1,776 ⚠️ | 158 ⚠️ |
| Target | 0 | 0 | 0 | <300 | <50 |

**Progress**: 🎉 60% of issues resolved (3/5 categories)

---

## 🔗 Related Documents

- [GitHub Issues Draft](./tech-debt/github-issues-draft.md) - Detailed issue content
- [Validation Script Improvements](./tech-debt/validation-script-improvements.md) - Technical spec
- [AI Code Quality Rules](../.cursor/rules/ai_code_quality_common.mdc) - Standards
- [One Source of Truth](../.cursor/rules/one_source_of_truth.mdc) - Architectural principle

---

## 📝 Notes

### Decision Log

**2025-10-10**: Cancelled Tasks 4-6 (CLI Error Handling)
- **Reason**: Actual violations = 0 (all false-positives from validation script)
- **Evidence**: `validate_error_handling.py` produces 100% false-positive rate
- **Action**: Prioritize validation script improvements first

### Lessons Learned

1. **Always validate the validator**: Validation scripts themselves can have bugs
2. **Context matters**: `return False` is not always an error
3. **Documentation ≠ Magic values**: Docstrings should be excluded
4. **User actions ≠ Silent failures**: User cancellation is normal control flow

---

**Last Review**: 2025-10-10
**Next Review**: After validation script improvements (est. 2-3 weeks)
