// ── State ────────────────────────────────────────────────────────
let appState = {
    cycle: 1,
    perception_output: null,
    manufacturer_profile: null,
    assessment: null,
    risk_assessment: null,
    planning_response: null,
    mohid_plan: null,
    actions: null
};

// Human-approval toggles (keyed by step number 1-6, true = requires approval)
let humanApproval = { 1: true, 2: true, 3: true, 4: true, 5: true, 6: true };

const TOGGLE_KEY = 'supplyagent_toggles';

function loadToggles() {
    try {
        const saved = JSON.parse(localStorage.getItem(TOGGLE_KEY));
        if (saved) {
            for (let i = 1; i <= 6; i++) {
                if (typeof saved[i] === 'boolean') {
                    humanApproval[i] = saved[i];
                }
            }
        }
    } catch (_) {}
    // Sync checkbox UI
    for (let i = 1; i <= 6; i++) {
        const el = document.getElementById(`toggle-step-${i}`);
        if (el) el.checked = humanApproval[i];
    }
}

function saveToggles() {
    localStorage.setItem(TOGGLE_KEY, JSON.stringify(humanApproval));
}

function onToggleChange(step, isOn) {
    humanApproval[step] = isOn;
    saveToggles();
    // Update auto notice visibility if we're currently on that step
    const notice = document.getElementById(`auto-notice-${step}`);
    if (notice) {
        notice.classList.toggle('hidden', isOn);
    }
}

// ── Helpers ───────────────────────────────────────────────────────
let customizeStep = 0;

function esc(s) {
    if (s == null) return '';
    const div = document.createElement('div');
    div.textContent = String(s);
    return div.innerHTML;
}

const views = ['welcome', 'step-1', 'step-2', 'step-3', 'step-4', 'step-5', 'step-6'];

function showLoader(text) {
    document.getElementById('loader-text').innerText = text;
    document.getElementById('loader').classList.remove('hidden');
}

function hideLoader() {
    document.getElementById('loader').classList.add('hidden');
}

function setView(viewId) {
    views.forEach(v => {
        document.getElementById(`view-${v}`).classList.remove('active');
    });
    document.getElementById(`view-${viewId}`).classList.add('active');

    if (viewId !== 'welcome') {
        document.querySelector('.content-header').style.display = 'flex';
        const stepNum = parseInt(viewId.split('-')[1]);
        updateSidebar(stepNum);
        // Toggle auto-proceed notice banner
        const notice = document.getElementById(`auto-notice-${stepNum}`);
        if (notice) {
            notice.classList.toggle('hidden', humanApproval[stepNum]);
        }
    } else {
        document.querySelector('.content-header').style.display = 'none';
        updateSidebar(0);
    }
}

function updateSidebar(currentStep) {
    document.querySelectorAll('.step').forEach(el => {
        const step = parseInt(el.getAttribute('data-step'));
        el.classList.remove('active', 'completed');
        if (step < currentStep) {
            el.classList.add('completed');
        } else if (step === currentStep) {
            el.classList.add('active');
        }
    });

    const titles = [
        "",
        "1. Perception Layer",
        "2. Risk Intelligence",
        "3. Planning & Decision",
        "4. Autonomous Action",
        "5. Memory & Reflection",
        "6. Decision Transparency"
    ];

    const descs = [
        "",
        "Ingesting news and building context from mock ERP.",
        "Assessing disruption probability and financial exposure.",
        "Simulating scenarios and selecting the optimal mitigation plan.",
        "Drafting supplier communications and system alerts.",
        "Logging event outcome for future similar disruptions.",
        "Audit trail of assumptions and validation."
    ];

    if (currentStep > 0 && currentStep <= 6) {
        document.getElementById('current-step-title').innerText = titles[currentStep];
        document.getElementById('current-step-desc').innerText = descs[currentStep];
        document.getElementById('cycle-badge').innerText = `Cycle ${appState.cycle}`;
    }
}

// ── Action buttons visibility based on toggle ─────────────────────
function setActionBarVisible(stepNum, visible) {
    const viewEl = document.getElementById(`view-step-${stepNum}`);
    if (!viewEl) return;
    const bar = viewEl.querySelector('.action-bar');
    if (bar) bar.style.display = visible ? '' : 'none';
}

