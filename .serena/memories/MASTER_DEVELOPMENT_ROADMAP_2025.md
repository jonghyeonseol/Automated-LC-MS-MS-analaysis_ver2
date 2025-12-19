# 🗺️ LC-MS/MS Ganglioside Platform - 마스터 개발 로드맵

**생성일**: 2025-12-12
**버전**: 1.0
**상태**: ACTIVE
**총 기간**: 6개월 (2025-12 ~ 2026-05)

---

## 📊 로드맵 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 0   │  PHASE 1   │  PHASE 2   │  PHASE 3   │  PHASE 4   │  PHASE 5  │
│  준비      │  긴급수정  │  성능최적화│  아키텍처  │  품질향상  │  고급기능 │
│  1주       │  2주       │  4주       │  6주       │  6주       │  4주      │
│  12/12-18  │  12/19-01  │  01-02     │  02-03     │  03-04     │  05       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📅 Phase 0: 준비 단계 (1주)
**기간**: 2025-12-12 ~ 2025-12-18
**목표**: 개발 환경 정비 및 기준선 수립

### 작업 목록
- [ ] **P0-1**: 테스트 커버리지 측정 (현재 상태 기록)
- [ ] **P0-2**: 성능 벤치마크 기준선 수립
- [ ] **P0-3**: 기존 메모리 정리 및 통합
- [ ] **P0-4**: CI/CD 파이프라인 검증
- [ ] **P0-5**: 개발 브랜치 전략 수립

### 완료 기준
- [ ] pytest --cov 결과 문서화
- [ ] 성능 기준선 JSON 생성
- [ ] 브랜치 전략 문서 작성

### 산출물
- `baseline_metrics_2025_12.json`
- `BRANCH_STRATEGY.md`

---

## 🚨 Phase 1: 긴급 수정 (2주)
**기간**: 2025-12-19 ~ 2026-01-01
**목표**: 프로덕션 차단 버그 및 보안 이슈 해결

### 작업 목록

#### Week 1: 버그 수정
- [ ] **P1-1**: ISSUE-002 - Rule 5 타입 에러 수정
  - 파일: `ganglioside_processor.py:883-940`
  - 변경: `suffix_group.iloc[i]` → `.to_dict()`
  - 테스트: Rule 5 통합 테스트 추가
  
- [ ] **P1-2**: ISSUE-014 - 데이터 무결성 (키 매핑)
  - 파일: `analysis_service.py:366-368`
  - 변경: 키 매핑 딕셔너리 추가
  - 테스트: predicted_rt NULL 검증

#### Week 2: 보안 강화
- [ ] **P1-3**: ISSUE-006 - CSV Injection 완전 보호
  - 파일: `ganglioside_processor.py:148-153`
  - 변경: 중간 수식 탐지 + 이스케이프
  - 테스트: 악성 CSV 테스트 케이스

- [ ] **P1-4**: 파일 업로드 검증 강화
  - 파일: `analysis_service.py:214-243`
  - 변경: MIME 타입 + 행 수 제한
  - 테스트: 대용량 파일 테스트

### 완료 기준
- [ ] 모든 기존 테스트 통과
- [ ] 4개 신규 테스트 추가 및 통과
- [ ] 보안 스캔 통과

### 산출물
- PR: `fix/critical-bugs-phase1`
- 테스트: `tests/integration/test_phase1_fixes.py`

---

## ⚡ Phase 2: 성능 최적화 (4주)
**기간**: 2026-01-02 ~ 2026-01-29
**목표**: 10x 성능 향상

### 작업 목록

#### Week 1-2: iterrows 제거
- [ ] **P2-1**: ISSUE-001 - ganglioside_processor.py 벡터화
  - 변경: `.iterrows()` → `.apply()` / `.map()`
  - 예상: 10-100x 성능 향상
  
- [ ] **P2-2**: ganglioside_categorizer.py 벡터화

- [ ] **P2-3**: algorithm_validator.py 벡터화

#### Week 3: 메모리 최적화
- [ ] **P2-4**: ISSUE-004 - DataFrame 복사 제거
  - 변경: 불필요한 `.copy()` 제거, 뷰 사용
  - 예상: 50% 메모리 감소

