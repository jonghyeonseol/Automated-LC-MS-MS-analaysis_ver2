"""
API 라우터 초기화
"""

from .data import router as data_router
from .settings import router as settings_router
from .web import router as web_router

__all__ = [
    'data_router',
    'settings_router', 
    'web_router'
]
