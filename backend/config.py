"""
Application Configuration
환경변수 및 설정 관리
"""

from pydantic import BaseModel
from typing import Optional
import os


class Settings(BaseModel):
    """애플리케이션 설정"""
    
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/ganglioside_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Application
    secret_key: str = "your-secret-key-here"
    debug: bool = True
    
    # File Upload
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "data/uploads"
    output_dir: str = "data/outputs"
    
    # Analysis Parameters
    regression_r2_threshold: float = 0.99
    outlier_threshold: float = 3.0
    rt_tolerance: float = 0.1
    
    # Visualization
    plot_width: int = 800
    plot_height: int = 600
    plot_dpi: int = 100


# 전역 설정 인스턴스
settings = Settings()

# 디렉토리 생성
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)