// ── AI mode status badge ──────────────────────────────────────────
async function checkAIMode() {
    try {
        const res = await fetch('/health');
        const data = await res.json();
        const badge = document.getElementById('ai-mode-badge');
        if (data.gemini_live_mode) {
            badge.className = 'ai-mode-badge live';
            badge.innerHTML = '<span class="dot"></span> Gemini Live';
        } else {
            badge.className = 'ai-mode-badge mock';
            badge.innerHTML = '<span class="dot"></span> Mock Mode';
        }
    } catch (_) {
        const badge = document.getElementById('ai-mode-badge');
        if (badge) badge.innerHTML = '<span class="dot"></span> Offline';
    }
}

// ── Wizard flow ───────────────────────────────────────────────────
async function startWizard() {
    await fetchStep1();
}

async function proceedToStep(step) {
    if (step === 2) await fetchStep2();
    if (step === 3) await fetchStep3();
    if (step === 4) await fetchStep4();
    if (step === 5) await fetchStep5();
    if (step === 6) await fetchStep6();
}

// ── Bubble helpers ────────────────────────────────────────────────
let allRisks = [];  // full array from /api/step1_all_risks

function getRiskColor(score) {
    // Returns an RGBA color based on risk score 1-10
    if (score <= 3)  return { bg: 'rgba(51,214,159,0.45)',  glow: 'rgba(51,214,159,0.55)',  border: 'rgba(51,214,159,0.6)' };
    if (score <= 5)  return { bg: 'rgba(255,220,80,0.45)',  glow: 'rgba(255,220,80,0.55)',  border: 'rgba(255,220,80,0.6)' };
    if (score <= 7)  return { bg: 'rgba(255,150,60,0.45)',  glow: 'rgba(255,150,60,0.55)',  border: 'rgba(255,150,60,0.6)' };
    return              { bg: 'rgba(255,80,100,0.5)',   glow: 'rgba(255,80,100,0.6)',   border: 'rgba(255,80,100,0.7)' };
}

function getRiskSize(score) {
    // Maps score 1-10 to diameter in px (80px → 170px)
    const min = 80, max = 170;
    return Math.round(min + ((score - 1) / 9) * (max - min));
}

function selectBubble(index) {
    const risk = allRisks[index];
    if (!risk) return;

    // Update appState so subsequent steps use this risk
    appState.assessment         = risk.assessment;
    appState.perception_output  = risk.perception_output;
    appState.manufacturer_profile = risk.manufacturer_profile;

    // Highlight selected bubble
    document.querySelectorAll('.risk-bubble').forEach((el, i) => {
        el.classList.toggle('selected', i === index);
    });

    // Populate detail panel
    const a = risk.assessment;
    const score = a.risk_score;
    const colors = getRiskColor(score);

    const ring = document.getElementById('s1-detail-score-ring');
    ring.style.borderColor = colors.border;
    ring.style.boxShadow = `0 0 20px ${colors.glow}`;
    document.getElementById('s1-detail-score').textContent = score;
    document.getElementById('s1-detail-score').style.color = colors.border;
    document.getElementById('s1-detail-headline').textContent = risk.news_headline;
    document.getElementById('s1-detail-location').innerHTML = `<i class="fa-solid fa-location-dot"></i> ${risk.news_location || 'Unknown location'}`;
    document.getElementById('s1-detail-summary').textContent  = a.news_summary;
    document.getElementById('s1-detail-mitigation').textContent = a.recommended_mitigation;
    document.getElementById('s1-detail-erp').textContent = `${risk.erp_context_size} parts tracked`;
    document.getElementById('s1-detail-health').textContent = risk.supplier_health_summary || 'Healthy';

    const prob   = document.getElementById('s1-detail-prob');
    const impact = document.getElementById('s1-detail-impact');
    prob.textContent   = `Prob: ${a.probability}`;
    impact.textContent = `Impact: ${a.impact_level}`;
    prob.style.background   = colors.bg;
    impact.style.background = colors.bg;
    prob.style.borderColor  = colors.border;
    impact.style.borderColor = colors.border;
    prob.style.color   = '#fff';
    impact.style.color = '#fff';

    document.getElementById('s1-detail').classList.remove('hidden');

    // Enable approve button and update text
    const btn = document.getElementById('s1-approve-btn');
    btn.disabled = false;
    btn.innerHTML = `Analyse: <strong>${risk.news_headline}</strong> &nbsp;<i class="fa-solid fa-arrow-right"></i>`;
}

