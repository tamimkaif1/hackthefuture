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

async function startWizard() {
    await fetchStep1();
}

async function proceedToStep(step) {
    if (step === 2) await fetchStep2();
    if (step === 3) await fetchStep3();
    if (step === 4) await fetchStep4();
    if (step === 6) await fetchStep6(); // Step 5 has no action button to proceed directly, wait, step 5 proceeds to 6
}

async function fetchStep1() {
    showLoader('Ingesting signals and assessing initial risk...');
    try {
        const res = await fetch('/api/step1_perception');
        if (!res.ok) throw new Error('Failed to fetch perception');
        const data = await res.json();
        
        appState.assessment = data.assessment;
        appState.perception_output = data.perception_output;
        appState.manufacturer_profile = data.manufacturer_profile;

        document.getElementById('s1-news').innerText = data.news_headline;
        document.getElementById('s1-erp').innerText = `${data.erp_context_size} parts tracked`;
        document.getElementById('s1-health').innerText = data.supplier_health_summary || "Healthy";
        document.getElementById('s1-json').innerText = JSON.stringify(data.assessment, null, 2);
        
        setView('step-1');
    } catch(e) {
        alert(e);
    }
    hideLoader();
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
        document.getElementById('s2-json').innerText = JSON.stringify(data, null, 2);
        
        setView('step-2');
    } catch(e) {
        alert(e);
    }
    hideLoader();
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
        const data = await res.json();
        
        appState.mohid_plan = data.mohid_plan;
        appState.planning_response = data.planning_response;

        document.getElementById('s3-chosen-plan').innerText = data.mohid_plan.chosen_scenario.action_type;
        document.getElementById('s3-cost').innerText = `$${data.mohid_plan.chosen_scenario.estimated_cost_usd.toLocaleString()}`;
        document.getElementById('s3-reasoning').innerText = data.mohid_plan.reasoning_tree;
        
        // Render options
        const grid = document.getElementById('s3-options');
        grid.innerHTML = '';
        data.tamim_options.forEach(opt => {
            const isRec = opt.name === data.planning_response.recommended_option;
            grid.innerHTML += `
                <div class="info-box ${isRec ? 'border-warning' : ''}" style="margin-bottom:15px; background: rgba(0,0,0,0.3);">
                    <h4 style="color:var(--text-primary)">
                        ${opt.name} 
                        ${isRec ? '<span class="badge" style="background:var(--accent);font-size:0.6rem;float:right;">Chosen</span>' : ''}
                    </h4>
                    <p class="text-secondary" style="font-size:0.85rem;margin-top:5px;">Cost: <span style="color:#fff">$${opt.mitigation_cost.toLocaleString()}</span></p>
                    <p class="text-secondary" style="font-size:0.85rem;">Net Benefit: <span style="color:var(--success)">$${opt.net_benefit.toLocaleString()}</span></p>
                </div>
            `;
        });

        setView('step-3');
    } catch(e) {
        alert(e);
    }
    hideLoader();
}

async function fetchStep4() {
    showLoader('Generating required actions...');
    try {
        const payload = {
            manufacturer_profile: appState.manufacturer_profile,
            risk_assessment: appState.risk_assessment,
            planning_response: appState.planning_response
        };
        const res = await fetch('/api/step4_actions_generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        appState.actions = data;

        document.getElementById('s4-email').innerText = data.supplier_email;
        document.getElementById('s4-alert').innerText = data.executive_alert;
        
        if (data.escalation_trigger) {
            document.getElementById('s4-escalation-card').style.display = 'block';
            document.getElementById('s4-escalation').innerText = data.escalation_trigger;
        } else {
            document.getElementById('s4-escalation-card').style.display = 'none';
        }

        document.getElementById('s4-log').innerText = JSON.stringify(data.workflow_integration_log, null, 2);

        setView('step-4');
    } catch(e) {
        alert(e);
    }
    hideLoader();
}

async function executeActions() {
    showLoader('Executing actions & saving to ERP / log...');
    try {
        const payload = {
            actions: appState.actions,
            risk_assessment: appState.risk_assessment
        };
        await fetch('/api/step4_actions_execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        // Action executed successfully! 
        // Move to Step 5 Memory Reflection automatically
        await fetchStep5();
    } catch(e) {
        alert(e);
        hideLoader();
    }
}

async function fetchStep5() {
    showLoader('Running memory reflection...');
    try {
        const payload = {
            assessment: appState.assessment,
            mohid_plan: appState.mohid_plan
        };
        await fetch('/api/step5_memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        setView('step-5');
    } catch(e) {
        alert(e);
    }
    hideLoader();
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
        const data = await res.json();

        document.getElementById('s6-trace').innerText = data.reasoning_trace;
        document.getElementById('s6-threshold').innerText = data.human_override_threshold;
        
        const asmList = document.getElementById('s6-assumptions');
        asmList.innerHTML = '';
        data.assumptions.forEach(a => {
            asmList.innerHTML += `<li>${a}</li>`;
        });

        const valList = document.getElementById('s6-validation');
        valList.innerHTML = '';
        data.bias_and_constraint_validation.forEach(v => {
            valList.innerHTML += `<li>${v}</li>`;
        });

        setView('step-6');
    } catch(e) {
        alert(e);
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