- [ ] **P2-5**: JSON 변환 최적화
  - 변경: 필요한 부분만 변환

#### Week 4: Rule 4/5 알고리즘 최적화
- [ ] **P2-6**: ISSUE-009 - Rule 4 O(n²) → O(n log n)
  - 변경: 병합 기반 처리

- [ ] **P2-7**: Rule 5 정렬 기반 윈도우 스캔

### 완료 기준
- [ ] 1,000 화합물 분석 < 1초
- [ ] 메모리 사용량 50% 감소
- [ ] 성능 벤치마크 통과

### 산출물
- PR: `perf/optimization-phase2`
- 벤치마크: `PERFORMANCE_BENCHMARK_PHASE2.md`

---

## 🏗️ Phase 3: 아키텍처 개선 (6주)
**기간**: 2026-01-30 ~ 2026-03-12
**목표**: 유지보수성 및 확장성 향상

### 작업 목록

#### Week 1-3: God Object 리팩토링
- [ ] **P3-1**: ISSUE-003 - Rule 추상화 설계
  ```
  apps/analysis/rules/
  ├── __init__.py
  ├── base_rule.py          # AbstractRule
  ├── rule1_regression.py   # RegressionRule
  ├── rule2_sugar.py        # SugarCountRule
  ├── rule3_isomer.py       # IsomerRule
  ├── rule4_oacetylation.py # OAcetylationRule
  ├── rule5_fragmentation.py # FragmentationRule
  └── pipeline.py           # RulePipeline
  ```

- [ ] **P3-2**: Rule 1 분리 (가장 복잡)
- [ ] **P3-3**: Rule 2-5 분리
- [ ] **P3-4**: Pipeline 오케스트레이터 구현

#### Week 4-5: v1 프로세서 제거
- [ ] **P3-5**: ISSUE-007 - v1/v2 결과 비교 테스트
- [ ] **P3-6**: v1 deprecation 경고 추가
- [ ] **P3-7**: v1 코드 완전 제거

#### Week 6: 로깅 마이그레이션
- [ ] **P3-8**: ISSUE-005 - print() → logging
  - 130개 print 문 마이그레이션
  - 로그 레벨 정의 (DEBUG/INFO/WARNING/ERROR)

### 완료 기준
- [ ] 파일당 평균 < 300줄
- [ ] 모든 Rule 독립 테스트 가능
- [ ] v1 코드 0줄
- [ ] print() 0개

### 산출물
- PR: `refactor/architecture-phase3`
- 문서: `ARCHITECTURE_V2.md`

---

## ✅ Phase 4: 품질 향상 (6주)
**기간**: 2026-03-13 ~ 2026-04-23
**목표**: 테스트 커버리지 80%+ 및 안정성 향상

### 작업 목록

#### Week 1-2: 테스트 커버리지 확대
- [ ] **P4-1**: Rule 1-5 유닛 테스트 작성
- [ ] **P4-2**: 에지 케이스 테스트
  - n=2 앵커
  - Log P 분산 0
  - 빈 DataFrame
  
- [ ] **P4-3**: 성능 테스트 (>1,000 화합물)

#### Week 3-4: 예외 처리 개선
- [ ] **P4-4**: ISSUE-008 - 30개 except Exception 수정
- [ ] **P4-5**: 커스텀 예외 클래스 정의
  ```python
  class RegressionError(AnalysisError): ...
  class InsufficientDataError(AnalysisError): ...
  class ValidationError(AnalysisError): ...
  ```

#### Week 5-6: 설정 검증 및 문서화
- [ ] **P4-6**: ISSUE-019 - 설정 값 검증 추가
- [ ] **P4-7**: API 문서 완성 (DRF Spectacular)
- [ ] **P4-8**: 사용자 가이드 작성

### 완료 기준
- [ ] 테스트 커버리지 ≥ 80%
- [ ] except Exception 0개
- [ ] API 문서 100% 완성

### 산출물
- PR: `quality/testing-phase4`
- 문서: `API_DOCUMENTATION.md`, `USER_GUIDE.md`

---

