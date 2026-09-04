// Executive LegalTech Javascript Controller — NexusTiQ24 Track PS05

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
    const bannerStatusText = document.getElementById('bannerStatusText');
    const bannerSubtext = document.getElementById('bannerSubtext');
    const processingTimer = document.getElementById('processingTimer');

    const btnExportJson = document.getElementById('btnExportJson');
    const btnPrintReport = document.getElementById('btnPrintReport');
    const btnCopySummary = document.getElementById('btnCopySummary');
    const btnOpenPolicy = document.getElementById('btnOpenPolicy');
    const btnClosePolicy = document.getElementById('btnClosePolicy');
    const policyModal = document.getElementById('policyModal');

    const riskScoreBadge = document.getElementById('riskScoreBadge');
    const riskBarFill = document.getElementById('riskBarFill');
    const riskScoreSubtext = document.getElementById('riskScoreSubtext');

    const financialScoreVal = document.getElementById('financialScoreVal');
    const financialBarFill = document.getElementById('financialBarFill');

    const legalScoreVal = document.getElementById('legalScoreVal');
    const legalBarFill = document.getElementById('legalBarFill');

    const opScoreVal = document.getElementById('opScoreVal');
    const opBarFill = document.getElementById('opBarFill');

    const comparisonTableBody = document.getElementById('comparisonTableBody');
    const plainSummaryList = document.getElementById('plainSummaryList');

    const countForbidden = document.getElementById('countForbidden');
    const countDeviations = document.getElementById('countDeviations');
    const countMissing = document.getElementById('countMissing');
    const countContradictions = document.getElementById('countContradictions');
    const countMatches = document.getElementById('countMatches');

    const filterPills = document.getElementById('filterPills');
    const findingSearchInput = document.getElementById('findingSearchInput');
    const docViewerBody = document.getElementById('docViewerBody');

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

    const toastContainer = document.getElementById('toastContainer');

    let currentReportData = null;
    let currentRawText = '';
    let currentFilter = 'all';
    let uploadedFileObject = null;

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

        uploadedFileObject = null;
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
        uploadedFileObject = null;
        showState('empty');
    });

    // 4. File Drag & Drop / Upload (TXT, MD, PDF, DOCX)
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleSelectedFile(file);
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
            handleSelectedFile(e.dataTransfer.files[0]);
        }
    });

    function handleSelectedFile(file) {
        uploadedFileObject = file;
        sampleLeaseSelect.selectedIndex = 0;

        const nameLower = file.name.toLowerCase();
        if (nameLower.endsWith('.pdf') || nameLower.endsWith('.docx') || nameLower.endsWith('.doc')) {
            leaseTextInput.value = `[Document File Loaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)]\nClick 'RUN AUTOMATED LEGAL REVIEW' to parse and analyze text from this document.`;
            showToast(`Loaded ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);
        } else {
            readFileContent(file);
        }
    }

    function readFileContent(file) {
        const reader = new FileReader();
        reader.onload = (evt) => {
            leaseTextInput.value = evt.target.result;
            showToast(`Loaded ${file.name}`);
        };
        reader.readAsText(file);
    }

    // 5. Policy Rulebook Modal
    btnOpenPolicy.addEventListener('click', () => policyModal.classList.remove('hidden'));
    btnClosePolicy.addEventListener('click', () => policyModal.classList.add('hidden'));
    policyModal.addEventListener('click', (e) => {
        if (e.target === policyModal) policyModal.classList.add('hidden');
    });

    // 6. Toolbar Actions
    analyzeBtn.addEventListener('click', runReview);
    retryBtn.addEventListener('click', runReview);

    btnExportJson.addEventListener('click', () => {
        if (!currentReportData) return;
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentReportData, null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", `lease_review_report_${Date.now()}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
        showToast("Report exported as JSON file");
    });

    btnPrintReport.addEventListener('click', () => {
        window.print();
    });

    btnCopySummary.addEventListener('click', () => {
        if (!currentReportData || !currentReportData.plain_language_summary) return;
        const summaryText = "LEASE REVIEW SUMMARY:\n" + currentReportData.plain_language_summary.map(s => `- ${s}`).join("\n");
        navigator.clipboard.writeText(summaryText);
        showToast("Executive summary copied to clipboard!");
    });

    // 7. Run Review Request
    async function runReview() {
        const text = leaseTextInput.value.trim();
        
        if (!uploadedFileObject && (!text || text.length < 30)) {
            showError("Input Too Short", "Please paste lease text or upload a valid document file (.txt, .md, .pdf, .docx).");
            return;
        }

        showState('loading');

        try {
            let res;
            if (uploadedFileObject && text.includes('[Document File Loaded:')) {
                // Send FormData for PDF/DOCX file upload
                const formData = new FormData();
                formData.append('file', uploadedFileObject);
                res = await fetch('/api/review', {
                    method: 'POST',
                    body: formData
                });
            } else {
                // Send JSON payload
                res = await fetch('/api/review', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ lease_text: text })
                });
            }

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || errData.details || `HTTP Error ${res.status}`);
            }

            const data = await res.json();
            currentReportData = data;
            
            // Extract raw text for Document Viewer
            if (uploadedFileObject && text.includes('[Document File Loaded:')) {
                currentRawText = `[Parsed from uploaded file: ${uploadedFileObject.name}]\n` + (data.findings?.matches?.[0]?.clause_quote || data.findings?.deviations?.[0]?.clause_quote || text);
            } else {
                currentRawText = text;
            }

            renderReport(data, currentRawText);
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

    // 8. Render Report Findings & Matrices
    function renderReport(data, rawText) {
        const status = data.status;
        const isClean = data.is_clean;
        const summary = data.summary || {};
        const riskBreakdown = data.risk_breakdown || {};
        const compTable = data.comparison_table || [];
        const findings = data.findings || {};
        const plainSummary = data.plain_language_summary || [];

        // Status Banner
        statusBanner.className = 'status-banner ' + (isClean ? 'status-clean' : 'status-flagged');
        bannerStatusText.textContent = status;
        bannerSubtext.textContent = isClean 
            ? 'Zero deviations, zero missing required clauses, and zero forbidden terms found. All clauses align with standard positions.' 
            : 'One or more deviations, missing required protections, forbidden terms, or contradictions were detected. Flagged for human review; final decision rests with legal reviewer.';
        
        processingTimer.textContent = `Processed in ${(data.processing_time_ms / 1000).toFixed(2)}s`;

        // Calculate Compliance Risk Score (100 max)
        let score = 100;
        score -= (summary.forbidden_terms_count || 0) * 35;
        score -= (summary.deviations_count || 0) * 20;
        score -= (summary.missing_protections_count || 0) * 15;
        score -= (summary.contradictions_count || 0) * 25;
        if (score < 0) score = 0;

        riskScoreBadge.textContent = `${score} / 100`;
        riskBarFill.style.width = `${score}%`;
        if (score === 100) {
            riskScoreSubtext.textContent = "Fully compliant lease agreement.";
            riskBarFill.style.background = "#10b981";
        } else if (score >= 70) {
            riskScoreSubtext.textContent = "Moderate risk — minor deviations or missing protections require review.";
            riskBarFill.style.background = "#f59e0b";
        } else {
            riskScoreSubtext.textContent = "High compliance risk — forbidden terms or major deviations present.";
            riskBarFill.style.background = "#f43f5e";
        }

        // Multi-Dimensional Risk Scores
        const finScore = riskBreakdown.financial_score ?? 100;
        financialScoreVal.textContent = `${finScore} / 100`;
        financialBarFill.style.width = `${finScore}%`;

        const legScore = riskBreakdown.legal_score ?? 100;
        legalScoreVal.textContent = `${legScore} / 100`;
        legalBarFill.style.width = `${legScore}%`;

        const opScore = riskBreakdown.operational_score ?? 100;
        opScoreVal.textContent = `${opScore} / 100`;
        opBarFill.style.width = `${opScore}%`;

        // Render Comparison Table
        renderComparisonTable(compTable);

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

        // Filter Pills text
        updatePillsCount(summary);

        // Document Viewer
        renderDocumentViewer(rawText, findings);

        // Finding Lists
        renderFindingLists(findings);
    }

    function renderComparisonTable(compTable) {
        comparisonTableBody.innerHTML = '';
        if (!compTable || compTable.length === 0) {
            comparisonTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No comparison metrics extracted.</td></tr>';
            return;
        }

        compTable.forEach(row => {
            const tr = document.createElement('tr');
            let tagClass = 'tag-compliant';
            if (row.status === 'DEVIATION') tagClass = 'tag-deviation';
            else if (row.status === 'MISSING') tagClass = 'tag-missing';
            else if (row.status === 'FORBIDDEN') tagClass = 'tag-forbidden';
            else if (row.status === 'CONTRADICTION') tagClass = 'tag-contradiction';

            tr.innerHTML = `
                <td><strong>${escapeHtml(row.parameter)}</strong></td>
                <td>${escapeHtml(row.submitted_term)}</td>
                <td>${escapeHtml(row.standard_policy)}</td>
                <td><span class="status-tag ${tagClass}">${escapeHtml(row.status)}</span></td>
            `;
            comparisonTableBody.appendChild(tr);
        });
    }

    function updatePillsCount(summary) {
        const total = (summary.forbidden_terms_count || 0) + (summary.deviations_count || 0) + (summary.missing_protections_count || 0) + (summary.contradictions_count || 0) + (summary.matches_count || 0);
        filterPills.querySelector('[data-filter="all"]').textContent = `ALL (${total})`;
        filterPills.querySelector('[data-filter="forbidden"]').textContent = `FORBIDDEN (${summary.forbidden_terms_count || 0})`;
        filterPills.querySelector('[data-filter="deviations"]').textContent = `DEVIATIONS (${summary.deviations_count || 0})`;
        filterPills.querySelector('[data-filter="missing"]').textContent = `MISSING (${summary.missing_protections_count || 0})`;
        filterPills.querySelector('[data-filter="contradictions"]').textContent = `CONTRADICTIONS (${summary.contradictions_count || 0})`;
        filterPills.querySelector('[data-filter="matches"]').textContent = `MATCHES (${summary.matches_count || 0})`;
    }

    // 9. Document Viewer Rendering with Quote Highlight Spans
    function renderDocumentViewer(rawText, findings) {
        docViewerBody.innerHTML = '';

        const quotesToHighlight = [];
        (findings.forbidden_terms || []).forEach(f => f.clause_quote && quotesToHighlight.push({ quote: f.clause_quote, type: 'forbidden' }));
        (findings.deviations || []).forEach(d => d.clause_quote && quotesToHighlight.push({ quote: d.clause_quote, type: 'deviation' }));
        (findings.contradictions || []).forEach(c => {
            if (c.clause_quote_1) quotesToHighlight.push({ quote: c.clause_quote_1, type: 'contradiction' });
            if (c.clause_quote_2) quotesToHighlight.push({ quote: c.clause_quote_2, type: 'contradiction' });
        });
        (findings.matches || []).forEach(m => m.clause_quote && quotesToHighlight.push({ quote: m.clause_quote, type: 'match' }));

        let formattedHtml = escapeHtml(rawText);

        quotesToHighlight.forEach((qObj, idx) => {
            const q = qObj.quote;
            if (!q) return;
            const escapedQ = escapeHtml(q);
            const quoteId = `quote-anchor-${idx}`;
            const spanHtml = `<span id="${quoteId}" class="highlight-quote" data-quote-text="${escapeHtml(q)}">${escapedQ}</span>`;
            formattedHtml = formattedHtml.replace(escapedQ, spanHtml);
        });

        docViewerBody.innerHTML = formattedHtml;
    }

    // 10. Finding Lists Rendering & Clause Renegotiation Counter-Offer Cards
    function renderFindingLists(findings) {
        // Forbidden Terms
        const forbidden = findings.forbidden_terms || [];
        if (forbidden.length > 0) {
            sectionForbidden.classList.remove('hidden');
            forbiddenList.innerHTML = forbidden.map(item => `
                <div class="finding-card border-danger" data-type="forbidden" data-quote="${escapeHtml(item.clause_quote)}">
                    <div class="quote-block">
                        <span class="quote-badge">VERIFIED SOURCE LEASE QUOTE</span>
                        "${escapeHtml(item.clause_quote)}"
                    </div>
                    <div class="finding-explanation text-danger">
                        <strong>Forbidden Term Violation:</strong> ${escapeHtml(item.explanation)}
                    </div>
                    ${item.suggested_renegotiation_clause ? `
                        <div class="renegotiation-box">
                            <span class="renegotiation-title">RECOMMENDED COUNTER-OFFER REPLACEMENT CLAUSE</span>
                            <div class="renegotiation-text">${escapeHtml(item.suggested_renegotiation_clause)}</div>
                            <button class="btn-copy-counter" data-counter="${escapeHtml(item.suggested_renegotiation_clause)}">COPY COUNTER-OFFER CLAUSE</button>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            sectionForbidden.classList.add('hidden');
        }

        // Deviations
        const deviations = findings.deviations || [];
        if (deviations.length > 0) {
            sectionDeviations.classList.remove('hidden');
            deviationsList.innerHTML = deviations.map(item => `
                <div class="finding-card border-warning" data-type="deviations" data-quote="${escapeHtml(item.clause_quote)}">
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
                    ${item.suggested_renegotiation_clause ? `
                        <div class="renegotiation-box">
                            <span class="renegotiation-title">RECOMMENDED COUNTER-OFFER REPLACEMENT CLAUSE</span>
                            <div class="renegotiation-text">${escapeHtml(item.suggested_renegotiation_clause)}</div>
                            <button class="btn-copy-counter" data-counter="${escapeHtml(item.suggested_renegotiation_clause)}">COPY COUNTER-OFFER CLAUSE</button>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            sectionDeviations.classList.add('hidden');
        }

        // Missing Protections (Silence)
        const missing = findings.missing_protections || [];
        if (missing.length > 0) {
            sectionMissing.classList.remove('hidden');
            missingList.innerHTML = missing.map(item => `
                <div class="finding-card border-info" data-type="missing">
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
                    ${item.suggested_renegotiation_clause ? `
                        <div class="renegotiation-box">
                            <span class="renegotiation-title">RECOMMENDED MANDATORY CLAUSE TO ADD</span>
                            <div class="renegotiation-text">${escapeHtml(item.suggested_renegotiation_clause)}</div>
                            <button class="btn-copy-counter" data-counter="${escapeHtml(item.suggested_renegotiation_clause)}">COPY CLAUSE TO ADD</button>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            sectionMissing.classList.add('hidden');
        }

        // Contradictions
        const contradictions = findings.contradictions || [];
        if (contradictions.length > 0) {
            sectionContradictions.classList.remove('hidden');
            contradictionsList.innerHTML = contradictions.map(item => `
                <div class="finding-card border-purple" data-type="contradictions" data-quote="${escapeHtml(item.clause_quote_1)}">
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

        // Matches
        const matches = findings.matches || [];
        if (matches.length > 0) {
            sectionMatches.classList.remove('hidden');
            matchesList.innerHTML = matches.map(item => `
                <div class="finding-card border-success" data-type="matches" data-quote="${escapeHtml(item.clause_quote)}">
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

        // Wire click handler on finding cards
        document.querySelectorAll('.finding-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.classList.contains('btn-copy-counter')) return;

                document.querySelectorAll('.finding-card').forEach(c => c.classList.remove('active-finding'));
                card.classList.add('active-finding');

                const quoteText = card.getAttribute('data-quote');
                if (quoteText) {
                    highlightQuoteInViewer(quoteText);
                }
            });
        });

        // Wire copy counter clause buttons
        document.querySelectorAll('.btn-copy-counter').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const textToCopy = btn.getAttribute('data-counter');
                if (textToCopy) {
                    navigator.clipboard.writeText(textToCopy);
                    showToast("Counter-offer replacement clause copied to clipboard!");
                }
            });
        });
    }

    function highlightQuoteInViewer(quoteText) {
        document.querySelectorAll('.highlight-quote').forEach(span => span.classList.remove('active-quote'));
        
        const spans = Array.from(document.querySelectorAll('.highlight-quote'));
        const matchedSpan = spans.find(s => s.getAttribute('data-quote-text') === quoteText || s.textContent.includes(quoteText));
        
        if (matchedSpan) {
            matchedSpan.classList.add('active-quote');
            matchedSpan.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    // 11. Filter Pills & Search Box
    filterPills.addEventListener('click', (e) => {
        if (!e.target.classList.contains('pill')) return;
        filterPills.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        e.target.classList.add('active');
        currentFilter = e.target.getAttribute('data-filter');
        applyFiltersAndSearch();
    });

    findingSearchInput.addEventListener('input', applyFiltersAndSearch);

    function applyFiltersAndSearch() {
        const query = findingSearchInput.value.toLowerCase().trim();
        const sections = [
            { id: 'sectionForbidden', type: 'forbidden' },
            { id: 'sectionDeviations', type: 'deviations' },
            { id: 'sectionMissing', type: 'missing' },
            { id: 'sectionContradictions', type: 'contradictions' },
            { id: 'sectionMatches', type: 'matches' }
        ];

        sections.forEach(sec => {
            const el = document.getElementById(sec.id);
            if (!el) return;

            const cards = el.querySelectorAll('.finding-card');
            let visibleCards = 0;

            cards.forEach(card => {
                const cardType = card.getAttribute('data-type');
                const cardText = card.textContent.toLowerCase();
                
                const matchesFilter = (currentFilter === 'all' || currentFilter === cardType);
                const matchesQuery = (!query || cardText.includes(query));

                if (matchesFilter && matchesQuery) {
                    card.classList.remove('hidden');
                    visibleCards++;
                } else {
                    card.classList.add('hidden');
                }
            });

            if (visibleCards > 0 && (currentFilter === 'all' || currentFilter === sec.type)) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        });
    }

    // Toast Utility
    function showToast(msg) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = msg;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.remove();
        }, 3000);
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
