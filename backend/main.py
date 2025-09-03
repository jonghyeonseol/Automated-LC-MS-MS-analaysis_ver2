"""
Ganglioside Analyzer - FastAPI Main Application
산성 당지질 LC-MS/MS 데이터 자동 분석 웹 서비스
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# API 라우터들 import 에러를 방지하기 위해 try-except 사용
try:
    from backend.api.routes.data import router as data_router
    from backend.api.routes.settings import router as settings_router
    from backend.api.routes.web import router as web_router

    print("✅ 모든 라우터 모듈이 성공적으로 로드되었습니다.")
except ImportError as e:
    print(f"⚠️ 라우터 로드 실패: {e}")
    print("기본 라우터를 사용합니다...")
    from fastapi import APIRouter

    # 기본 라우터들 생성
    data_router = APIRouter(prefix="/api", tags=["data"])
    settings_router = APIRouter(prefix="/api", tags=["settings"])
    web_router = APIRouter(tags=["web"])

# FastAPI 앱 초기화
app = FastAPI(
    title="🧬 Ganglioside Analyzer",
    description="산성 당지질 LC-MS/MS 데이터 자동 분석 시스템",
    version="2.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 라우터 등록
app.include_router(data_router)
app.include_router(settings_router)
app.include_router(web_router)


# 루트 엔드포인트
@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "🧬 Ganglioside Analyzer API v2.0",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "data": "/api/upload, /api/analyze, /api/visualize",
            "settings": "/api/settings, /api/reset-settings, /api/analysis-preview",
            "web": "/analyzer, /test",
        },
    }


# API 상태 확인 엔드포인트
@app.get("/api/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "service": "ganglioside-analyzer", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
