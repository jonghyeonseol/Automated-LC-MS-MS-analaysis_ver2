"""
설정 관련 API 라우터
분석 파라미터 설정, 조회, 리셋 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Dict, Any

from .data import get_data_processor

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
async def get_current_settings():
    """현재 분석 설정 조회"""
    data_processor = get_data_processor()
    
    return {
        "current_settings": {
            "outlier_threshold": data_processor.outlier_threshold,
            "r2_threshold": data_processor.r2_threshold,
            "rt_tolerance": data_processor.rt_tolerance
        },
        "default_settings": {
            "outlier_threshold": 3.0,
            "r2_threshold": 0.99,
            "rt_tolerance": 0.1
        },
        "setting_ranges": {
            "outlier_threshold": {"min": 1.0, "max": 5.0, "step": 0.1},
            "r2_threshold": {"min": 0.90, "max": 0.999, "step": 0.001},
            "rt_tolerance": {"min": 0.05, "max": 0.5, "step": 0.01}
        }
    }


@router.post("/settings")
async def update_settings(
    outlier_threshold: float = 3.0,
    r2_threshold: float = 0.99,
    rt_tolerance: float = 0.1
):
    """분석 설정 업데이트"""
    try:
        data_processor = get_data_processor()
        
        # 설정 범위 검증
        if not (1.0 <= outlier_threshold <= 5.0):
            raise HTTPException(status_code=400, detail="outlier_threshold must be between 1.0 and 5.0")
        if not (0.90 <= r2_threshold <= 0.999):
            raise HTTPException(status_code=400, detail="r2_threshold must be between 0.90 and 0.999")
        if not (0.05 <= rt_tolerance <= 0.5):
            raise HTTPException(status_code=400, detail="rt_tolerance must be between 0.05 and 0.5")
        
        # 설정 업데이트
        data_processor.outlier_threshold = outlier_threshold
        data_processor.r2_threshold = r2_threshold  
        data_processor.rt_tolerance = rt_tolerance
        
        print(f"⚙️ 설정 업데이트: outlier={outlier_threshold}, r2={r2_threshold}, rt={rt_tolerance}")
        
        return {
            "message": "Settings updated successfully",
            "updated_settings": {
                "outlier_threshold": outlier_threshold,
                "r2_threshold": r2_threshold,
                "rt_tolerance": rt_tolerance
            },
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"설정 업데이트 중 오류 발생: {str(e)}")


@router.post("/reset-settings")
async def reset_settings():
    """설정을 기본값으로 리셋"""
    try:
        data_processor = get_data_processor()
        
        data_processor.outlier_threshold = 3.0
        data_processor.r2_threshold = 0.99
        data_processor.rt_tolerance = 0.1
        
        print("🔄 설정 리셋: 모든 값이 기본값으로 복원됨")
        
        return {
            "message": "Settings reset to default values",
            "default_settings": {
                "outlier_threshold": 3.0,
                "r2_threshold": 0.99,
                "rt_tolerance": 0.1
            },
            "timestamp": pd.Timestamp.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"설정 리셋 중 오류 발생: {str(e)}")


@router.get("/analysis-preview")
async def analysis_preview(
    outlier_threshold: float = 3.0,
    r2_threshold: float = 0.99,
    rt_tolerance: float = 0.1,
    data_type: str = "Porcine"
):
    """설정 변경에 따른 분석 결과 미리보기 (샘플 데이터 사용)"""
    try:
        data_processor = get_data_processor()
        
        # 샘플 데이터 생성
        sample_data = {
            'Name': ['GD1a(36:1;O2)', 'GM1a(36:1;O2)', 'GM3(36:1;O2)', 'GD3(36:1;O2)', 'GT1b(36:1;O2)'],
            'RT': [9.572, 10.452, 10.606, 10.126, 8.701],
            'Volume': [1000000, 500000, 2000000, 800000, 1200000],
            'Log P': [1.53, 4.00, 7.74, 5.27, -0.94],
            'Anchor': ['T', 'F', 'F', 'T', 'T']
        }
        df = pd.DataFrame(sample_data)
        
        # 임시 설정으로 분석
        original_settings = {
            'outlier_threshold': data_processor.outlier_threshold,
            'r2_threshold': data_processor.r2_threshold,
            'rt_tolerance': data_processor.rt_tolerance
        }
        
        # 미리보기용 설정 적용
        data_processor.outlier_threshold = outlier_threshold
        data_processor.r2_threshold = r2_threshold
        data_processor.rt_tolerance = rt_tolerance
        
        # 분석 실행
        preview_results = data_processor.process_data(df, data_type=data_type)
        
        # 원래 설정 복원
        data_processor.outlier_threshold = original_settings['outlier_threshold']
        data_processor.r2_threshold = original_settings['r2_threshold']
        data_processor.rt_tolerance = original_settings['rt_tolerance']
        
        return {
            "message": "Analysis preview completed",
            "preview_settings": {
                "outlier_threshold": outlier_threshold,
                "r2_threshold": r2_threshold,
                "rt_tolerance": rt_tolerance,
                "data_type": data_type
            },
            "preview_results": {
                "success_rate": preview_results['statistics']['success_rate'],
                "valid_compounds": preview_results['statistics']['valid_compounds'],
                "outliers": preview_results['statistics']['outliers'],
                "setting_impact": preview_results.get('setting_impact', {}),
                "quality_grade": preview_results['analysis_summary']['data_quality']
            },
            "comparison_note": "Preview based on sample data - actual results may vary"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"미리보기 중 오류 발생: {str(e)}")
