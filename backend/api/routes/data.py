"""
데이터 관련 API 라우터
파일 업로드, 분석, 시각화 엔드포인트
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import io
from typing import Dict, Any

from backend.services.dummy.processors import DummyGangliosideDataProcessor, DummyVisualizationService

router = APIRouter(prefix="/api", tags=["data"])

# 서비스 인스턴스 초기화
try:
    from backend.services.data_processor import GangliosideDataProcessor
    from backend.services.visualization_service import VisualizationService
    data_processor = GangliosideDataProcessor()
    visualization_service = VisualizationService()
    print("✅ 실제 분석 모듈 로드 성공")
except ImportError as e:
    print(f"⚠️ 분석 모듈 로드 실패: {e}")
    print("더미 모듈을 사용합니다...")
    data_processor = DummyGangliosideDataProcessor()
    visualization_service = DummyVisualizationService()

# 서비스 접근 함수
def get_data_processor():
    return data_processor

def get_visualization_service():
    return visualization_service


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """CSV 파일 업로드 및 기본 검증"""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="CSV 파일만 업로드 가능합니다.")
        
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        required_columns = ['Name', 'RT', 'Volume', 'Log P', 'Anchor']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"필수 컬럼이 누락되었습니다: {missing_columns}"
            )
        
        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": df.columns.tolist(),
            "anchor_count": len(df[df['Anchor'] == 'T']),
            "rt_range": [float(df['RT'].min()), float(df['RT'].max())],
            "log_p_range": [float(df['Log P'].min()), float(df['Log P'].max())]
        }
        
        return JSONResponse({
            "message": "파일 업로드 성공",
            "filename": file.filename,
            "stats": stats
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류 발생: {str(e)}")


@router.post("/analyze")
async def analyze_data(file: UploadFile = File(...), data_type: str = "Porcine"):
    """업로드된 CSV 데이터에 대한 회귀분석 및 규칙 적용"""
    try:
        # 파일 읽기
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # 필수 컬럼 검증
        required_columns = ['Name', 'RT', 'Volume', 'Log P', 'Anchor']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"필수 컬럼이 누락되었습니다: {missing_columns}"
            )
        
        # 데이터 처리 및 분석 실행
        results = data_processor.process_data(df, data_type=data_type)
        
        return JSONResponse({
            "message": "분석 완료",
            "filename": file.filename,
            "results": results
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


@router.post("/visualize")
async def create_visualizations(file: UploadFile = File(...)):
    """분석 결과 시각화 생성"""
    try:
        # 파일 읽기 및 분석
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # 분석 실행
        analysis_results = data_processor.process_data(df)
        
        # 시각화 생성
        plots = visualization_service.create_all_plots(analysis_results)
        
        return JSONResponse({
            "message": "시각화 생성 완료",
            "plots": plots
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시각화 생성 중 오류 발생: {str(e)}")


# 데이터 프로세서 인스턴스를 외부에서 접근할 수 있도록 export
def get_data_processor():
    """데이터 프로세서 인스턴스 반환"""
    return data_processor
