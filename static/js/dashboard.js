let currentSteps = [];
let presetsMap = {};
let apiBaseUrl = "";

const BUILTIN_PRESETS = [
    {
        id: "scenario_wikipedia_search",
        title: "Wikipedia 多步驟導覽與搜尋斷言測試",
        target_url: "https://www.wikipedia.org",
        headless: true,
        browser_type: "chromium",
        steps: [
            { id: "step_1", name: "造訪 Wikipedia 首頁", action: "goto", value: "https://www.wikipedia.org", timeout: 15000 },
            { id: "step_2", name: "輸入搜尋關鍵字 'Python'", action: "fill", selector: "input#searchInput", value: "Python", timeout: 5000 },
            { id: "step_3", name: "點擊搜尋按鈕", action: "click", selector: "button[type='submit']", timeout: 5000 },
            { id: "step_4", name: "驗證頁面包含 Python 標題", action: "assert_text", selector: "h1#firstHeading, h1", value: "Python", timeout: 10000 }
        ]
    },
    {
        id: "scenario_httpbin_form",
        title: "HTTPBin 表單填寫與回應斷言測試",
        target_url: "https://httpbin.org/forms/post",
        headless: true,
        browser_type: "chromium",
        steps: [
            { id: "step_1", name: "造訪 HTTPBin 表單頁面", action: "goto", value: "https://httpbin.org/forms/post", timeout: 10000 },
            { id: "step_2", name: "輸入顧客姓名", action: "fill", selector: "input[name='custname']", value: "測試員 Antigravity", timeout: 5000 },
            { id: "step_3", name: "輸入電話號碼", action: "fill", selector: "input[name='custtel']", value: "0912345678", timeout: 5000 },
            { id: "step_4", name: "點擊大尺寸披薩選項", action: "click", selector: "input[value='large']", timeout: 5000 },
            { id: "step_5", name: "送出表單", action: "click", selector: "button", timeout: 5000 },
            { id: "step_6", name: "驗證伺服器回應包含輸入姓名", action: "assert_text", selector: "body", value: "Antigravity", timeout: 10000 }
        ]
    }
];

document.addEventListener("DOMContentLoaded", () => {
    loadPresets();
});

async function detectApiBaseUrl() {
    // 1. If running on local server directly
    if (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") {
        apiBaseUrl = "";
        return true;
    }

    // 2. If running on Cloudflare Pages, try connecting to local Python FastAPI backend
    try {
        const res = await fetch("http://127.0.0.1:8000/api/scenarios");
        if (res.ok) {
            apiBaseUrl = "http://127.0.0.1:8000";
            return true;
        }
    } catch (e) {}

    apiBaseUrl = "";
    return false;
}

async function loadPresets() {
    const hasBackend = await detectApiBaseUrl();
    let scenarios = BUILTIN_PRESETS;

    if (hasBackend) {
        try {
            const fetchUrl = apiBaseUrl ? `${apiBaseUrl}/api/scenarios` : "/api/scenarios";
            const res = await fetch(fetchUrl);
            if (res.ok && res.headers.get("content-type")?.includes("application/json")) {
                scenarios = await res.json();
            }
        } catch (err) {
            console.warn("Using built-in presets fallback:", err);
        }
    } else {
        const consoleBox = document.getElementById("tabConsole");
        if (consoleBox) {
            consoleBox.innerHTML = '<div class="log-line warn">[提示] 目前正在 Cloudflare Pages 雲端靜態模式下預覽儀表板。如需點擊「啟動測試偵測」執行 Playwright 自動化測試，請確認本機 Python FastAPI 服務 (http://127.0.0.1:8000) 已啟動。</div>';
        }
    }

    const select = document.getElementById("presetSelect");
    select.innerHTML = '<option value="">-- 自訂新情境 --</option>';

    scenarios.forEach(sc => {
        presetsMap[sc.id] = sc;
        const opt = document.createElement("option");
        opt.value = sc.id;
        opt.textContent = sc.title;
        select.appendChild(opt);
    });

    select.addEventListener("change", (e) => {
        const scId = e.target.value;
        if (scId && presetsMap[scId]) {
            applyScenario(presetsMap[scId]);
        } else {
            currentSteps = [];
            renderSteps();
        }
    });

    if (scenarios.length > 0) {
        select.value = scenarios[0].id;
        applyScenario(scenarios[0]);
    }
}

function applyScenario(sc) {
    document.getElementById("scenarioTitle").value = sc.title || "";
    document.getElementById("targetUrl").value = sc.target_url || "";
    document.getElementById("browserType").value = sc.browser_type || "chromium";
    document.getElementById("headlessSelect").value = sc.headless ? "true" : "false";
    currentSteps = sc.steps || [];
    renderSteps();
}

