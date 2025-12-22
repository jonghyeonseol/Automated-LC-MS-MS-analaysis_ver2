# 🔄 세션 관리 프로토콜

**버전**: 1.0
**생성일**: 2025-12-12
**목적**: 작업 연속성 보장 및 컨텍스트 유지

---

## 📋 세션 라이프사이클

```
┌─────────────────────────────────────────────────────────────────┐
│                        세션 시작                                 │
│  1. 프로젝트 활성화                                              │
│  2. 메모리 로드 (3개 필수)                                       │
│  3. 마지막 체크포인트 확인                                       │
│  4. TodoWrite 작업 목록 갱신                                     │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        작업 진행                                 │
│  • 30분마다 체크포인트 저장                                      │
│  • 주요 결정 기록                                                │
│  • TodoWrite 상태 업데이트                                       │
│  • 문제 발생 시 블로커 기록                                      │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        세션 종료                                 │
│  1. 진행 상황 저장 (CURRENT_PHASE_STATUS)                        │
│  2. 다음 작업 기록 (NEXT_SESSION_TASKS)                          │
│  3. 최종 체크포인트 저장                                         │
│  4. 메모리 정리 (임시 체크포인트 삭제)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 세션 시작 체크리스트

### 필수 단계

```python
# Step 1: 프로젝트 활성화
mcp__serena__activate_project("Regression")

# Step 2: 필수 메모리 로드 (순서대로)
mcp__serena__read_memory("MASTER_DEVELOPMENT_ROADMAP_2025")  # 전체 계획
mcp__serena__read_memory("CURRENT_PHASE_STATUS")              # 현재 상태
mcp__serena__read_memory("NEXT_SESSION_TASKS")                # 이번 작업

# Step 3: 마지막 체크포인트 확인
mcp__serena__list_memories()  # CHECKPOINT_ 접두사 확인
mcp__serena__read_memory("LAST_CHECKPOINT")

# Step 4: 작업 목록 설정
TodoWrite([현재 Phase 작업들])
```

### 컨텍스트 질문 (자가 점검)
1. ❓ 현재 어느 Phase인가?
2. ❓ 이번 세션의 목표는?
3. ❓ 블로커가 있는가?
4. ❓ 마지막 세션에서 미완료 작업은?

---

## ⏱️ 작업 중 체크포인트

### 30분 체크포인트 (자동)
```python
checkpoint = {
    "timestamp": "2025-12-12T14:30:00",
    "phase": "Phase 0",
    "current_task": "P0-1",
    "progress": "테스트 커버리지 측정 중",
    "completed_in_session": ["P0-3"],
    "blockers": [],
    "notes": ""
}
mcp__serena__write_memory(f"CHECKPOINT_{timestamp}", checkpoint)
```

### 주요 결정 기록
```python
decision = {
    "date": "2025-12-12",
    "topic": "브랜치 전략",
    "decision": "GitFlow 채택",
    "rationale": "복잡한 릴리즈 관리 필요",
    "alternatives_considered": ["GitHub Flow", "Trunk-based"],
    "impact": "Phase 1부터 적용"
}
mcp__serena__write_memory("DECISION_2025_12_12_branch_strategy", decision)
```

### 문제 발생 시
```python
blocker = {
    "date": "2025-12-12",
    "issue": "pytest 실행 오류",
    "impact": "P0-1 작업 지연",
    "workaround": "가상환경 재생성",
    "status": "resolved/pending"
}
mcp__serena__write_memory("BLOCKER_2025_12_12_pytest", blocker)
```

---

## 🏁 세션 종료 체크리스트

### 필수 단계

```python
# Step 1: 진행 상황 업데이트
# CURRENT_PHASE_STATUS 메모리의 작업 상태 갱신
mcp__serena__edit_memory("CURRENT_PHASE_STATUS", 
    "P0-1 | 테스트 커버리지 측정 | ⏳ 대기",
    "P0-1 | 테스트 커버리지 측정 | ✅ 완료",
    "literal")

