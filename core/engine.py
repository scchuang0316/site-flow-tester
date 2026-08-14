import asyncio
import os
import time
import trace
import traceback
from typing import Callable, Optional, List
from playwright.async_api import async_playwright, Page, Response, ConsoleMessage

from core.models import (
    ScenarioConfig,
    ScenarioResult,
    StepConfig,
    StepResult,
    ActionType,
    LogEntry
)

class SiteTesterEngine:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "screenshots"), exist_ok=True)

    async def run_scenario(
        self,
        scenario: ScenarioConfig,
        progress_callback: Optional[Callable[[str, StepResult], None]] = None
    ) -> ScenarioResult:
        start_time = time.time()
        console_errors: List[LogEntry] = []
        network_errors: List[LogEntry] = []
        step_results: List[StepResult] = []
        passed_steps = 0
        failed_steps = 0

        async with async_playwright() as p:
            browser_name = scenario.browser_type.lower()
            if browser_name == "firefox":
                browser = await p.firefox.launch(headless=scenario.headless)
            elif browser_name == "webkit":
                browser = await p.webkit.launch(headless=scenario.headless)
            else:
                browser = await p.chromium.launch(headless=scenario.headless)

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) SiteFlowTester/1.0"
            )
            page = await context.new_page()

            # Listener for JS console logs & errors
            def handle_console(msg: ConsoleMessage):
                if msg.type in ["error", "warning"]:
                    console_errors.append(LogEntry(
                        level="console_err" if msg.type == "error" else "warning",
                        message=f"[{msg.type.upper()}] {msg.text}",
                        details={"location": msg.location}
                    ))

            # Listener for uncaught JS page errors
            def handle_page_error(error):
                console_errors.append(LogEntry(
                    level="console_err",
                    message=f"[Page Exception] {str(error)}",
                    details={"traceback": traceback.format_exc()}
                ))

            # Listener for Network failures
            def handle_response(response: Response):
                if response.status >= 400:
                    network_errors.append(LogEntry(
                        level="network_err",
                        message=f"[HTTP {response.status}] {response.url}",
                        details={"status": response.status, "status_text": response.status_text}
                    ))

            page.on("console", handle_console)
            page.on("pageerror", handle_page_error)
            page.on("response", handle_response)

            # Navigate to target URL first if provided and page is blank and first step is not GOTO
            if scenario.target_url and page.url == "about:blank" and (not scenario.steps or scenario.steps[0].action != ActionType.GOTO):
                try:
                    await page.goto(scenario.target_url, wait_until="domcontentloaded", timeout=15000)
                except Exception as e:
                    console_errors.append(LogEntry(
                        level="error",
                        message=f"Initial page navigation failed: {str(e)}"
                    ))

            for idx, step in enumerate(scenario.steps):
                step_start = time.time()
                logs: List[LogEntry] = []
                screenshot_file = None
                success = False
                err_msg = None

                try:
                    logs.append(LogEntry(level="info", message=f"Executing step: {step.name} ({step.action})"))
                    
                    if step.action == ActionType.GOTO:
                        target = step.value or scenario.target_url
                        await page.goto(target, wait_until="domcontentloaded", timeout=step.timeout)
                    
                    elif step.action == ActionType.CLICK:
                        if not step.selector:
                            raise ValueError("Selector is required for click action")
                        await page.wait_for_selector(step.selector, state="visible", timeout=step.timeout)
                        await page.click(step.selector, timeout=step.timeout)
                    
                    elif step.action == ActionType.FILL:
                        if not step.selector:
                            raise ValueError("Selector is required for fill action")
                        await page.wait_for_selector(step.selector, state="visible", timeout=step.timeout)
                        await page.fill(step.selector, step.value or "", timeout=step.timeout)
                    
                    elif step.action == ActionType.SELECT_OPTION:
                        if not step.selector:
                            raise ValueError("Selector is required for select_option action")
                        await page.select_option(step.selector, step.value or "", timeout=step.timeout)

                    elif step.action == ActionType.WAIT_FOR:
                        if not step.selector:
                            raise ValueError("Selector is required for wait_for action")
                        await page.wait_for_selector(step.selector, timeout=step.timeout)

                    elif step.action == ActionType.ASSERT_TEXT:
                        if not step.selector:
                            raise ValueError("Selector is required for assert_text action")
                        await page.wait_for_selector(step.selector, timeout=step.timeout)
                        content = await page.text_content(step.selector)
                        expected = step.value or ""
                        if expected.lower() not in (content or "").lower():
                            raise AssertionError(f"Expected text '{expected}' not found in '{content}'")

                    elif step.action == ActionType.ASSERT_URL:
                        current_url = page.url
                        expected = step.value or ""
                        if expected not in current_url:
                            raise AssertionError(f"Expected URL to contain '{expected}', got '{current_url}'")

                    elif step.action == ActionType.HOVER:
                        if not step.selector:
                            raise ValueError("Selector is required for hover action")
                        await page.hover(step.selector, timeout=step.timeout)

                    elif step.action == ActionType.SCROLL:
                        await page.evaluate("window.scrollBy(0, 400)")

                    elif step.action == ActionType.SCREENSHOT:
                        pass # Handled below automatically for all steps

                    # Capture step screenshot
                    shot_name = f"{scenario.id}_step_{idx+1}_{int(time.time()*1000)}.png"
                    shot_rel_path = os.path.join("screenshots", shot_name)
                    shot_abs_path = os.path.join(self.output_dir, shot_rel_path)
                    await page.screenshot(path=shot_abs_path, full_page=False)
                    screenshot_file = shot_rel_path

                    success = True
                    passed_steps += 1
                    logs.append(LogEntry(level="info", message=f"Step '{step.name}' completed successfully."))

                except Exception as e:
                    success = False
                    failed_steps += 1
                    err_msg = str(e)
                    logs.append(LogEntry(level="error", message=f"Step '{step.name}' failed: {err_msg}"))
                    
                    # Take failure screenshot
                    try:
                        shot_name = f"{scenario.id}_err_step_{idx+1}_{int(time.time()*1000)}.png"
                        shot_rel_path = os.path.join("screenshots", shot_name)
                        shot_abs_path = os.path.join(self.output_dir, shot_rel_path)
                        await page.screenshot(path=shot_abs_path)
                        screenshot_file = shot_rel_path
                    except Exception:
                        pass

                step_duration = (time.time() - step_start) * 1000
                res = StepResult(
                    step_id=step.id,
                    step_name=step.name,
                    action=step.action.value,
                    success=success,
                    duration_ms=round(step_duration, 2),
                    error_message=err_msg,
                    screenshot_path=screenshot_file,
                    log_entries=logs
                )
                step_results.append(res)

                if progress_callback:
                    await progress_callback(step.id, res)

                # Small delay between steps for visual clarity
                await asyncio.sleep(0.3)

            # Performance timing metrics
            perf_metrics = {}
            try:
                perf_nav = await page.evaluate("() => JSON.stringify(performance.getEntriesByType('navigation')[0] || {})")
                import json
                perf_metrics = json.loads(perf_nav)
            except Exception:
                pass

            await browser.close()

        end_time = time.time()
        overall_duration = round((end_time - start_time) * 1000, 2)
        overall_passed = failed_steps == 0

        return ScenarioResult(
            scenario_id=scenario.id,
            scenario_title=scenario.title,
            target_url=scenario.target_url,
            start_time=start_time,
            end_time=end_time,
            duration_ms=overall_duration,
            passed=overall_passed,
            total_steps=len(scenario.steps),
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            step_results=step_results,
            console_errors=console_errors,
            network_errors=network_errors,
            performance_metrics=perf_metrics
        )
