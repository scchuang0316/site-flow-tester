let currentSteps = [];
let presetsMap = {};

document.addEventListener("DOMContentLoaded", () => {
    loadPresets();
});

async function loadPresets() {
    try {
        const res = await fetch("/api/scenarios");
        const scenarios = await res.json();
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
    } catch (err) {
        console.error("Failed to load presets:", err);
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

    const loc = window.location;
    const wsProtocol = loc.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${loc.host}/ws/run-scenario`;

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
        // Fallback to HTTP POST if WebSocket fails
        console.warn("WebSocket fallback to HTTP POST");
        try {
            const res = await fetch("/api/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            document.getElementById("liveGrid").innerHTML = "";
            result.step_results.forEach(sr => appendStepCard(sr));
            finishRun(result, `/reports/report_${result.scenario_id}_${Math.floor(result.start_time)}.html`);
        } catch (e) {
            alert("執行失敗: " + e);
            document.getElementById("runBtn").disabled = false;
            document.getElementById("liveSpinner").style.display = "none";
        }
    };
}

function appendStepCard(res) {
    const grid = document.getElementById("liveGrid");
    const statusClass = res.success ? "status-pass" : "status-fail";
    const statusText = res.success ? '<span style="color: var(--pass-emerald);">✓ PASSED</span>' : '<span style="color: var(--fail-rose);">✗ FAILED</span>';

    const card = document.createElement("div");
    card.className = `live-step-card ${statusClass}`;
    
    let imgContent = '<div style="color: var(--text-dim); font-size: 12px;">無截圖</div>';
    if (res.screenshot_path) {
        imgContent = `<img src="/reports/${res.screenshot_path}" onclick="window.open('/reports/${res.screenshot_path}')">`;
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