# Step 2: 다음 세션 작업 기록
next_tasks = """
# 다음 세션 작업 목록
**날짜**: 2025-12-13
**Phase**: Phase 0

## 예정 작업
1. [ ] P0-2: 성능 벤치마크 기준선 수립
2. [ ] P0-4: CI/CD 파이프라인 검증

## 컨텍스트
- P0-1 완료됨: 커버리지 42%
- 벤치마크 스크립트 작성 필요

## 참고 파일
- tests/performance/benchmark.py (신규 생성 필요)
"""
mcp__serena__write_memory("NEXT_SESSION_TASKS", next_tasks)

# Step 3: 최종 체크포인트
final_checkpoint = """
# 최종 체크포인트: 2025-12-12

## 완료 작업
- P0-1: 테스트 커버리지 측정 (42%)
- P0-3: 메모리 정리 완료

## 미완료 작업
- P0-2: 성능 벤치마크 (다음 세션)

## 다음 단계
- 벤치마크 스크립트 작성
- CI/CD 검증
"""
mcp__serena__write_memory("LAST_CHECKPOINT", final_checkpoint)

# Step 4: 임시 체크포인트 정리 (선택적)
# 오래된 CHECKPOINT_ 메모리 삭제
```

---

## 📊 메모리 구조

### 영구 메모리 (삭제 금지)
| 메모리 이름 | 용도 | 업데이트 주기 |
|-------------|------|---------------|
| `MASTER_DEVELOPMENT_ROADMAP_2025` | 전체 6개월 계획 | Phase 변경 시 |
| `CURRENT_PHASE_STATUS` | 현재 Phase 상태 | 매 세션 |
| `SESSION_MANAGEMENT_PROTOCOL` | 이 문서 | 필요 시 |

### 반영구 메모리 (Phase 완료 후 정리)
| 메모리 이름 | 용도 | 생명주기 |
|-------------|------|----------|
| `NEXT_SESSION_TASKS` | 다음 세션 작업 | 세션별 갱신 |
| `LAST_CHECKPOINT` | 마지막 상태 | 세션별 갱신 |
| `DECISION_*` | 주요 결정 기록 | Phase 완료까지 |
| `BLOCKER_*` | 문제 기록 | 해결까지 |

### 임시 메모리 (정기 정리)
| 메모리 이름 | 용도 | 정리 주기 |
|-------------|------|-----------|
| `CHECKPOINT_*` | 30분 체크포인트 | 세션 종료 시 |

---

## 🔍 컨텍스트 복구 시나리오

### 시나리오 1: 정상 재개
```
1. activate_project → read_memory(3개) → 작업 계속
```

### 시나리오 2: 세션 중단 (비정상 종료)
```
1. activate_project
2. list_memories → CHECKPOINT_ 찾기
3. 가장 최근 CHECKPOINT 읽기
4. 상태 복구 후 작업 재개
```

### 시나리오 3: 장기 중단 (1주 이상)
```
1. activate_project
2. MASTER_DEVELOPMENT_ROADMAP_2025 읽기 (전체 맥락)
3. CURRENT_PHASE_STATUS 읽기 (현재 위치)
4. 필요 시 Phase 상태 재평가
5. 새 TodoWrite 작성
```

---

## ✅ 품질 체크리스트

### 세션 시작 시
- [ ] 3개 필수 메모리 로드 완료
- [ ] 현재 Phase 작업 목록 확인
- [ ] 블로커 확인 및 해결 계획

### 세션 중
- [ ] 30분마다 체크포인트 저장
- [ ] 주요 결정 기록
- [ ] TodoWrite 상태 최신화

### 세션 종료 시
- [ ] CURRENT_PHASE_STATUS 업데이트
- [ ] NEXT_SESSION_TASKS 작성
- [ ] LAST_CHECKPOINT 저장
- [ ] 임시 메모리 정리

---

## 🎯 명령어 빠른 참조

```bash
# 프로젝트 활성화
mcp__serena__activate_project("Regression")

# 메모리 목록
mcp__serena__list_memories()

# 메모리 읽기
mcp__serena__read_memory("MEMORY_NAME")

# 메모리 쓰기
mcp__serena__write_memory("MEMORY_NAME", content)

# 메모리 수정
mcp__serena__edit_memory("MEMORY_NAME", old, new, "literal")

# 메모리 삭제
mcp__serena__delete_memory("MEMORY_NAME")
```

---

**프로토콜 버전**: 1.0
**최종 업데이트**: 2025-12-12