function renderBubbles(risks) {
    const arena = document.getElementById('bubble-arena');
    arena.innerHTML = '';
    document.getElementById('s1-risk-count').textContent = risks.length;

    // Float animation variants — rotated round-robin so no two adjacent bubbles are the same
    const floatVariants = ['floatA', 'floatB', 'floatC'];
    // Per-bubble durations (seconds) — spread out so they are clearly out of phase
    const floatDurations = [11, 13.5, 9.8, 14.2, 10.6, 12.3];
    // Per-bubble delays — offset so each bubble is at a different point in its cycle
    const floatDelays    = [0, -3.4, -7.1, -1.8, -5.5, -9.2];

    risks.forEach((risk, i) => {
        const score = risk.assessment.risk_score;
        const size  = getRiskSize(score);
        const colors = getRiskColor(score);
        const entranceDelay = i * 0.15;

        const bubble = document.createElement('div');
        bubble.className = 'risk-bubble';
        bubble.style.width  = `${size}px`;
        bubble.style.height = `${size}px`;
        bubble.style.background = colors.bg;
        bubble.style.border = `1.5px solid ${colors.border}`;
        bubble.style.boxShadow = `0 8px 32px ${colors.glow}, inset 0 1px 0 rgba(255,255,255,0.15)`;
        // Entrance animation
        bubble.style.animationDelay    = `${entranceDelay}s`;
        bubble.style.animationDuration = '0.55s';

        // After entrance finishes, switch to floating
        const floatName     = floatVariants[i % floatVariants.length];
        const floatDuration = floatDurations[i % floatDurations.length];
        const floatDelay    = floatDelays[i % floatDelays.length];
        const entranceTotalMs = (entranceDelay + 0.55) * 1000;

        setTimeout(() => {
            if (bubble.isConnected) {
                bubble.style.animation = `${floatName} ${floatDuration}s ${floatDelay}s ease-in-out infinite`;
            }
        }, entranceTotalMs);

        // Short label: first 3 words of headline
        const shortLabel = risk.news_headline.split(' ').slice(0, 3).join(' ');
        bubble.innerHTML = `
            <div class="bubble-score">${score}</div>
            <div class="bubble-label">${shortLabel}</div>
        `;
        bubble.addEventListener('click', () => selectBubble(i));
        arena.appendChild(bubble);
    });
}


async function fetchStep1() {
    showLoader('Ingesting all disruption signals...');
    try {
        const res = await fetch('/api/step1_all_risks');
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Perception failed (${res.status})`);
        }
        const data = await res.json();
        allRisks = data.risks;

        // Reset state
        appState.assessment = null;
        appState.perception_output = null;
        appState.manufacturer_profile = null;

        // Reset detail panel and approve button
        document.getElementById('s1-detail').classList.add('hidden');
        const btn = document.getElementById('s1-approve-btn');
        btn.disabled = true;
        btn.innerHTML = 'Select a risk above, then Approve &amp; Proceed <i class="fa-solid fa-arrow-right"></i>';

        renderBubbles(allRisks);
        setView('step-1');
        hideLoader();

        // Auto-proceed: pick the highest-risk bubble automatically
        if (!humanApproval[1] && allRisks.length > 0) {
            const topIdx = allRisks.reduce((best, r, i) =>
                r.assessment.risk_score > allRisks[best].assessment.risk_score ? i : best, 0);
            selectBubble(topIdx);
            await new Promise(r => setTimeout(r, 800));
            await fetchStep2();
        }
    } catch (e) {
        hideLoader();
        alert('Step 1 error: ' + e.message);
    }
}

async function fetchStep2() {
    showLoader('Simulating risk impact...');
    try {
        const payload = {
            perception_output: appState.perception_output,
            manufacturer_profile: appState.manufacturer_profile
        };
        const res = await fetch('/api/step2_risk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Risk assessment failed (${res.status})`);
        }
        const data = await res.json();
        appState.risk_assessment = data;

        document.getElementById('s2-level').innerText = data.risk_level.toUpperCase();

        // Dynamic coloring based on risk level
        const levelWrap = document.getElementById('s2-level').parentElement;
        levelWrap.className = 'info-box';
        document.getElementById('s2-level').className = 'stat';
        if (data.risk_level.toLowerCase() === 'critical') {
            levelWrap.style.borderLeftColor = 'var(--danger)';
            document.getElementById('s2-level').style.color = 'var(--danger)';
        } else if (data.risk_level.toLowerCase() === 'high') {
            levelWrap.style.borderLeftColor = 'var(--warning)';
            document.getElementById('s2-level').style.color = 'var(--warning)';
        } else {
            levelWrap.style.borderLeftColor = 'var(--success)';
            document.getElementById('s2-level').style.color = 'var(--success)';
        }

        document.getElementById('s2-rev').innerText = `$${data.revenue_at_risk.toLocaleString()}`;
        document.getElementById('s2-down').innerText = data.downtime_days;

        // Populate data cards with real API field names
        const probPct = data.disruption_probability != null
            ? `${Math.round(data.disruption_probability * 100)}%` : '—';
        document.getElementById('s2-probability').innerText  = probPct;
        document.getElementById('s2-event-type').innerText   = (data.event_type || '—').replace(/_/g, ' ');
        document.getElementById('s2-parts').innerText        = data.affected_part || '—';
        document.getElementById('s2-delay').innerText        = data.delay_days != null ? `${data.delay_days} days` : '—';
        document.getElementById('s2-sla').innerText          = data.sla_penalty_risk != null
            ? `$${data.sla_penalty_risk.toLocaleString()}` : '—';
        document.getElementById('s2-total').innerText        = data.total_financial_exposure != null
            ? `$${data.total_financial_exposure.toLocaleString()}` : '—';


        setView('step-2');
        hideLoader();

        if (!humanApproval[2]) {
            await new Promise(r => setTimeout(r, 600));
            await fetchStep3();
        }
    } catch (e) {
        hideLoader();
        alert('Step 2 error: ' + e.message);
    }
}

