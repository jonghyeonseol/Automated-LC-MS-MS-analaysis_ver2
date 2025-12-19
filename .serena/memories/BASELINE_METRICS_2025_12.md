# 📊 Phase 0 기준선 지표

**측정일**: 2025-12-12
**환경**: Python 3.13.7, Django 4.2.25, SQLite

---

## 테스트 커버리지 기준선

### 전체 요약
| 지표 | 값 |
|------|-----|
| **전체 커버리지** | 46% |
| **총 테스트 수** | 72 |
| **통과** | 33 (46%) |
| **실패** | 39 (54%) |
| **코드 라인** | 2,475 (apps/ 전체) |
| **미커버 라인** | 1,329 |

### 모듈별 커버리지

| 모듈 | 커버리지 | 상태 |
|------|----------|------|
| `apps/analysis/models.py` | 95% | ✅ 양호 |
| `apps/analysis/services/improved_regression.py` | 89% | ✅ 양호 |
| `apps/core/models.py` | 82% | ✅ 양호 |
| `apps/visualization/views.py` | 80% | ✅ 양호 |
| `apps/analysis/admin.py` | 77% | 🟡 보통 |
| `apps/analysis/services/analysis_service.py` | 77% | 🟡 보통 |
| `apps/analysis/services/ganglioside_processor_v2.py` | 74% | 🟡 보통 |
| `apps/analysis/serializers.py` | 63% | 🟡 보통 |
| `apps/analysis/services/ganglioside_categorizer.py` | 63% | 🟡 보통 |
| `apps/analysis/services/ganglioside_processor.py` | 57% | 🔴 개선 필요 |
| `apps/analysis/views.py` | 26% | 🔴 심각 |
| `apps/analysis/views_web.py` | 26% | 🔴 심각 |
| `apps/core/views.py` | 27% | 🔴 심각 |
| `apps/analysis/tasks.py` | 12% | 🔴 심각 |

### 커버리지 0% 모듈 (미사용/미테스트)
- `apps/analysis/consumers.py` (0%) - WebSocket
- `apps/analysis/routing.py` (0%) - WebSocket 라우팅
- `apps/analysis/services/algorithm_validator.py` (0%)
- `apps/analysis/services/export_service.py` (0%)
- `apps/analysis/services/migrate_to_v2.py` (0%)
- `apps/analysis/services/regression_analyzer.py` (0%)

---

## 테스트 실패 분석

### 실패 원인 분류
| 원인 | 개수 | 비율 |
|------|------|------|
| NOT NULL 제약조건 (log_p) | ~20 | 51% |
| 기타 모델/DB 이슈 | ~15 | 38% |
| Import 오류 | 1 | 3% |
| 기타 | ~3 | 8% |

### 주요 실패 테스트
1. `test_models.py` - Compound 모델 log_p 필수 필드 누락
2. `test_api_endpoints.py` - API 엔드포인트 테스트 전반
3. `test_analysis_workflow.py` - 전체 워크플로우 테스트
4. `test_v2_processor.py` - V2 프로세서 통합 테스트

---

## 성능 기준선 ✅

### V1 프로세서 (Flask 레거시)
**테스트 데이터**: `testwork_user.csv` (323 화합물)

| 지표 | 측정값 | 비고 |
|------|--------|------|
| **처리 시간** | 0.399s | 323 화합물 기준 |
| **현재 메모리** | 0.42 MB | 처리 완료 후 |
| **피크 메모리** | 0.92 MB | 처리 중 최대 |
| **유효 화합물** | 163 (50.5%) | Rule 1-5 통과 |
| **이상치** | 175 (54.2%) | 필터링됨 |

### V1 Rule 1 상세
| 프리픽스 | R² | 샘플 수 |
|----------|-----|---------|
| GD1 | 0.982 | 23 |
| GM1 | 0.991 | 4 |

### V2 프로세서 (Django) ❌
**상태**: 오류 발생
**오류**: `'list' object has no attribute 'iterrows'`
**위치**: `ganglioside_categorizer.py:132`
**원인**: ISSUE-002 (데이터 타입 불일치)

