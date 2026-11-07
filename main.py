from datetime import datetime, timezone
import json
import random
import urllib.request
from flask import Flask, jsonify, render_template_string, request

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
        .prediction-btn { background: linear-gradient(135deg, #f59e0b, #d97706); color: #0b1329; font-size: 24px; font-weight: 800; width: 100%; padding: 16px; border: none; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2); }
        
        .action-btn { background: #22304f; color: #f8fafc; font-size: 13px; font-weight: 700; width: 100%; padding: 12px; border: 1px solid #334155; border-radius: 8px; cursor: pointer; transition: all 0.2s; margin-bottom: 8px; }
        .action-btn:active { background: #334155; transform: scale(0.98); }

        .countdown { font-size: 13px; color: #8f9bb3; }
        
        .table-container { background: #17223b; border-radius: 12px; overflow: hidden; border: 1px solid #22304f; max-height: 420px; overflow-y: auto; }
        .table-header { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; background: #22304f; padding: 10px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8f9bb3; text-align: center; position: sticky; top: 0; }
        .table-row { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; padding: 12px; align-items: center; border-bottom: 1px solid #22304f; font-size: 13px; text-align: center; }
        .table-row:last-child { border-bottom: none; }
        .col-period { font-family: monospace; font-size: 11px; color: #94a3b8; text-align: left; }
        .col-num { font-weight: 700; font-size: 15px; }
        .col-num.red { color: #ef4444; }
        .col-num.green { color: #10b981; }
        .col-size { font-weight: 600; }
        
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block; }
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
        <button class="action-btn" onclick="triggerNextPrediction()">⚡ Generate Next Prediction Ahead</button>
        <div class="countdown" id="countdown-timer">Next draw in --s</div>
    </div>

    <div class="table-container">
        <div class="table-header">
            <div style="text-align: left;">Period</div>
            <div>Number</div>
            <div>Big/Small</div>
            <div>Status</div>
        </div>
        <div id="history-container">
            <div class="table-row"><div style="text-align: center;" colspan="4">Syncing live results...</div></div>
        </div>
    </div>
</div>

<script>
    let currentTimeframe = 60;
    let timeframeName = '1M';
    let timeLeft = 60;
    let manualOffset = 0;

    function switchTimeframe(secs, name) {
        currentTimeframe = secs;
        timeframeName = name;
        timeLeft = secs;
        manualOffset = 0;
