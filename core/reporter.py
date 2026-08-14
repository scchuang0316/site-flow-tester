import json
import os
from typing import Dict, Any
from core.models import ScenarioResult

class Reporter:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def save_json(self, result: ScenarioResult, filename: str = None) -> str:
        if not filename:
            filename = f"report_{result.scenario_id}_{int(result.start_time)}.json"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
        return path

    def generate_html(self, result: ScenarioResult, filename: str = None) -> str:
        if not filename:
            filename = f"report_{result.scenario_id}_{int(result.start_time)}.html"
        path = os.path.join(self.output_dir, filename)

        status_badge_class = "badge-pass" if result.passed else "badge-fail"
        status_text = "PASS" if result.passed else "FAIL"

        steps_html = ""
        for i, step in enumerate(result.step_results, 1):
            step_badge = '<span class="badge badge-pass">PASSED</span>' if step.success else '<span class="badge badge-fail">FAILED</span>'
            err_html = f'<div class="error-msg">{step.error_message}</div>' if step.error_message else ""
            img_html = f'<img src="{step.screenshot_path}" class="step-screenshot" alt="step screenshot">' if step.screenshot_path else '<div class="no-img">No Screenshot</div>'
            
            logs_html = "".join([f'<li class="log-{l.level}">[{l.level.upper()}] {l.message}</li>' for l in step.log_entries])

            steps_html += f"""
            <div class="step-card {'step-fail' if not step.success else ''}">
                <div class="step-header">
                    <span class="step-num">Step {i}</span>
                    <span class="step-title">{step.step_name} ({step.action})</span>
                    <span class="step-duration">{step.duration_ms} ms</span>
                    {step.badge_status if hasattr(step, 'badge_status') else step_badge}
                </div>
                {err_html}
                <div class="step-body">
                    <div class="step-logs">
                        <h4>Log Entries</h4>
                        <ul>{logs_html}</ul>
                    </div>
                    <div class="step-media">
                        {img_html}
                    </div>
                </div>
            </div>
            """

        console_errs_html = ""
        if result.console_errors:
            for ce in result.console_errors:
                console_errs_html += f'<li class="err-console">{ce.message}</li>'
        else:
            console_errs_html = '<li class="no-err">No JS Console errors detected.</li>'

        net_errs_html = ""
        if result.network_errors:
            for ne in result.network_errors:
                net_errs_html += f'<li class="err-net">{ne.message}</li>'
        else:
            net_errs_html = '<li class="no-err">No HTTP network errors (4xx/5xx) detected.</li>'

        html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>測試報告 - {result.scenario_title}</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --pass-color: #10b981;
            --fail-color: #ef4444;
            --accent-color: #3b82f6;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 24px;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        h1 {{ margin: 0; font-size: 24px; }}
        .badge {{
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 14px;
        }}
        .badge-pass {{ background-color: rgba(16, 185, 129, 0.2); color: var(--pass-color); border: 1px solid var(--pass-color); }}
        .badge-fail {{ background-color: rgba(239, 68, 68, 0.2); color: var(--fail-color); border: 1px solid var(--fail-color); }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .stat-num {{ font-size: 24px; font-weight: bold; margin-top: 8px; color: var(--accent-color); }}
        .step-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            margin-bottom: 16px;
            padding: 16px;
        }}
        .step-card.step-fail {{ border-color: var(--fail-color); }}
        .step-header {{ display: flex; align-items: center; gap: 12px; font-size: 16px; font-weight: bold; }}
        .step-num {{ color: var(--accent-color); }}
        .step-duration {{ margin-left: auto; color: var(--text-sub); font-size: 14px; }}
        .error-msg {{ background: rgba(239, 68, 68, 0.15); color: #fca5a5; padding: 12px; border-radius: 6px; margin-top: 12px; font-family: monospace; }}
        .step-body {{ display: grid; grid-template-columns: 1fr 280px; gap: 16px; margin-top: 12px; }}
        .step-logs ul {{ margin: 0; padding-left: 20px; font-size: 13px; color: var(--text-sub); }}
        .step-logs li {{ margin-bottom: 4px; }}
        .log-error {{ color: #fca5a5; }}
        .step-screenshot {{ width: 100%; border-radius: 6px; border: 1px solid var(--card-border); }}
        .no-img {{ display: flex; align-items: center; justify-content: center; height: 120px; background: #090d16; color: var(--text-sub); border-radius: 6px; font-size: 12px; }}
        .section-box {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
        .section-box h3 {{ margin-top: 0; font-size: 18px; border-bottom: 1px solid var(--card-border); padding-bottom: 8px; }}
        ul.err-list {{ padding-left: 20px; font-family: monospace; font-size: 13px; }}
        li.err-console {{ color: #fca5a5; }}
        li.err-net {{ color: #fcd34d; }}
        li.no-err {{ color: var(--pass-color); list-style: none; padding-left: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>{result.scenario_title}</h1>
                <div style="color: var(--text-sub); font-size: 14px; margin-top: 4px;">Target URL: <a href="{result.target_url}" target="_blank" style="color: var(--accent-color);">{result.target_url}</a></div>
            </div>
            <div>
                <span class="badge {status_badge_class}">{status_text}</span>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div>總耗時</div>
                <div class="stat-num">{result.duration_ms} ms</div>
            </div>
            <div class="stat-card">
                <div>總步驟數</div>
                <div class="stat-num">{result.total_steps}</div>
            </div>
            <div class="stat-card">
                <div>成功步驟</div>
                <div class="stat-num" style="color: var(--pass-color);">{result.passed_steps}</div>
            </div>
            <div class="stat-card">
                <div>失敗步驟</div>
                <div class="stat-num" style="color: var(--fail-color);">{result.failed_steps}</div>
            </div>
        </div>

        <div class="section-box">
            <h3>JS Console 監控紀錄 ({len(result.console_errors)} 則警報)</h3>
            <ul class="err-list">{console_errs_html}</ul>
        </div>

        <div class="section-box">
            <h3>Network 請求異常紀錄 ({len(result.network_errors)} 則警報)</h3>
            <ul class="err-list">{net_errs_html}</ul>
        </div>

        <h2>詳細步驟執行過程</h2>
        {steps_html}
    </div>
</body>
</html>
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return path