### 성능 목표
| 지표 | 현재 (V1) | 목표 | 상태 |
|------|-----------|------|------|
| 323 화합물 분석 | 0.399s | < 0.5s | ✅ 달성 |
| 1,000 화합물 분석 | ~1.2s (추정) | < 1s | 🟡 개선 필요 |
| 메모리 사용량 | 0.92 MB | < 50MB | ✅ 양호 |
| API 응답 시간 | 미측정 | < 500ms | ⏳ |

---

## CI/CD 상태 ✅

### GitHub Actions 파이프라인 분석
**파일**: `.github/workflows/ci-cd.yml`

| Job | 설명 | 상태 |
|-----|------|------|
| **lint** | Black, isort, flake8 | ✅ 구성됨 |
| **security** | Bandit, Safety | ✅ 구성됨 |
| **test** | pytest + PostgreSQL + Redis | ⚠️ 실패 예상 |
| **build** | Docker 이미지 빌드 | ✅ 구성됨 |
| **deploy** | SSH 배포 (main only) | ⏳ 시크릿 필요 |
| **performance** | Locust (PR only) | ⏳ 미구현 |

### CI/CD 이슈
| 이슈 | 심각도 | 설명 |
|------|--------|------|
| 커버리지 임계값 | 🔴 Critical | 요구 70%, 현재 46% → CI 실패 |
| Celery 태그 구문 | 🟡 Medium | Line 215 태그 형식 오류 |
| GitHub Secrets | 🟡 Medium | DOCKER_*, DEPLOY_* 미설정 |
| 테스트 실패 | 🔴 Critical | 39개 테스트 실패 → CI 실패 |

### Docker 구성 분석
**파일**: `docker-compose.yml`, `Dockerfile`

| 서비스 | 이미지 | 포트 | 상태 |
|--------|--------|------|------|
| postgres | postgres:15-alpine | 5432 | ✅ |
| redis | redis:7-alpine | 6379 | ✅ |
| django | ganglioside:latest | 8000 | ✅ |
| daphne | ganglioside:latest | 8001 | ✅ |
| celery_worker | ganglioside-celery | - | ✅ |
| celery_beat | ganglioside-celery | - | ✅ |
| nginx | nginx:alpine | 80,443 | ✅ |

### Dockerfile 품질
| 항목 | 상태 |
|------|------|
| 멀티스테이지 빌드 | ✅ 적용됨 |
| 비루트 사용자 | ✅ ganglioside (uid:1000) |
| 헬스체크 | ✅ curl /health |
| Python 버전 | 3.9-slim |

### CI 통과 조건
1. ❌ 커버리지 70%+ (현재 46%)
2. ❌ 모든 테스트 통과 (현재 33/72)
3. ⚠️ GitHub Secrets 설정 필요

---

## Git 브랜치 전략 ✅

**모델**: Git Flow (간소화)

| 브랜치 | 역할 | 상태 |
|--------|------|------|
| `main` | 프로덕션 | ✅ 활성 |
| `develop` | 통합 | ✅ 새로 생성 (2025-12-12) |
| `feature/*` | 새 기능 | ⏳ 사용 예정 |
| `fix/*` | 버그 수정 | ⏳ 사용 예정 |
| `hotfix/*` | 긴급 패치 | ⏳ 사용 예정 |

**상세 문서**: `GIT_BRANCH_STRATEGY` 메모리 참조

---

## 개선 우선순위

### 커버리지 개선 대상 (Phase 4)
1. `apps/analysis/views.py` (26% → 70%+)
2. `apps/analysis/tasks.py` (12% → 60%+)
3. `apps/analysis/services/ganglioside_processor.py` (57% → 80%+)

### 테스트 수정 대상 (Phase 1)
1. Compound 모델 fixture 수정 (log_p 필수)
2. API 테스트 fixture 업데이트
3. Celery 테스트 import 오류 수정

---

## Phase 4 목표

| 지표 | 현재 | 목표 |
|------|------|------|
| 전체 커버리지 | 46% | ≥80% |
| 테스트 통과율 | 46% | ≥95% |
| 핵심 서비스 커버리지 | 57-77% | ≥85% |

---

**측정 완료**: 2025-12-12
**다음 측정**: Phase 2 완료 후
