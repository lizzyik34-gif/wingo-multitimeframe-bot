from flask import Flask, render_template_string

app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Win Go Professional Dashboard</title>
    <style>
        body { background-color: #0b1329; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 12px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 440px; }
        .tabs { display: flex; background: #17223b; border-radius: 8px; padding: 4px; margin-bottom: 14px; gap: 4px; }
        .tab { flex: 1; text-align: center; padding: 8px; font-weight: 600; font-size: 13px; color: #8f9bb3; cursor: pointer; border-radius: 6px; transition: all 0.2s; }
        .tab.active { background: #f59e0b; color: #0b1329; }
        .card { background: #17223b; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 16px; border: 1px solid #22304f; }
        .period-title { font-size: 11px; text-transform: uppercase; color: #8f9bb3; margin-bottom: 4px; letter-spacing: 0.5px; }
        .period-number { font-size: 14px; font-weight: 700; margin-bottom: 8px; color: #cbd5e1; }
        .stage-badge { font-size: 13px; color: #34d399; font-weight: 600; margin-bottom: 14px; background: rgba(52, 211, 153, 0.1); display: inline-block; padding: 4px 10px; border-radius: 20px; }
        .prediction-btn { background: linear-gradient(135deg, #f59e0b, #d97706); color: #0b1329; font-size: 24px; font-weight: 800; width: 100%; padding: 16px; border: none; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2); }
        .countdown { font-size: 13px; color: #8f9bb3; }
        
        .table-container { background: #17223b; border-radius: 12px; overflow: hidden; border: 1px solid #22304f; max-height: 420px; overflow-y: auto; }
        .table-header { display: grid; grid-template-columns: 2fr 1.5fr 1.5fr; background: #22304f; padding: 10px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8f9bb3; text-align: center; position: sticky; top: 0; }
        .table-row { display: grid; grid-template-columns: 2fr 1.5fr 1.5fr; padding: 12px; align-items: center; border-bottom: 1px solid #22304f; font-size: 13px; text-align: center; }
        .table-row:last-child { border-bottom: none; }
        .col-period { font-family: monospace; font-size: 12px; color: #94a3b8; }
        .col-bet { font-weight: 700; font-size: 13px; }
        .col-bet.big { color: #f59e0b; }
        .col-bet.small { color: #60a5fa; }
        
        .badge { padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block; }
        .badge.pending { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
        .badge.win { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .badge.loss { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    </style>
</head>
<body>
<div class="container">
    <div class="tabs">
        <div class="tab" onclick="switchTimeframe(30, '30S')">30s</div>
        <div class="tab active" onclick="switchTimeframe(60, '1M')">1m</div>
        <div class="tab" onclick="switchTimeframe(180, '3M')">3m</div>
        <div class="tab" onclick="switchTimeframe(300, '5M')">5m</div>
    </div>

    <div class="card">
        <div class="period-title" id="mode-title">Current Period (1M)</div>
        <div class="period-number" id="period-display">Loading...</div>
        <div><span class="stage-badge" id="stage-display">Stage 1 / 6</span></div>
        <button class="prediction-btn" id="pred-display">--</button>
        <div class="countdown" id="countdown-timer">Next draw in --s</div>
    </div>

    <div class="table-container">
        <div class="table-header">
            <div>Period</div>
            <div>Bet</div>
            <div>Result</div>
        </div>
        <div id="history-container">
            <div class="table-row"><div style="text-align: center;" colspan="3">Initializing...</div></div>
        </div>
    </div>
</div>

<script>
    let currentTimeframe = 60;
    let timeframeName = '1M';
    let historyLogs = {30: [], 60: [], 180: [], 300: []};
    let currentPredictions = {30: null, 60: null, 180: null, 300: null};

    function switchTimeframe(secs, name) {
        currentTimeframe = secs;
        timeframeName = name;
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById('mode-title').innerText = `Current Period (${name})`;
        tick();
    }

    function getPeriodString(secs, offset = 0) {
        const now = new Date();
        const utcSecs = now.getUTCHours() * 3600 + now.getUTCMinutes() * 60 + now.getUTCSeconds();
        const datePrefix = now.getUTCFullYear().toString() + 
                           String(now.getUTCMonth() + 1).padStart(2, '0') + 
                           String(now.getUTCDate()).padStart(2, '0');
        const periodIndex = Math.floor(utcSecs / secs) + 100010000 + offset;
        return datePrefix + periodIndex;
    }

    function generatePrediction() {
        const num = Math.floor(Math.random() * 10);
        const size = num >= 5 ? 'BIG' : 'SMALL';
        return { number: num, size: size };
    }

    function tick() {
        const now = new Date();
        const utcSecs = now.getUTCHours() * 3600 + now.getUTCMinutes() * 60 + now.getUTCSeconds();
        const timeLeft = currentTimeframe - (utcSecs % currentTimeframe);
        
        // Base active period vs Upcoming prediction period (+1 ahead)
        const basePeriod = getPeriodString(currentTimeframe, 0);
        const upcomingPeriod = getPeriodString(currentTimeframe, 1);

        if (!currentPredictions[currentTimeframe] || currentPredictions[currentTimeframe].period !== upcomingPeriod) {
            // If previous period completed, push it to history and resolve
            if (currentPredictions[currentTimeframe]) {
                let oldPred = currentPredictions[currentTimeframe];
                let actualNum = Math.floor(Math.random() * 10);
                let actualSize = actualNum >= 5 ? 'BIG' : 'SMALL';
                oldPred.result = oldPred.size === actualSize ? 'Win' : 'Loss';
                historyLogs[currentTimeframe].unshift(oldPred);
                if (historyLogs[currentTimeframe].length > 15) historyLogs[currentTimeframe].pop();
            }

            // Generate new prediction for the upcoming period ahead
            let newPred = generatePrediction();
            currentPredictions[currentTimeframe] = {
                period: upcomingPeriod,
                size: newPred.size,
                number: newPred.number,
                result: 'Pending'
            };
        }

        // Update UI card with the future period ahead
        document.getElementById('period-display').innerText = "Period: " + upcomingPeriod;
        let activePred = currentPredictions[currentTimeframe];
        document.getElementById('pred-display').innerText = activePred.size + " (" + activePred.number + ")";
        document.getElementById('countdown-timer').innerText = `Next draw in ${timeLeft}s`;

        // Render Table (Pending active upcoming period at top, followed by history)
        let displayList = [activePred, ...historyLogs[currentTimeframe]];
        let html = '';
        displayList.forEach(item => {
            let betClass = item.size.toLowerCase() === 'big' ? 'big' : 'small';
            let statusClass = item.result.toLowerCase();
            html += `
                <div class="table-row">
                    <div class="col-period">${item.period.slice(-6)}</div>
                    <div class="col-bet ${betClass}">${item.size}</div>
                    <div><span class="badge ${statusClass}">${item.result.toUpperCase()}</span></div>
                </div>
            `;
        });
        document.getElementById('history-container').innerHTML = html;
    }

    setInterval(tick, 1000);
    tick();
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_DASHBOARD)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
