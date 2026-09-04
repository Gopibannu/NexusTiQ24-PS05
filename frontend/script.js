// Frontend Javascript logic for Lease Review Assistant

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const sampleLeaseSelect = document.getElementById('sampleLeaseSelect');
    const leaseTextInput = document.getElementById('leaseTextInput');
    const clearBtn = document.getElementById('clearBtn');
    const fileInput = document.getElementById('fileInput');
    const dropzone = document.getElementById('dropzone');
    const analyzeBtn = document.getElementById('analyzeBtn');

    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const errorState = document.getElementById('errorState');
    const errorTitle = document.getElementById('errorTitle');
    const errorMessage = document.getElementById('errorMessage');
    const retryBtn = document.getElementById('retryBtn');

    const reportContent = document.getElementById('reportContent');
    const statusBanner = document.getElementById('statusBanner');
    const bannerIcon = document.getElementById('bannerIcon');
    const bannerStatusText = document.getElementById('bannerStatusText');
    const bannerSubtext = document.getElementById('bannerSubtext');
    const processingTimer = document.getElementById('processingTimer');

    const plainSummaryList = document.getElementById('plainSummaryList');

    const countForbidden = document.getElementById('countForbidden');
    const countDeviations = document.getElementById('countDeviations');
    const countMissing = document.getElementById('countMissing');
    const countContradictions = document.getElementById('countContradictions');
    const countMatches = document.getElementById('countMatches');

    const sectionForbidden = document.getElementById('sectionForbidden');
    const forbiddenList = document.getElementById('forbiddenList');

    const sectionDeviations = document.getElementById('sectionDeviations');
    const deviationsList = document.getElementById('deviationsList');

    const sectionMissing = document.getElementById('sectionMissing');
    const missingList = document.getElementById('missingList');

    const sectionContradictions = document.getElementById('sectionContradictions');
    const contradictionsList = document.getElementById('contradictionsList');

    const sectionMatches = document.getElementById('sectionMatches');
    const matchesList = document.getElementById('matchesList');

    // 1. Fetch sample leases on startup
    fetchSampleLeases();

    async function fetchSampleLeases() {
        try {
            const res = await fetch('/api/leases');
            if (res.ok) {
                const leases = await res.json();
                sampleLeaseSelect.innerHTML = '<option value="" disabled selected>Select a synthetic lease scenario...</option>';
                leases.forEach(lease => {
                    const opt = document.createElement('option');
                    opt.value = lease.id;
                    opt.textContent = `${lease.name} [Target: ${lease.expected}]`;
                    sampleLeaseSelect.appendChild(opt);
                });
            }
        } catch (err) {
            console.warn("Could not load sample leases:", err);
        }
    }

    // 2. Sample Lease Selection Change
    sampleLeaseSelect.addEventListener('change', async (e) => {
        const leaseId = e.target.value;
        if (!leaseId) return;

        try {
            const res = await fetch(`/api/leases/${leaseId}`);
            if (res.ok) {
                const data = await res.json();
                leaseTextInput.value = data.content;
            }
        } catch (err) {
            console.error("Error loading lease file:", err);
        }
    });

    // 3. Clear button
    clearBtn.addEventListener('click', () => {
        leaseTextInput.value = '';
        sampleLeaseSelect.selectedIndex = 0;
        showState('empty');
    });

    // 4. File Drag & Drop / Upload
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            readFileContent(file);
        }
    });

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            readFileContent(e.dataTransfer.files[0]);
        }
    });

    function readFileContent(file) {
        const reader = new FileReader();
        reader.onload = (evt) => {
            leaseTextInput.value = evt.target.result;
            sampleLeaseSelect.selectedIndex = 0;
        };
        reader.readAsText(file);
    }

    // 5. Analyze Button Click
    analyzeBtn.addEventListener('click', runReview);
    retryBtn.addEventListener('click', runReview);

    async function runReview() {
        const text = leaseTextInput.value.trim();
        if (!text || text.length < 30) {
            showError("Input Too Short", "Please paste or select a valid lease agreement text (at least 30 characters).");
            return;
        }

        showState('loading');

        try {
            const res = await fetch('/api/review', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ lease_text: text })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || errData.details || `HTTP Error ${res.status}`);
            }

            const data = await res.json();
            renderReport(data);
            showState('report');
        } catch (err) {
            console.error("Review request failed:", err);
            showError("Analysis Request Failed", err.message || "Model analysis call failed or timed out. Please try again.");
        }
    }

    function showState(state) {
        emptyState.classList.add('hidden');
        loadingState.classList.add('hidden');
        errorState.classList.add('hidden');
        reportContent.classList.add('hidden');

        if (state === 'empty') emptyState.classList.remove('hidden');
        else if (state === 'loading') loadingState.classList.remove('hidden');
        else if (state === 'error') errorState.classList.remove('hidden');
        else if (state === 'report') reportContent.classList.remove('hidden');
    }

    function showError(title, msg) {
        errorTitle.textContent = title;
        errorMessage.textContent = msg;
        showState('error');
    }

    // 6. Render Report Findings
    function renderReport(data) {
        const status = data.status; // "CLEAN" or "FLAGGED FOR HUMAN REVIEW"
        const isClean = data.is_clean;
        const summary = data.summary || {};
        const findings = data.findings || {};
        const plainSummary = data.plain_language_summary || [];

        // Status Banner
        statusBanner.className = 'status-banner ' + (isClean ? 'status-clean' : 'status-flagged');
        bannerIcon.textContent = isClean ? '✅' : '🚨';
        bannerStatusText.textContent = status;
        bannerSubtext.textContent = isClean 
            ? 'Zero deviations, zero missing required clauses, and zero forbidden terms found. All clauses align with standard positions.' 
            : 'One or more deviations, missing required protections, forbidden terms, or contradictions were detected. Flagged for human review; final decision rests with legal reviewer.';
        
        processingTimer.textContent = `Processed in ${(data.processing_time_ms / 1000).toFixed(2)}s`;

        // Executive Plain Summary
        plainSummaryList.innerHTML = '';
        if (plainSummary.length > 0) {
            plainSummary.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                plainSummaryList.appendChild(li);
            });
        }

        // Metrics Counters
        countForbidden.textContent = summary.forbidden_terms_count || 0;
        countDeviations.textContent = summary.deviations_count || 0;
        countMissing.textContent = summary.missing_protections_count || 0;
        countContradictions.textContent = summary.contradictions_count || 0;
        countMatches.textContent = summary.matches_count || 0;

        // Render Finding Lists

        // 1. Forbidden Terms
        const forbidden = findings.forbidden_terms || [];
        if (forbidden.length > 0) {
            sectionForbidden.classList.remove('hidden');
            forbiddenList.innerHTML = forbidden.map(item => `
                <div class="finding-card border-danger">
                    <div class="quote-block">
                        <span class="quote-badge">VERIFIED SOURCE LEASE QUOTE</span>
                        "${escapeHtml(item.clause_quote)}"
                    </div>
                    <div class="finding-explanation text-danger">
                        <strong>Forbidden Term Violation:</strong> ${escapeHtml(item.explanation)}
                    </div>
                </div>
            `).join('');
        } else {
            sectionForbidden.classList.add('hidden');
        }

        // 2. Deviations
        const deviations = findings.deviations || [];
        if (deviations.length > 0) {
            sectionDeviations.classList.remove('hidden');
            deviationsList.innerHTML = deviations.map(item => `
                <div class="finding-card border-warning">
                    <div class="quote-block">
                        <span class="quote-badge">VERIFIED SOURCE LEASE QUOTE</span>
                        "${escapeHtml(item.clause_quote)}"
                    </div>
                    <div class="finding-explanation">
                        <strong>Deviation:</strong> ${escapeHtml(item.deviation_explanation)}
                    </div>
                    ${item.standard_rule_violated ? `
                        <div class="rule-citation">
                            <strong>Standard Rule Violated:</strong> ${escapeHtml(item.standard_rule_violated)}
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            sectionDeviations.classList.add('hidden');
        }

        // 3. Missing Protections (Silence)
        const missing = findings.missing_protections || [];
        if (missing.length > 0) {
            sectionMissing.classList.remove('hidden');
            missingList.innerHTML = missing.map(item => `
                <div class="finding-card border-info">
                    <div class="quote-block">
                        <span class="quote-badge">SILENCE FINDING — NOT FOUND IN LEASE</span>
                        <em>[Required clause entirely absent from contract document]</em>
                    </div>
                    <div class="finding-explanation text-info">
                        <strong>Missing Required Protection:</strong> ${escapeHtml(item.missing_protection)}
                    </div>
                    <div class="rule-citation">
                        <strong>Why It Matters:</strong> ${escapeHtml(item.why_it_matters)}
                    </div>
                </div>
            `).join('');
        } else {
            sectionMissing.classList.add('hidden');
        }

        // 4. Contradictions
        const contradictions = findings.contradictions || [];
        if (contradictions.length > 0) {
            sectionContradictions.classList.remove('hidden');
            contradictionsList.innerHTML = contradictions.map(item => `
                <div class="finding-card border-purple">
                    <div class="quote-block">
                        <span class="quote-badge">VERIFIED SOURCE LEASE QUOTE 1</span>
                        "${escapeHtml(item.clause_quote_1)}"
                    </div>
                    <div class="quote-block">
                        <span class="quote-badge">VERIFIED SOURCE LEASE QUOTE 2</span>
                        "${escapeHtml(item.clause_quote_2)}"
                    </div>
                    <div class="finding-explanation text-purple">
                        <strong>Internal Contradiction:</strong> ${escapeHtml(item.explanation)}
                    </div>
                </div>
            `).join('');
        } else {
            sectionContradictions.classList.add('hidden');
        }

        // 5. Matches
        const matches = findings.matches || [];
        if (matches.length > 0) {
            sectionMatches.classList.remove('hidden');
            matchesList.innerHTML = matches.map(item => `
                <div class="finding-card border-success">
                    <div class="quote-block">
                        <span class="quote-badge">VERIFIED SOURCE LEASE QUOTE</span>
                        "${escapeHtml(item.clause_quote)}"
                    </div>
                    <div class="finding-explanation text-success">
                        <strong>Policy Alignment:</strong> ${escapeHtml(item.explanation)}
                    </div>
                </div>
            `).join('');
        } else {
            sectionMatches.classList.add('hidden');
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
