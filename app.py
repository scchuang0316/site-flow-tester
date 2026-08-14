import asyncio
import json
import os
from typing import List
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.models import ScenarioConfig, ScenarioResult, StepConfig, ActionType
from core.engine import SiteTesterEngine
from core.reporter import Reporter

app = FastAPI(title="SiteFlowTester - Web Operations Testing Tool")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENARIOS_DIR = os.path.join(BASE_DIR, "scenarios")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(SCENARIOS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

engine = SiteTesterEngine(output_dir=REPORTS_DIR)
reporter = Reporter(output_dir=REPORTS_DIR)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/scenarios")
async def list_scenarios():
    items = []
    for fname in os.listdir(SCENARIOS_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(SCENARIOS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items.append(data)
            except Exception:
                pass
    return items

@app.post("/api/scenarios")
async def create_scenario(scenario: ScenarioConfig):
    file_path = os.path.join(SCENARIOS_DIR, f"{scenario.id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(scenario.model_dump_json(indent=2))
    return {"status": "success", "id": scenario.id, "file": file_path}

@app.post("/api/run", response_model=ScenarioResult)
async def run_test(scenario: ScenarioConfig):
    result = await engine.run_scenario(scenario)
    reporter.save_json(result)
    reporter.generate_html(result)
    return result

@app.get("/api/reports")
async def list_reports():
    reports = []
    for fname in os.listdir(REPORTS_DIR):
        if fname.startswith("report_") and fname.endswith(".html"):
            json_name = fname.replace(".html", ".json")
            json_path = os.path.join(REPORTS_DIR, json_name)
            summary = {"html_file": f"/reports/{fname}", "json_file": f"/reports/{json_name}" if os.path.exists(json_path) else None}
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        summary["title"] = data.get("scenario_title")
                        summary["target_url"] = data.get("target_url")
                        summary["passed"] = data.get("passed")
                        summary["duration_ms"] = data.get("duration_ms")
                        summary["start_time"] = data.get("start_time")
                except Exception:
                    pass
            reports.append(summary)
    reports.sort(key=lambda x: x.get("start_time", 0), reverse=True)
    return reports

@app.websocket("/ws/run-scenario")
async def websocket_run(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        scenario_data = json.loads(data)
        scenario = ScenarioConfig(**scenario_data)

        async def step_progress(step_id: str, res):
            await websocket.send_json({
                "type": "step_progress",
                "step_id": step_id,
                "result": res.model_dump()
            })

        result = await engine.run_scenario(scenario, progress_callback=step_progress)
        reporter.save_json(result)
        html_path = reporter.generate_html(result)

        await websocket.send_json({
            "type": "completed",
            "result": result.model_dump(),
            "html_report": f"/reports/{os.path.basename(html_path)}"
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