async function fetchStep3() {
    showLoader('Formulating mitigation strategies...');
    try {
        const payload = {
            assessment: appState.assessment,
            risk_assessment: appState.risk_assessment
        };
        const res = await fetch('/api/step3_plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Planning failed (${res.status})`);
        }
        const data = await res.json();

        appState.mohid_plan = data.mohid_plan;
        appState.planning_response = data.planning_response;

        renderStep3(data);
        setView('step-3');
        hideLoader();

        if (!humanApproval[3]) {
            await new Promise(r => setTimeout(r, 600));
            await fetchStep4();
        }
    } catch (e) {
        hideLoader();
        alert('Step 3 error: ' + e.message);
    }
}

// ── Shared Step 3 accordion renderer ─────────────────────────────
function renderStep3(data) {
    const recommendedName = data.planning_response?.recommended_option || data.mohid_plan?.chosen_scenario?.action_type || '';
    const accordion = document.getElementById('s3-accordion');
    accordion.innerHTML = '';

    // Reset approve button
    const appBtn = document.getElementById('s3-approve-btn');
    appBtn.disabled = true;
    appBtn.innerHTML = 'Select a plan above, then Approve <i class="fa-solid fa-arrow-right"></i>';

    // If no tamim options, show a single row from mohid plan
    const options = data.tamim_options && data.tamim_options.length > 0
        ? data.tamim_options
        : [{ name: recommendedName, mitigation_cost: data.mohid_plan?.chosen_scenario?.estimated_cost_usd || 0, net_benefit: 0, description: data.mohid_plan?.reasoning_tree || '' }];

    options.forEach((opt, i) => {
        const isRec = opt.name === recommendedName || i === 0 && !recommendedName;
        const row = document.createElement('div');
        row.className = `plan-row${isRec ? ' is-recommended' : ''}`;
        if (isRec) row.classList.add('open'); // AI pick starts expanded

        const cost = `$${(opt.mitigation_cost || 0).toLocaleString()}`;
        const netBenefit = opt.net_benefit ? `$${opt.net_benefit.toLocaleString()}` : null;

        row.innerHTML = `
            <div class="plan-row-header" onclick="togglePlanRow(this)">
                <div class="plan-row-num">${i + 1}</div>
                <div class="plan-row-title">${esc(opt.name)}</div>
                <div class="plan-row-chips">
                    <span class="plan-chip plan-chip--cost"><i class="fa-solid fa-dollar-sign"></i> ${cost}</span>
                    ${isRec ? '<span class="plan-chip plan-chip--ai"><i class="fa-solid fa-robot"></i> AI Pick</span>' : ''}
                </div>
                <i class="fa-solid fa-chevron-down plan-row-chevron"></i>
            </div>
            <div class="plan-row-body">
                <div class="plan-row-inner">
                    <div class="plan-detail-block">
                        <p class="eyebrow">Mitigation cost</p>
                        <p class="plan-detail-value" style="color:var(--text-primary);font-weight:700;">${cost}</p>
                    </div>
                    ${netBenefit ? `
                    <div class="plan-detail-block">
                        <p class="eyebrow">Net benefit</p>
                        <p class="plan-detail-value" style="color:var(--success);font-weight:700;">${netBenefit}</p>
                    </div>` : '<div></div>'}
                    <div class="plan-detail-block" style="grid-column:1/-1;">
                        <p class="eyebrow">AI reasoning</p>
                        <p class="plan-detail-value">${esc(opt.description || opt.rationale || 'No additional detail available.')}</p>
                    </div>
                    <div class="plan-select-bar">
                        <button class="btn btn-${isRec ? 'primary' : 'secondary'}" style="font-size:0.82rem;padding:8px 18px;"
                            onclick="selectPlan(${i}, '${esc(opt.name)}', '${cost}')">
                            <i class="fa-solid fa-check"></i> Select this plan
                        </button>
                    </div>
                </div>
            </div>
        `;
        accordion.appendChild(row);
    });
}

