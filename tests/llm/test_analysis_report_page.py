"""AI 分析报告独立页入口。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.frontend import register_frontend


def test_llm_analysis_report_page_has_url() -> None:
    app = FastAPI()
    register_frontend(app)
    client = TestClient(app)
    response = client.get("/llm-analysis-report")
    assert response.status_code == 200
    assert "AI 分析报告" in response.text
    assert "/static/js/llm-assistant/report-page/boot.js" in response.text
    assert "--brabus-red: #d32f2f" in response.text
    assert 'class="sheet"' in response.text
