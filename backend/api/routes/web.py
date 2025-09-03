"""
웹 인터페이스 라우터
HTML 페이지 서빙
"""

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["web"])

# 템플릿 설정
template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
templates = Jinja2Templates(directory=template_dir)


@router.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """브라우저 테스트 페이지"""
    return templates.TemplateResponse(
        "simple_test_page.html", {"request": request}
    )


@router.get("/analyzer", response_class=HTMLResponse)
async def analyzer_page(request: Request):
    """Ganglioside 분석기 메인 페이지"""
    return templates.TemplateResponse(
        "simple_test_page.html", {"request": request}
    )


@router.get("/interactive", response_class=HTMLResponse)
async def interactive_page(request: Request):
    """인터랙티브 분석 페이지"""
    return templates.TemplateResponse(
        "simple_test_page.html", {"request": request}
    )


@router.get("/", response_class=HTMLResponse)
async def root_redirect(request: Request):
    """루트 페이지 - 분석기로 리다이렉트"""
    return templates.TemplateResponse(
        "simple_test_page.html", {"request": request}
    )