function togglePlanRow(headerEl) {
    const row = headerEl.closest('.plan-row');
    const wasOpen = row.classList.contains('open');
    // Collapse all
    document.querySelectorAll('.plan-row').forEach(r => r.classList.remove('open'));
    if (!wasOpen) row.classList.add('open');
}

function selectPlan(index, name, cost) {
    // Mark visually
    document.querySelectorAll('.plan-row').forEach((r, i) => {
        r.classList.toggle('is-selected', i === index);
        r.classList.toggle('is-recommended', false);
        // Update chips row
        const chips = r.querySelector('.plan-row-chips');
        // Remove old selected chip
        chips.querySelectorAll('.plan-chip--selected').forEach(c => c.remove());
        if (i === index) {
            const chip = document.createElement('span');
            chip.className = 'plan-chip plan-chip--selected';
            chip.innerHTML = '<i class="fa-solid fa-check"></i> Selected';
            chips.appendChild(chip);
        }
    });
    // Enable approve button
    const btn = document.getElementById('s3-approve-btn');
    btn.disabled = false;
    btn.innerHTML = `Approve: <strong>${name}</strong> &nbsp;<i class="fa-solid fa-arrow-right"></i>`;
}


async function fetchStep4() {
    showLoader('Generating required actions...');
    try {
        // Build fallback planning_response if step 3 was skipped
        const planningResponse = appState.planning_response || {
            recommended_option: 'Expedite alternate freight',
            justification: 'Auto-derived from risk assessment',
            expected_cost_usd: 500000,
            estimated_downtime_reduction_days: 5
        };
        // Build fallback risk_assessment if step 2 was skipped
        const riskAssessment = appState.risk_assessment || {
            event_type: 'shipping_delay',
            affected_part: 'MECH-VALVE-202',
            disruption_probability: 0.85,
            delay_days: 30,
            inventory_days: 30,
            downtime_days: 0,
            revenue_at_risk: 5000000,
            sla_penalty_risk: 1000000,
            total_financial_exposure: 6000000,
            risk_level: 'high'
        };
        const payload = {
            manufacturer_profile: appState.manufacturer_profile,
            risk_assessment: riskAssessment,
            planning_response: planningResponse
        };
        const res = await fetch('/api/step4_actions_generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Action generation failed (${res.status})`);
        }
        const data = await res.json();
        appState.actions = data;

        document.getElementById('s4-email').innerText = data.supplier_email;
        document.getElementById('s4-alert').innerText = data.executive_alert;
        document.getElementById('s4-po').innerText = data.po_adjustment_suggestion || '-';
        document.getElementById('s4-escalation').innerText = data.escalation_trigger || '-';

        const workflowEl = document.getElementById('s4-workflow');
        if (workflowEl) {
            workflowEl.innerText = Array.isArray(data.workflow_integration_log)
                ? data.workflow_integration_log.join('\n')
                : JSON.stringify(data.workflow_integration_log || [], null, 2);
        }

        setView('step-4');
        hideLoader();

        // If approval is off, auto-execute and move to step 5
        if (!humanApproval[4]) {
            await new Promise(r => setTimeout(r, 600));
            await executeActions();
        }
    } catch (e) {
        hideLoader();
        alert('Step 4 error: ' + e.message);
    }
}

async function executeActions() {
    showLoader('Executing actions & saving to ERP / log...');
    try {
        const payload = {
            actions: appState.actions,
            risk_assessment: appState.risk_assessment
        };
        const res = await fetch('/api/step4_actions_execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Action execution failed (${res.status})`);
        }
        // Action executed successfully — move to Step 5
        await fetchStep5();
    } catch (e) {
        hideLoader();
        alert('Execute actions error: ' + e.message);
    }
}

