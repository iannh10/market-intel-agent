/* ═══════════════════════════════════════
   MarketPulse — Frontend Logic
   SSE streaming + dark-mode + report render
═══════════════════════════════════════ */

(function () {
    'use strict';

    // ── DOM refs ─────────────────────────────────────
    const themeToggle = document.getElementById('themeToggle');
    const runForm = document.getElementById('runForm');
    const topicInput = document.getElementById('topicInput');
    const voiceToggle = document.getElementById('voiceToggle');
    const runBtn = document.getElementById('runBtn');
    const results = document.getElementById('results');
    const consoleEl = document.getElementById('console');
    const consoleStatus = document.getElementById('consoleStatus');
    const cardsSection = document.getElementById('cardsSection');
    const runAgainBtn = document.getElementById('runAgainBtn');
    const timestampRow = document.getElementById('timestampRow');

    // Card body refs
    const newsBody = document.getElementById('newsBody');
    const trendsBody = document.getElementById('trendsBody');
    const strategyBody = document.getElementById('strategyBody');
    const riskBody = document.getElementById('riskBody');
    const voiceBody = document.getElementById('voiceBody');
    const cardVoice = document.getElementById('cardVoice');

    // Pipeline steps
    const pipelineSteps = {
        data: document.querySelector('[data-agent="data"]'),
        trend: document.querySelector('[data-agent="trend"]'),
        strategy: document.querySelector('[data-agent="strategy"]'),
        risk: document.querySelector('[data-agent="risk"]'),
        report: document.querySelector('[data-agent="report"]'),
    };

    // ── Dark Mode ────────────────────────────────────
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    const saved = localStorage.getItem('theme');

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }

    // Apply saved or system preference
    applyTheme(saved || (prefersDark.matches ? 'dark' : 'light'));

    themeToggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        applyTheme(current === 'dark' ? 'light' : 'dark');
    });

    // ── Helpers ──────────────────────────────────────
    function addConsoleLine(text, cls) {
        const line = document.createElement('div');
        line.className = 'console-line' + (cls ? ' ' + cls : '');
        line.textContent = text;
        consoleEl.appendChild(line);
        consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    function setRunning(isRunning) {
        runBtn.disabled = isRunning;
        if (isRunning) {
            runBtn.classList.add('loading');
        } else {
            runBtn.classList.remove('loading');
        }
    }

    function resetPipeline() {
        Object.values(pipelineSteps).forEach(el => {
            el.classList.remove('active', 'done');
        });
    }

    function activateStep(agent) {
        const order = ['data', 'trend', 'strategy', 'risk', 'report'];
        const idx = order.indexOf(agent);
        order.forEach((a, i) => {
            const el = pipelineSteps[a];
            if (i < idx) { el.classList.remove('active'); el.classList.add('done'); }
            if (i === idx) { el.classList.add('active'); el.classList.remove('done'); }
            if (i > idx) { el.classList.remove('active', 'done'); }
        });
    }

    // Guess pipeline step from log line
    function detectStep(msg) {
        if (msg.includes('Data Agent')) activateStep('data');
        else if (msg.includes('Trend Agent')) activateStep('trend');
        else if (msg.includes('Strategy Agent')) activateStep('strategy');
        else if (msg.includes('Risk Agent')) activateStep('risk');
        else if (msg.includes('Voice Agent')) activateStep('report');
        else if (msg.includes('Pipeline complete')) {
            Object.values(pipelineSteps).forEach(el => {
                el.classList.remove('active');
                el.classList.add('done');
            });
        }
    }

    // ── Report Rendering ─────────────────────────────
    function el(tag, cls, text) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text) e.textContent = text;
        return e;
    }

    function renderNews(articles) {
        newsBody.innerHTML = '';
        articles.forEach(a => {
            const item = el('div', 'news-item');
            item.appendChild(el('div', 'news-headline', a.headline));
            const src = el('div', 'news-source');
            const link = document.createElement('a');
            link.href = a.source;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = new URL(a.source).hostname.replace('www.', '');
            src.appendChild(link);
            item.appendChild(src);
            item.appendChild(el('div', 'news-summary', a.summary));
            newsBody.appendChild(item);
        });
    }

    function renderTagList(container, items, accentVar) {
        const ul = el('ul', 'tag-list');
        items.forEach((item, i) => {
            const li = el('li', 'tag-item');
            const bullet = el('span', 'tag-bullet', String(i + 1));
            li.appendChild(bullet);
            li.appendChild(el('span', null, item));
            ul.appendChild(li);
        });
        container.appendChild(ul);
    }

    function renderSubSection(container, heading, items) {
        container.appendChild(el('p', 'sub-heading', heading));
        renderTagList(container, items);
    }

    function renderTrends(data) {
        trendsBody.innerHTML = '';
        renderTagList(trendsBody, data.trends || []);
        if ((data.sentiment_shifts || []).length) {
            renderSubSection(trendsBody, 'Sentiment Shifts', data.sentiment_shifts);
        }
    }

    function renderStrategy(data) {
        strategyBody.innerHTML = '';
        renderTagList(strategyBody, data.opportunities || []);
        if ((data.recommendations || []).length) {
            renderSubSection(strategyBody, 'Recommendations', data.recommendations);
        }
    }

    function renderRisks(data) {
        riskBody.innerHTML = '';
        renderTagList(riskBody, data.risks || []);
        if ((data.weak_signals || []).length) {
            renderSubSection(riskBody, 'Weak Signals', data.weak_signals);
        }
        if ((data.uncertainties || []).length) {
            renderSubSection(riskBody, 'Uncertainties', data.uncertainties);
        }
    }

    function renderReport(report) {
        renderNews(report.articles);
        renderTrends(report.trends);
        renderStrategy(report.strategy);
        renderRisks(report.risks);

        if (report.voice_script) {
            voiceBody.innerHTML = '';
            voiceBody.appendChild(el('div', 'voice-script', report.voice_script));
            cardVoice.style.display = '';
        } else {
            cardVoice.style.display = 'none';
        }

        const now = new Date().toLocaleString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
        timestampRow.textContent = `Topic: "${report.topic}" · Generated on ${now}`;

        cardsSection.style.display = '';
        cardsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ── Form Submit ──────────────────────────────────
    runForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const topic = topicInput.value.trim();
        if (!topic) return;

        const includeVoice = voiceToggle.checked;

        // UI reset
        setRunning(true);
        resetPipeline();
        results.style.display = '';
        cardsSection.style.display = 'none';
        consoleEl.innerHTML = '';
        consoleStatus.textContent = 'Running…';
        addConsoleLine('⏳  Connecting to pipeline…', 'log-info');

        // Scroll to results
        setTimeout(() => results.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);

        try {
            // 1. POST /run
            const res = await fetch('/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, include_voice: includeVoice }),
            });

            if (!res.ok) {
                const err = await res.json();
                addConsoleLine('❌  Server error: ' + (err.error || res.statusText), 'log-error');
                consoleStatus.textContent = 'Error';
                setRunning(false);
                return;
            }

            const { run_id } = await res.json();
            addConsoleLine('✅  Pipeline started. Streaming agent output…', 'log-success');

            // 2. Open SSE stream
            const es = new EventSource(`/stream/${run_id}`);

            es.addEventListener('log', (ev) => {
                const msg = ev.data.replace(/\\n/g, '\n');
                addConsoleLine(msg);
                detectStep(msg);
            });

            es.addEventListener('done', (ev) => {
                es.close();
                setRunning(false);
                consoleStatus.textContent = 'Complete';
                addConsoleLine('', null);
                addConsoleLine('✦ Report ready.', 'log-success');

                try {
                    const report = JSON.parse(ev.data);
                    renderReport(report);
                } catch (err) {
                    addConsoleLine('⚠️  Could not parse report JSON.', 'log-error');
                }
            });

            es.addEventListener('error', (ev) => {
                if (ev.data) {
                    addConsoleLine('❌  ' + ev.data.replace(/\\n/g, '\n'), 'log-error');
                    consoleStatus.textContent = 'Error';
                }
                es.close();
                setRunning(false);
            });

            es.onerror = () => {
                if (es.readyState === EventSource.CLOSED) return;
                addConsoleLine('⚠️  Connection lost.', 'log-error');
                es.close();
                setRunning(false);
                consoleStatus.textContent = 'Disconnected';
            };

        } catch (err) {
            addConsoleLine('❌  Fetch error: ' + err.message, 'log-error');
            consoleStatus.textContent = 'Error';
            setRunning(false);
        }
    });

    // ── Run Again ─────────────────────────────────────
    runAgainBtn.addEventListener('click', () => {
        topicInput.value = '';
        results.style.display = 'none';
        cardsSection.style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => topicInput.focus(), 600);
    });

})();