function renderSteps() {
    const listContainer = document.getElementById("stepsList");
    listContainer.innerHTML = "";

    currentSteps.forEach((step, idx) => {
        const item = document.createElement("div");
        item.className = "step-item";
        item.innerHTML = `
            <div class="step-item-header">
                <span class="step-badge-num">步驟 ${idx + 1}</span>
                <button class="btn-remove-step" onclick="removeStep(${idx})"><i class="fa-solid fa-trash"></i></button>
            </div>
            <div class="form-group" style="margin-bottom: 8px;">
                <input type="text" class="form-control" placeholder="步驟名稱" value="${step.name || ''}" onchange="updateStep(${idx}, 'name', this.value)">
            </div>
            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                <select class="form-control" style="width: 140px;" onchange="updateStep(${idx}, 'action', this.value)">
                    <option value="goto" ${step.action === 'goto' ? 'selected' : ''}>goto (導覽)</option>
                    <option value="click" ${step.action === 'click' ? 'selected' : ''}>click (點擊)</option>
                    <option value="fill" ${step.action === 'fill' ? 'selected' : ''}>fill (輸入)</option>
                    <option value="assert_text" ${step.action === 'assert_text' ? 'selected' : ''}>assert_text</option>
                    <option value="wait_for" ${step.action === 'wait_for' ? 'selected' : ''}>wait_for (等待)</option>
                    <option value="assert_url" ${step.action === 'assert_url' ? 'selected' : ''}>assert_url</option>
                    <option value="hover" ${step.action === 'hover' ? 'selected' : ''}>hover (懸停)</option>
                    <option value="scroll" ${step.action === 'scroll' ? 'selected' : ''}>scroll (滾動)</option>
                </select>
                <input type="text" class="form-control" placeholder="CSS 選擇器 (Selector)" value="${step.selector || ''}" onchange="updateStep(${idx}, 'selector', this.value)">
            </div>
            <div>
                <input type="text" class="form-control" placeholder="輸入數值 / 預期目標" value="${step.value || ''}" onchange="updateStep(${idx}, 'value', this.value)">
            </div>
        `;
        listContainer.appendChild(item);
    });
}

function addStepItem() {
    currentSteps.push({
        id: "step_" + Date.now(),
        name: "新步驟 " + (currentSteps.length + 1),
        action: "click",
        selector: "",
        value: "",
        timeout: 10000
    });
    renderSteps();
}

function removeStep(idx) {
    currentSteps.splice(idx, 1);
    renderSteps();
}

function updateStep(idx, key, val) {
    if (currentSteps[idx]) {
        currentSteps[idx][key] = val;
    }
}

async function runScenario() {
    const title = document.getElementById("scenarioTitle").value;
    const targetUrl = document.getElementById("targetUrl").value;
    const browserType = document.getElementById("browserType").value;
    const headless = document.getElementById("headlessSelect").value === "true";

    if (!targetUrl) {
        alert("請輸入目標網站 URL");
        return;
    }

    const hasBackend = await detectApiBaseUrl();

    if (!hasBackend && window.location.hostname !== "127.0.0.1" && window.location.hostname !== "localhost") {
        alert("【未連線到測試引擎】\n\n您目前正在 Cloudflare Pages 雲端靜態模式下檢視儀表板。\n由於 Playwright 無頭瀏覽器需要 Python 引擎環境，請確保您的本機測試服務已啟動：\n\n/Users/i_scchuang/site_flow_tester/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000");
        return;
    }

    const payload = {
        id: "run_" + Date.now(),
        title: title || "自訂測試",
        target_url: targetUrl,
        browser_type: browserType,
        headless: headless,
        steps: currentSteps
    };

    // Reset UI State
    document.getElementById("statStatus").textContent = "執行中...";
    document.getElementById("statStatus").className = "stat-value val-blue";
    document.getElementById("liveSpinner").style.display = "inline-block";
    document.getElementById("runBtn").disabled = true;
    document.getElementById("liveGrid").innerHTML = "";
    document.getElementById("tabConsole").innerHTML = "";
    document.getElementById("tabNetwork").innerHTML = "";
    document.getElementById("viewReportBtn").style.display = "none";

    const targetHost = apiBaseUrl || window.location.origin;

    // WebSocket attempt
    let wsHost = targetHost.replace(/^http/, "ws");
    const wsUrl = `${wsHost}/ws/run-scenario`;

    try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            ws.send(JSON.stringify(payload));
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === "step_progress") {
                appendStepCard(msg.result);
            } else if (msg.type === "completed") {
                finishRun(msg.result, msg.html_report);
            } else if (msg.type === "error") {
                alert("測試發生錯誤: " + msg.message);
                document.getElementById("statStatus").textContent = "異常 Error";
                document.getElementById("statStatus").className = "stat-value val-fail";
                document.getElementById("runBtn").disabled = false;
                document.getElementById("liveSpinner").style.display = "none";
            }
        };

        ws.onerror = async () => {
            fallbackToHttpRun(payload, targetHost);
        };
    } catch (e) {
        fallbackToHttpRun(payload, targetHost);
    }
}