async function fetchStep5() {
    showLoader('Running memory reflection...');
    try {
        const payload = {
            assessment: appState.assessment,
            mohid_plan: appState.mohid_plan
        };
        const res = await fetch('/api/step5_memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `Memory step failed (${res.status})`);

        document.getElementById('s5-summary').innerText = data.summary_text || '-';
        document.getElementById('s5-lesson').innerText = data.key_takeaways || '-';
        document.getElementById('s5-metric').innerText = data.success_metric || '-';

        setView('step-5');
        hideLoader();

        if (!humanApproval[5]) {
            await new Promise(r => setTimeout(r, 600));
            await fetchStep6();
        }
    } catch (e) {
        hideLoader();
        alert('Step 5 error: ' + e.message);
    }
}

async function fetchStep6() {
    showLoader('Compiling transparency report...');
    try {
        const payload = {
            perception_output: appState.perception_output,
            risk_assessment: appState.risk_assessment,
            planning_response: appState.planning_response
        };
        const res = await fetch('/api/step6_transparency', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Transparency step failed (${res.status})`);
        }
        const data = await res.json();

        document.getElementById('s6-trace').innerText = data.reasoning_trace;
        document.getElementById('s6-threshold').innerText = data.human_override_threshold;

        const asmList = document.getElementById('s6-assumptions');
        asmList.innerHTML = '';
        data.assumptions.forEach(a => {
            asmList.innerHTML += `<li>${esc(a)}</li>`;
        });

        const valList = document.getElementById('s6-validation');
        valList.innerHTML = '';
        data.bias_and_constraint_validation.forEach(v => {
            valList.innerHTML += `<li>${esc(v)}</li>`;
        });

        setView('step-6');
    } catch (e) {
        alert('Step 6 error: ' + e.message);
    }
    hideLoader();
}

// ── Customize modal ───────────────────────────────────────────────
function openCustomizeModal(step) {
    customizeStep = step;
    document.getElementById('customize-prompt').value = '';
    document.getElementById('customize-modal').classList.remove('hidden');
}

function closeCustomizeModal() {
    document.getElementById('customize-modal').classList.add('hidden');
    customizeStep = 0;
}

async function submitCustomize() {
    const prompt = document.getElementById('customize-prompt').value.trim();
    if (!prompt) {
        alert('Please enter your instructions.');
        return;
    }
    showLoader('Applying your instructions and regenerating...');
    closeCustomizeModal();
    try {
        if (customizeStep === 1) {
            const res = await fetch('/api/step1_customize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ assessment: appState.assessment, custom_prompt: prompt })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Customize failed');
            appState.assessment = data.assessment;
            document.getElementById('s1-json').innerText = JSON.stringify(data.assessment, null, 2);
        } else if (customizeStep === 2) {
            const payload = { perception_output: appState.perception_output, manufacturer_profile: appState.manufacturer_profile, custom_prompt: prompt };
            const res = await fetch('/api/step2_risk', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Customize failed');
            appState.risk_assessment = data;
            document.getElementById('s2-level').innerText = data.risk_level.toUpperCase();
            const levelWrap = document.getElementById('s2-level').parentElement;
            levelWrap.className = 'info-box';
            if (data.risk_level.toLowerCase() === 'critical') levelWrap.style.borderLeftColor = 'var(--danger)';
            else if (data.risk_level.toLowerCase() === 'high') levelWrap.style.borderLeftColor = 'var(--warning)';
            else levelWrap.style.borderLeftColor = 'var(--success)';
            document.getElementById('s2-rev').innerText = `$${data.revenue_at_risk.toLocaleString()}`;
            document.getElementById('s2-down').innerText = data.downtime_days;
            document.getElementById('s2-json').innerText = JSON.stringify(data, null, 2);
        } else if (customizeStep === 3) {
            const payload = { assessment: appState.assessment, risk_assessment: appState.risk_assessment, custom_prompt: prompt };
            const res = await fetch('/api/step3_plan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Customize failed');
            appState.mohid_plan = data.mohid_plan;
            appState.planning_response = data.planning_response;
            renderStep3(data);

        } else if (customizeStep === 4) {
            const payload = { manufacturer_profile: appState.manufacturer_profile, risk_assessment: appState.risk_assessment, planning_response: appState.planning_response, custom_prompt: prompt };
            const res = await fetch('/api/step4_actions_generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Customize failed');
            appState.actions = data;
            document.getElementById('s4-email').innerText = data.supplier_email;
            document.getElementById('s4-alert').innerText = data.executive_alert;
            document.getElementById('s4-po').innerText = data.po_adjustment_suggestion || '-';
            document.getElementById('s4-escalation').innerText = data.escalation_trigger || '-';
            const workflowEl = document.getElementById('s4-workflow');
            if (workflowEl) workflowEl.innerText = Array.isArray(data.workflow_integration_log) ? data.workflow_integration_log.join('\n') : JSON.stringify(data.workflow_integration_log || [], null, 2);
        } else if (customizeStep === 5) {
            const payload = { assessment: appState.assessment, mohid_plan: appState.mohid_plan, custom_prompt: prompt };
            const res = await fetch('/api/step5_memory', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Customize failed');
            document.getElementById('s5-summary').innerText = data.summary_text || '-';
            document.getElementById('s5-lesson').innerText = data.key_takeaways || '-';
            document.getElementById('s5-metric').innerText = data.success_metric || '-';
        } else if (customizeStep === 6) {
            const payload = { perception_output: appState.perception_output, risk_assessment: appState.risk_assessment, planning_response: appState.planning_response, custom_prompt: prompt };
            const res = await fetch('/api/step6_transparency', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Customize failed');
            document.getElementById('s6-trace').innerText = data.reasoning_trace;
            document.getElementById('s6-threshold').innerText = data.human_override_threshold;
            const asmList = document.getElementById('s6-assumptions');
            asmList.innerHTML = '';
            data.assumptions.forEach(a => { asmList.innerHTML += `<li>${esc(a)}</li>`; });
            const valList = document.getElementById('s6-validation');
            valList.innerHTML = '';
            data.bias_and_constraint_validation.forEach(v => { valList.innerHTML += `<li>${esc(v)}</li>`; });
        }
    } catch (e) {
        alert('Customize error: ' + e.message);
    }
    hideLoader();
}

function startNewCycle() {
    appState.cycle += 1;
    appState.perception_output = null;
    appState.manufacturer_profile = null;
    appState.assessment = null;
    appState.risk_assessment = null;
    appState.planning_response = null;
    appState.mohid_plan = null;
    appState.actions = null;

    startWizard();
}

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadToggles();
    checkAIMode();
});

// ── Settings panel ────────────────────────────────────────────────
let settingsFiles = [];

function openSettings() {
    document.getElementById('settings-modal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeSettings() {
    document.getElementById('settings-modal').classList.add('hidden');
    document.body.style.overflow = '';
}

function onSettingsOverlayClick(e) {
    if (e.target === document.getElementById('settings-modal')) closeSettings();
}

// Drag & drop
function onDragOver(e) {
    e.preventDefault();
    document.getElementById('settings-upload-zone').classList.add('drag-over');
}
function onDragLeave(e) {
    document.getElementById('settings-upload-zone').classList.remove('drag-over');
}
function onFileDrop(e) {
    e.preventDefault();
    document.getElementById('settings-upload-zone').classList.remove('drag-over');
    addFiles(Array.from(e.dataTransfer.files));
}
function onFileSelect(e) {
    addFiles(Array.from(e.target.files));
    e.target.value = '';
}

function addFiles(newFiles) {
    newFiles.forEach(f => {
        if (!settingsFiles.find(x => x.name === f.name && x.size === f.size)) {
            settingsFiles.push(f);
        }
    });
    renderFileList();
}

function removeFile(index) {
    settingsFiles.splice(index, 1);
    renderFileList();
}

function fmtSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes/1024).toFixed(1)} KB`;
    return `${(bytes/1048576).toFixed(1)} MB`;
}

function fileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    if (['csv','xls','xlsx'].includes(ext)) return 'fa-file-csv';
    if (ext === 'pdf') return 'fa-file-pdf';
    if (ext === 'json') return 'fa-file-code';
    return 'fa-file-lines';
}

function renderFileList() {
    const listEl  = document.getElementById('settings-file-list');
    const procRow = document.getElementById('settings-process-row');
    const countEl = document.getElementById('settings-file-count');

    if (settingsFiles.length === 0) {
        listEl.classList.add('hidden');
        procRow.classList.add('hidden');
        return;
    }
    listEl.classList.remove('hidden');
    procRow.classList.remove('hidden');
    countEl.textContent = `${settingsFiles.length} file${settingsFiles.length > 1 ? 's' : ''} ready`;

    listEl.innerHTML = settingsFiles.map((f, i) => `
        <div class="file-chip">
            <i class="fa-solid ${fileIcon(f.name)}"></i>
            <span class="chip-name">${esc(f.name)}</span>
            <span class="chip-size">${fmtSize(f.size)}</span>
            <i class="fa-solid fa-xmark chip-remove" onclick="removeFile(${i})"></i>
        </div>
    `).join('');
}

// ── Simulated AI processing ───────────────────────────────────────
async function processFiles() {
    const btn = document.getElementById('settings-process-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analysing…';

    // Reset UI
    const progressEl = document.getElementById('settings-progress');
    const summaryEl  = document.getElementById('settings-summary');
    const logEl      = document.getElementById('settings-log');
    const fillEl     = document.getElementById('settings-progress-fill');
    const pctEl      = document.getElementById('settings-progress-pct');
    const labelEl    = document.getElementById('settings-progress-label');

    progressEl.classList.remove('hidden');
    summaryEl.classList.add('hidden');
    logEl.innerHTML = '';
    fillEl.style.width = '0%';

    const fileNames = settingsFiles.map(f => f.name);

    // Simulated steps
    const steps = [
        { pct: 8,  label: 'Reading file headers…',        log: `→ Detected ${settingsFiles.length} file(s): ${fileNames.join(', ')}`, cls: 'info' },
        { pct: 20, label: 'Parsing ERP data structure…',   log: '→ Scanning for part IDs, SKUs, stock levels…', cls: '' },
        { pct: 34, label: 'Extracting supplier records…',  log: '→ Found supplier names, locations, lead times', cls: '' },
        { pct: 48, label: 'Mapping shipping routes…',      log: '→ Identified origin ports and freight lanes', cls: '' },
        { pct: 60, label: 'Cross-referencing BOM sheets…', log: '→ Bill of Materials cross-checked against inventory', cls: '' },
        { pct: 74, label: 'Building risk exposure map…',    log: '→ Calculating buffer days vs lead times per part', cls: '' },
        { pct: 88, label: 'Indexing into agent context…',  log: '→ Knowledge encoded into in-session memory', cls: 'ok' },
        { pct: 100,label: 'Extraction complete',           log: '✓ All data loaded — agent context updated', cls: 'ok' },
    ];

    for (const step of steps) {
        labelEl.textContent = step.label;
        fillEl.style.width  = `${step.pct}%`;
        pctEl.textContent   = `${step.pct}%`;
        const line = document.createElement('div');
        line.className = `log-line ${step.cls}`;
        line.textContent = step.log;
        logEl.appendChild(line);
        logEl.scrollTop = logEl.scrollHeight;
        await new Promise(r => setTimeout(r, 420 + Math.random() * 280));
    }

    // Build smart summary based on filenames
    showExtractionSummary(fileNames);

    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Re-analyse';
}

function showExtractionSummary(fileNames) {
    // Generate plausible extracted data based on uploaded file names
    const parts = ['IC-7NM-001', 'MECH-VALVE-202', 'AUTO-HARNESS-X', 'PCB-CTRL-44', 'SENSOR-IMU-7'];
    const suppliers = ['Hsinchu Semi Corp', 'Shenzhen Precision', 'Korea Micro Parts', 'Foxconn Industrial'];
    const routes = ['Shanghai → LA (Ocean)', 'Taipei → Frankfurt (Air)', 'Busan → Rotterdam (Ocean)', 'Shenzhen → Dubai (Air)'];
    const watchlist = ['Port of Shenzhen', 'Red Sea corridor', 'Taiwan Strait', 'Suez Canal'];

    const totalItems = parts.length + suppliers.length + routes.length;

    document.getElementById('settings-summary-badge').textContent = `${totalItems} items extracted`;
    document.getElementById('settings-summary-grid').innerHTML = `
        <div class="summary-card">
            <div class="summary-card-title"><i class="fa-solid fa-box-open"></i> Parts &amp; SKUs</div>
            ${parts.map(p => `<div class="summary-item"><i class="fa-solid fa-check"></i>${p}</div>`).join('')}
        </div>
        <div class="summary-card">
            <div class="summary-card-title"><i class="fa-solid fa-industry"></i> Suppliers</div>
            ${suppliers.map(s => `<div class="summary-item"><i class="fa-solid fa-check"></i>${s}</div>`).join('')}
        </div>
        <div class="summary-card">
            <div class="summary-card-title"><i class="fa-solid fa-ship"></i> Shipping Routes</div>
            ${routes.map(r => `<div class="summary-item"><i class="fa-solid fa-check"></i>${r}</div>`).join('')}
        </div>
        <div class="summary-card">
            <div class="summary-card-title"><i class="fa-solid fa-eye"></i> Risk Watchlist</div>
            ${watchlist.map(w => `<div class="summary-item"><i class="fa-solid fa-check"></i>${w}</div>`).join('')}
        </div>
    `;
    document.getElementById('settings-summary').classList.remove('hidden');
}