## 🚀 Phase 5: 고급 기능 (4주)
**기간**: 2026-04-24 ~ 2026-05-21
**목표**: 프로덕션 고급 기능 활성화

### 작업 목록

#### Week 1-2: 비동기 처리 활성화
- [ ] **P5-1**: Celery 작업 활성화
- [ ] **P5-2**: 대규모 분석 비동기 처리
- [ ] **P5-3**: 진행률 표시 구현

#### Week 3-4: 실시간 기능
- [ ] **P5-4**: Django Channels 활성화
- [ ] **P5-5**: 실시간 로그 스트리밍
- [ ] **P5-6**: 예측 불확실성 표시 (Bayesian std)

### 완료 기준
- [ ] 10,000 화합물 분석 가능
- [ ] 동시 사용자 100명 지원
- [ ] 실시간 진행률 표시

### 산출물
- PR: `feature/async-realtime-phase5`
- 문서: `PRODUCTION_DEPLOYMENT_V2.md`

---

## 📊 성공 지표 (KPI)

| 지표 | 현재 | Phase 2 후 | Phase 4 후 | 최종 |
|------|------|------------|------------|------|
| 분석 속도 (1K) | ~10s | < 1s | < 1s | < 1s |
| 메모리 (1K) | ~500MB | ~250MB | ~200MB | ~150MB |
| 테스트 커버리지 | ~40% | ~50% | ≥80% | ≥85% |
| 코드 라인/파일 | 1,284 | 1,284 | ~300 | ~300 |
| 동시 사용자 | 10 | 10 | 50 | 100 |
| print() 문 | 130 | 130 | 0 | 0 |

---

## 🔄 체크포인트 일정

| 날짜 | 마일스톤 | 검증 항목 |
|------|----------|-----------|
| 2025-12-18 | Phase 0 완료 | 기준선 수립 |
| 2026-01-01 | Phase 1 완료 | 버그 0, 보안 통과 |
| 2026-01-29 | Phase 2 완료 | 성능 10x 향상 |
| 2026-03-12 | Phase 3 완료 | 파일당 <300줄 |
| 2026-04-23 | Phase 4 완료 | 커버리지 80%+ |
| 2026-05-21 | Phase 5 완료 | 프로덕션 준비 |

---

## ⚠️ 리스크 관리

### 높은 리스크
| 리스크 | 확률 | 영향 | 완화 전략 |
|--------|------|------|-----------|
| Phase 3 리팩토링 회귀 | 중 | 높음 | 단계별 마이그레이션, 100% 테스트 |
| 성능 목표 미달 | 낮 | 중 | 조기 벤치마크, 대안 알고리즘 |

### 의존성
- Phase 1 → Phase 2 (버그 수정 후 최적화)
- Phase 2 → Phase 3 (성능 기준선 후 리팩토링)
- Phase 3 → Phase 4 (구조 개선 후 테스트)

---

## 📝 세션 관리 프로토콜

### 세션 시작
```bash
# 1. 프로젝트 활성화
mcp__serena__activate_project("Regression")

# 2. 현재 상태 로드
mcp__serena__read_memory("MASTER_DEVELOPMENT_ROADMAP_2025")
mcp__serena__read_memory("CURRENT_PHASE_STATUS")

# 3. 마지막 체크포인트 확인
mcp__serena__read_memory("LAST_CHECKPOINT")
```

### 작업 중
```bash
# 30분마다 체크포인트
mcp__serena__write_memory("CHECKPOINT_[timestamp]", current_state)

# 주요 결정 기록
mcp__serena__write_memory("DECISION_[date]_[topic]", decision_log)
```

### 세션 종료
```bash
# 1. 진행 상황 저장
mcp__serena__write_memory("CURRENT_PHASE_STATUS", status)

# 2. 다음 세션 작업 기록
mcp__serena__write_memory("NEXT_SESSION_TASKS", tasks)

# 3. 최종 체크포인트
mcp__serena__write_memory("LAST_CHECKPOINT", checkpoint)
```

---

**마지막 업데이트**: 2025-12-12
**다음 리뷰**: 2025-12-18 (Phase 0 완료)
