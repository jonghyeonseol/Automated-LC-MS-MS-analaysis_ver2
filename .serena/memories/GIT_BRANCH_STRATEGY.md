# 🌿 Git 브랜치 전략

**수립일**: 2025-12-12
**모델**: Git Flow (간소화)

---

## 브랜치 구조

```
main (production)
  ├── develop (integration)
  │   ├── feature/* (새 기능)
  │   ├── fix/* (버그 수정)
  │   └── refactor/* (리팩토링)
  └── hotfix/* (긴급 패치)
```

---

## 브랜치 역할

| 브랜치 | 용도 | 병합 대상 | 보호 |
|--------|------|-----------|------|
| `main` | 프로덕션 배포 | - | ✅ 보호됨 |
| `develop` | 통합 브랜치 | main | ✅ 보호됨 |
| `feature/*` | 새 기능 개발 | develop | - |
| `fix/*` | 버그 수정 | develop | - |
| `refactor/*` | 코드 리팩토링 | develop | - |
| `hotfix/*` | 긴급 수정 | main + develop | - |

---

## 작업 흐름

### 새 기능 개발
```bash
git checkout develop
git pull origin develop
git checkout -b feature/ISSUE-XXX-description
# ... 작업 ...
git add . && git commit -m "feat: description (#ISSUE-XXX)"
git push -u origin feature/ISSUE-XXX-description
# PR 생성: feature/* → develop
```

### 버그 수정
```bash
git checkout develop
git pull origin develop
git checkout -b fix/ISSUE-XXX-description
# ... 수정 ...
git add . && git commit -m "fix: description (#ISSUE-XXX)"
git push -u origin fix/ISSUE-XXX-description
# PR 생성: fix/* → develop
```

### 긴급 패치 (Hotfix)
```bash
git checkout main
git pull origin main
git checkout -b hotfix/ISSUE-XXX-description
# ... 긴급 수정 ...
git add . && git commit -m "hotfix: description (#ISSUE-XXX)"
git push -u origin hotfix/ISSUE-XXX-description
# PR 생성: hotfix/* → main
# 추가 PR: main → develop (동기화)
```

### 릴리스
```bash
git checkout develop
git pull origin develop
# 모든 테스트 통과 확인
# PR 생성: develop → main
# 태그: git tag -a v2.x.x -m "Release v2.x.x"
```

---

## 커밋 메시지 컨벤션

### 형식
```
<type>: <description> (#ISSUE-XXX)

[optional body]

[optional footer]
```

### 타입
| Type | 설명 | 예시 |
|------|------|------|
| `feat` | 새 기능 | `feat: add Rule 6 validation` |
| `fix` | 버그 수정 | `fix: resolve iterrows error` |
| `refactor` | 리팩토링 | `refactor: extract GodObject` |
| `test` | 테스트 추가 | `test: add V2 processor tests` |
| `docs` | 문서화 | `docs: update API reference` |
| `perf` | 성능 개선 | `perf: vectorize pandas ops` |
| `chore` | 빌드/도구 | `chore: update dependencies` |

---

## PR 규칙

### 제목 형식
```
[TYPE] Brief description (#ISSUE-XXX)
```

### 필수 체크리스트
- [ ] 테스트 추가/수정됨
- [ ] 문서 업데이트됨
- [ ] lint/typecheck 통과
- [ ] 리뷰어 지정됨

### 병합 조건
1. ✅ CI 파이프라인 통과
2. ✅ 1+ 리뷰어 승인
3. ✅ 충돌 해결됨
4. ✅ 최신 develop/main과 동기화

---

## Phase별 브랜치 전략

### Phase 1 (Critical Fixes)
```
develop
  ├── fix/ISSUE-002-iterrows-error
  ├── fix/ISSUE-007-log-p-null
  ├── fix/ISSUE-008-oac-validation
  └── fix/ISSUE-014-api-error-handling
```

### Phase 2 (Performance)
```
develop
  ├── refactor/remove-iterrows
  ├── perf/vectorize-pandas
  └── perf/batch-processing
```

### Phase 3 (Architecture)
```
develop
  ├── refactor/god-object-extraction
  ├── refactor/dependency-injection
  └── refactor/module-consolidation
```

---

## 현재 브랜치 상태

| 브랜치 | 상태 | 마지막 커밋 |
|--------|------|-------------|
| `main` | ✅ 활성 | b47d2b0 |
| `develop` | ✅ 새로 생성 | cc30e49 |
| `origin/Update-(v.2.0.0)` | ⚠️ 오래된 | - |
| `origin/claude/*` | ⚠️ 정리 필요 | - |

---

## 브랜치 정리 계획

### 삭제 대상
```bash
# 병합 완료된 claude/* 브랜치 정리
git push origin --delete claude/codebase-review-011CV54mHmpqUgaPj7tFEa2H
git push origin --delete claude/review-codebase-01Q81JmdxHDWk3s5KM4XdYSg
git push origin --delete add-claude-github-actions-1761029022275
```

---

**다음 단계**: Phase 1 첫 fix 브랜치 생성