async function fallbackToHttpRun(payload, targetHost) {
    try {
        const runUrl = targetHost ? `${targetHost}/api/run` : "/api/run";
        const res = await fetch(runUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            if (res.status === 405) {
                throw new Error("Cloudflare Pages 靜態節點不支援 POST 請求。請確認 Python FastAPI 後端服務 (http://127.0.0.1:8000) 已啟動。");
            }
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
        }

        const contentType = res.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            throw new Error("伺服器並未回傳 JSON 格式。請確認 Python FastAPI 後端服務 (http://127.0.0.1:8000) 已啟動。");
        }

        const result = await res.json();
        document.getElementById("liveGrid").innerHTML = "";
        result.step_results.forEach(sr => appendStepCard(sr));
        finishRun(result, `${targetHost}/reports/report_${result.scenario_id}_${Math.floor(result.start_time)}.html`);
    } catch (e) {
        alert("執行失敗: " + e.message);
        document.getElementById("statStatus").textContent = "未連線";
        document.getElementById("statStatus").className = "stat-value val-fail";
        document.getElementById("runBtn").disabled = false;
        document.getElementById("liveSpinner").style.display = "none";
    }
}

function appendStepCard(res) {
    const grid = document.getElementById("liveGrid");
    const statusClass = res.success ? "status-pass" : "status-fail";
    const statusText = res.success ? '<span style="color: var(--pass-emerald);">✓ PASSED</span>' : '<span style="color: var(--fail-rose);">✗ FAILED</span>';

    const card = document.createElement("div");
    card.className = `live-step-card ${statusClass}`;
    
    let imgContent = '<div style="color: var(--text-dim); font-size: 12px;">無截圖</div>';
    const reportHost = apiBaseUrl || "";
    if (res.screenshot_path) {
        imgContent = `<img src="${reportHost}/reports/${res.screenshot_path}" onclick="window.open('${reportHost}/reports/${res.screenshot_path}')">`;
    }

    let errToast = '';
    if (res.error_message) {
        errToast = `<div class="err-toast">${res.error_message}</div>`;
    }

    card.innerHTML = `
        <div class="live-card-head">
            <span>${res.step_name} (${res.action})</span>
            <span>${statusText}</span>
        </div>
        <div class="live-card-body">
            <div class="live-img-box">${imgContent}</div>
            <div style="font-size: 12px; color: var(--text-muted); display: flex; justify-content: space-between;">
                <span>耗時</span>
                <span>${res.duration_ms} ms</span>
            </div>
            ${errToast}
        </div>
    `;
    grid.appendChild(card);
}

function finishRun(result, htmlReportUrl) {
    document.getElementById("runBtn").disabled = false;
    document.getElementById("liveSpinner").style.display = "none";

    const passed = result.passed;
    document.getElementById("statStatus").textContent = passed ? "通過 (PASS)" : "未通過 (FAIL)";
    document.getElementById("statStatus").className = passed ? "stat-value val-pass" : "stat-value val-fail";

    document.getElementById("statDuration").textContent = `${result.duration_ms} ms`;
    document.getElementById("statSteps").textContent = `${result.passed_steps} / ${result.total_steps}`;
    document.getElementById("statAlerts").textContent = `${result.console_errors.length} / ${result.network_errors.length}`;

    // Populate Console Logs Tab
    const consoleBox = document.getElementById("tabConsole");
    document.getElementById("cntConsole").textContent = result.console_errors.length;
    if (result.console_errors.length === 0) {
        consoleBox.innerHTML = '<div class="log-line info">✓ 畫面未偵測到任何 JavaScript Console Error。</div>';
    } else {
        consoleBox.innerHTML = result.console_errors.map(ce => `<div class="log-line err">[Console Error] ${ce.message}</div>`).join('');
    }

    // Populate Network Logs Tab
    const netBox = document.getElementById("tabNetwork");
    document.getElementById("cntNetwork").textContent = result.network_errors.length;
    if (result.network_errors.length === 0) {
        netBox.innerHTML = '<div class="log-line info">✓ 未偵測到 HTTP 4xx/5xx 網路連線錯誤。</div>';
    } else {
        netBox.innerHTML = result.network_errors.map(ne => `<div class="log-line warn">[Network Error] ${ne.message}</div>`).join('');
    }

    if (htmlReportUrl) {
        const btn = document.getElementById("viewReportBtn");
        btn.href = htmlReportUrl;
        btn.style.display = "inline-block";
    }
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

    document.getElementById(tabId).style.display = "block";
    if (tabId === 'tabConsole') {
        event.target.classList.add("active");
    } else {
        event.target.classList.add("active");
    }
}
