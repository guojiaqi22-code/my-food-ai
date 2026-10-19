import os
import io
import json
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
import google.generativeai as genai
from PIL import Image

app = FastAPI()

# 从 Render 环境变量读取 API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""), transport="rest")

@app.get("/", response_class=HTMLResponse)
async def index():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 代谢健康与控糖审查</title>
    <!-- 引入 html2canvas 实现长图导出 -->
    <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 16px; max-width: 480px; margin: auto; background: #f8fafc; color: #1e293b; }
        .card { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.06); margin-bottom: 16px; }
        h2 { font-size: 1.15rem; margin-top: 0; margin-bottom: 12px; color: #0f172a; }
        .form-group { margin-bottom: 12px; }
        label { display: block; font-size: 0.82rem; color: #64748b; margin-bottom: 4px; font-weight: 500; }
        input, select { width: 100%; padding: 11px; border: 1px solid #cbd5e1; border-radius: 10px; box-sizing: border-box; font-size: 0.95rem; }
        
        /* 5人身份切换栏 */
        .profile-tabs { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 14px; }
        .tab-btn { padding: 8px 3px; border: 1.5px solid #e2e8f0; border-radius: 10px; background: #f8fafc; color: #475569; font-size: 0.74rem; font-weight: 600; cursor: pointer; text-align: center; transition: 0.15s; line-height: 1.3; }
        .tab-btn.active { background: #eff6ff; border-color: #0284c7; color: #0284c7; box-shadow: 0 2px 4px rgba(2,132,199,0.12); }
        .role-badge { display: inline-block; background: #e0f2fe; color: #0369a1; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; margin-bottom: 10px; }

        .btn { width: 100%; padding: 14px; background: #0284c7; color: white; border: none; border-radius: 12px; font-size: 1rem; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn:active { background: #0369a1; }
        .divider { text-align: center; margin: 15px 0; position: relative; color: #94a3b8; font-size: 0.85rem; }
        .divider::before, .divider::after { content: ""; position: absolute; top: 50%; width: 42%; height: 1px; background: #e2e8f0; }
        .divider::before { left: 0; }
        .divider::after { right: 0; }
        #preview { width: 100%; max-height: 200px; object-fit: contain; margin: 10px 0; display: none; border-radius: 8px; border: 1px dashed #cbd5e1; }
        #loading { display: none; text-align: center; color: #0284c7; font-weight: bold; margin: 15px 0; }
        #result { display: none; }
        .score-badge { font-size: 2.2rem; font-weight: 800; text-align: center; margin: 8px 0; }
        .danger { color: #dc2626; }
        .warning { color: #d97706; }
        .safe { color: #16a34a; }
        
        .intake-box { background: #eff6ff; border: 1.5px solid #bfdbfe; border-radius: 12px; padding: 12px 14px; margin: 12px 0; }
        .intake-box h4 { margin: 0 0 4px 0; color: #1d4ed8; font-size: 0.95rem; }
        .intake-box p { margin: 0; font-size: 0.9rem; color: #1e3a8a; line-height: 1.4; }

        /* 功能 1：视觉冲击折算条 */
        .visual-box { background: #fff1f2; border: 1.5px solid #fecdd3; border-radius: 12px; padding: 12px 14px; margin: 12px 0; }
        .visual-box h4 { margin: 0 0 4px 0; color: #e11d48; font-size: 0.95rem; }
        .visual-box p { margin: 0; font-size: 0.92rem; color: #9f1239; font-weight: bold; line-height: 1.4; }

        /* 功能 2：代谢债务与运动消耗代价 */
        .debt-box { background: #fff7ed; border: 1.5px solid #ffedd5; border-radius: 12px; padding: 12px 14px; margin: 12px 0; }
        .debt-box h4 { margin: 0 0 4px 0; color: #c2410c; font-size: 0.95rem; }
        .debt-box p { margin: 0; font-size: 0.9rem; color: #9a3412; line-height: 1.4; }

        /* 功能 3：荧光排雷标签 */
        .tag-container { display: flex; flex-direction: column; gap: 8px; margin-top: 6px; }
        .ingredient-tag { display: block; padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; line-height: 1.4; }
        .tag-red { background: #fee2e2; border-left: 4px solid #ef4444; color: #991b1b; }
        .tag-yellow { background: #fef3c7; border-left: 4px solid #f59e0b; color: #92400e; }
        .tag-green { background: #dcfce7; border-left: 4px solid #22c55e; color: #166534; }

        /* 功能 5：同店/同场景安全点餐公式 */
        .menu-box { background: #faf5ff; border: 1.5px solid #d8b4fe; border-radius: 12px; padding: 14px; margin-top: 14px; }
        .menu-box h3 { margin: 0 0 8px 0; color: #6b21a8; font-size: 0.98rem; }
        .menu-item { font-size: 0.88rem; color: #4c1d95; line-height: 1.5; margin-bottom: 6px; }

        .substitute-box { background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 12px; padding: 14px; margin-top: 14px; }
        .substitute-box h3 { margin: 0 0 8px 0; color: #15803d; font-size: 0.98rem; }
        .sub-item { font-size: 0.88rem; color: #14532d; line-height: 1.5; margin-bottom: 6px; }

        .action-row { display: flex; gap: 10px; margin-top: 16px; }
        .btn-action { flex: 1; padding: 12px 8px; border-radius: 10px; border: 1px solid #cbd5e1; background: #f8fafc; color: #334155; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: 0.15s; }
        .btn-action:active { background: #e2e8f0; }
    </style>
</head>
<body>
    <div class="card">
        <h2>👨‍👩‍👦 1. 选择进食者档案 <span style="font-size: 0.75rem; color: #16a34a; font-weight: normal;">(5人独立记忆)</span></h2>
        
        <!-- 5个身份切换标签 -->
        <div class="profile-tabs" id="profileTabs">
            <button type="button" class="tab-btn active" onclick="switchSlot(0)" id="tab_0">👦<br><span id="tab_name_0">壮年男性</span></button>
            <button type="button" class="tab-btn" onclick="switchSlot(1)" id="tab_1">👩<br><span id="tab_name_1">壮年女性</span></button>
            <button type="button" class="tab-btn" onclick="switchSlot(2)" id="tab_2">🧑<br><span id="tab_name_2">青少年</span></button>
            <button type="button" class="tab-btn" onclick="switchSlot(3)" id="tab_3">👴<br><span id="tab_name_3">老年男性</span></button>
            <button type="button" class="tab-btn" onclick="switchSlot(4)" id="tab_4">👵<br><span id="tab_name_4">老年女性</span></button>
        </div>

        <div style="display: flex; gap: 10px;" class="form-group">
            <div style="flex: 1;">
                <label>身份称呼 (可自定义)</label>
                <input type="text" id="memberName" oninput="saveCurrentSlot()">
            </div>
            <div style="flex: 1.3;">
                <label>生理阶段与审查侧重</label>
                <select id="roleFocus" onchange="saveCurrentSlot()">
                    <option value="成人控糖与护肝增肌">成人控糖 / 护肝增肌</option>
                    <option value="女性抗糖抗炎与轻体">女性抗糖 / 抗炎轻体</
