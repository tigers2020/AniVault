# Git 히스토리 API 키 정화 가이드

## 🚨 CRITICAL SECURITY ISSUE

**발견**: `config/config.toml` 파일에 **TMDB API 키가 Git 히스토리에 노출됨**

```toml
# config/config.toml:18 (4개 커밋에 포함)
api_key = "c479...0120"  # 🔴 노출된 키! (redacted for security)  # pragma: allowlist secret
```

**영향 범위**:
- Git 커밋: 4개 (dfbd832, 1d27f14, 0b83475, 902ef7f)
- 노출 기간: 2025-10-08 (오늘)
- Public repo 여부: 확인 필요

---

## ✅ 즉시 조치 (5분 내)

### Step 1: TMDB API 키 무효화 및 재발급

1. **TMDB 웹사이트 로그인**: https://www.themoviedb.org/settings/api
2. **기존 키 삭제**: "c479f9ce20ccbcc06dbcce991a238120" 삭제
3. **새 키 발급**: 새로운 API 키 생성
4. **`.env` 파일에만 저장**:
   ```bash
   echo "TMDB_API_KEY=your_new_api_key_here" > .env
   ```

### Step 2: config.toml을 Git에서 제거

```bash
# config.toml을 Git 추적에서 제거 (이미 .gitignore에 추가됨)
git rm --cached config/config.toml

# 변경사항 커밋
git add .gitignore
git commit -m "security: remove config.toml from Git tracking

- Add config/config.toml to .gitignore
- Remove API key from tracked files
- Users must use config.toml.template and .env file

BREAKING CHANGE: config.toml is no longer tracked in Git.
Copy config.toml.template to config.toml and configure settings."
```

---

## 🔧 Git 히스토리 정화 (선택사항, 주의 필요)

### ⚠️ 주의사항

**히스토리 재작성은 위험합니다:**
- ✅ Private repo → 안전하게 진행 가능
- ❌ Public repo + 이미 클론된 경우 → 완전 정화 불가능
- ❌ 협업 중인 repo → 팀원 작업 손실 위험

### Option A: BFG Repo-Cleaner (권장)

```bash
# 1. BFG 다운로드
# https://rtyley.github.io/bfg-repo-cleaner/

# 2. 백업 생성
git clone --mirror . ../AniVault-backup.git

# 3. API 키가 포함된 파일 제거
java -jar bfg.jar --delete-files config.toml --no-blob-protection

# 4. Git GC 실행
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. 강제 푸시 (주의!)
git push --force --all
git push --force --tags
```

### Option B: git filter-repo (더 안전)

```bash
# 1. git-filter-repo 설치
pip install git-filter-repo

# 2. 백업 생성
git clone . ../AniVault-backup

# 3. API 키 문자열 치환
git filter-repo --replace-text <(echo "c479f9ce20ccbcc06dbcce991a238120==>REDACTED_API_KEY")

# 4. 강제 푸시 (주의!)
git push --force --all
git push --force --tags
```

### Option C: 새 Repo 생성 (가장 안전)

```bash
# 1. 현재 상태 백업
git clone . ../AniVault-clean

# 2. .git 폴더 삭제
cd ../AniVault-clean
rm -rf .git

# 3. 새로운 Git 초기화
git init
git add .
git commit -m "Initial commit - clean history"

# 4. 원격 저장소 재설정
git remote add origin <new-repo-url>
git push -u origin master
```

---

## 🔐 향후 방지 조치

### 1. Pre-commit Hook 설정

```yaml
# .pre-commit-config.yaml 추가
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: |
          (?x)^(
            .*\.json|
            .*\.txt|
            tests/.*
          )$
```

### 2. GitHub Secret Scanning 활성화

GitHub repo settings → Security → Secret scanning 활성화

### 3. 환경변수만 사용

```python
# ✅ GOOD: 환경변수에서 로드
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("TMDB_API_KEY")
if not api_key:
    raise ValueError("TMDB_API_KEY not set in .env file")
```

```python
# ❌ BAD: config 파일에 하드코딩
api_key = "c479f9ce20ccbcc06dbcce991a238120"
```

---

## ✅ 체크리스트

- [ ] TMDB API 키 무효화 및 재발급
- [ ] `.env` 파일에 새 키 설정
- [ ] `config.toml`을 Git 추적에서 제거
- [ ] `.gitignore`에 `config/config.toml` 추가 (✅ 완료)
- [ ] `config.toml.template` 생성 (✅ 완료)
- [ ] (선택) Git 히스토리 정화
- [ ] Pre-commit hook 설정
- [ ] 팀원에게 변경사항 공지

---

## 📞 지원

- **TMDB API 관리**: https://www.themoviedb.org/settings/api
- **BFG Repo-Cleaner**: https://rtyley.github.io/bfg-repo-cleaner/
- **git-filter-repo**: https://github.com/newren/git-filter-repo

---

**작성일**: 2025-10-08
**최종 업데이트**: 2025-10-08
