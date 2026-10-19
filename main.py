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
        
        /* 功能 9：5人家庭身份切换栏 */
        .profile-tabs { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 14px; }
        .tab-btn { padding: 8px 4px; border: 1.5px solid #e2e8f0; border-radius: 10px; background: #f8fafc; color: #475569; font-size: 0.78rem; font-weight: 600; cursor: pointer; text-align: center; transition: 0.15s; line-height: 1.3; }
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
        
        <!-- 5个家庭成员槽位 -->
        <div class="profile-tabs" id="profileTabs">
            <button type="button" class="tab-btn active" onclick="switchSlot(0)" id="tab_0">👨<br><span id="tab_name_0">男性</span></button>
            <button type="button" class="tab-btn" onclick="switchSlot(1)" id="tab_1">👩<br><span id="tab_name_1">女性</span></button>
            <button type="button" class="tab-btn" onclick="switchSlot(2)" id="tab_2">👦<br><span id="tab_name_2">青少年</span></button>
            <button type="button" class="tab-btn" onclick="switchSlot(3)" id="tab_3">👴<br><span id="tab_name_3">健康长辈</span></button>
            <button type="button" class="tab-btn" onclick="switchSlot(4)" id="tab_4">👵<br><span id="tab_name_4">慢性病长辈</span></button>
        </div>

        <div style="display: flex; gap: 10px;" class="form-group">
            <div style="flex: 1;">
                <label>成员称呼 (可改名)</label>
                <input type="text" id="memberName" oninput="saveCurrentSlot()">
            </div>
            <div style="flex: 1.3;">
                <label>生理阶段与审查侧重</label>
                <select id="roleFocus" onchange="saveCurrentSlot()">
                    <option value="成人控糖与护肝增肌">成人控糖 / 护肝增肌</option>
                    <option value="女性抗糖抗炎与轻体">女性抗糖 / 抗炎轻体</option>
                    <option value="生长发育期青少年(严查添加剂与高果糖，重钙与蛋白)">发育期青少年 (促生长/严查添加剂)</option>
                    <option value="中老年慢病管理(稳血糖/护血管/控钠与反式脂肪)">老龄长辈 (稳血糖/护血管/控盐)</option>
                </select>
            </div>
        </div>

        <div style="display: flex; gap: 10px;" class="form-group">
            <div style="flex: 1;">
                <label>性别</label>
                <select id="gender" onchange="saveCurrentSlot()"><option value="男">男</option><option value="女">女</option></select>
            </div>
            <div style="flex: 1;">
                <label>年龄</label>
                <input type="number" id="age" oninput="saveCurrentSlot()">
            </div>
            <div style="flex: 1;">
                <label>身高(cm)</label>
                <input type="number" id="height" oninput="saveCurrentSlot()">
            </div>
            <div style="flex: 1;">
                <label>体重(kg)</label>
                <input type="number" id="weight" oninput="saveCurrentSlot()">
            </div>
        </div>
    </div>

    <div class="card">
        <h2>🍽️ 2. 提供食物信息 (二选一或结合)</h2>
        <div class="form-group">
            <label>方式 A：输入食物、品牌或餐厅名称</label>
            <input type="text" id="foodText" placeholder="如：麦当劳薯条、提子、霸王茶姬伯牙绝弦" oninput="toggleSubmitBtn()">
        </div>
        <div class="divider">或</div>
        <div class="form-group">
            <label>方式 B：拍摄实物或配料表图片</label>
            <input type="file" id="fileInput" accept="image/*" capture="environment" style="display:none;" onchange="handleFile(this)">
            <button type="button" class="btn" style="background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;" onclick="document.getElementById('fileInput').click()">📸 拍照 / 从相册选择</button>
            <img id="preview">
        </div>
        <button id="submitBtn" class="btn" style="background: #16a34a; margin-top: 10px; display: none;" onclick="analyze()">开始 AI 审查</button>
        <div id="loading">AI 正在结合该成员体质深度审查...</div>
    </div>

    <!-- 审查结论卡片 (支持导出长图) -->
    <div class="card" id="result">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h2 style="margin: 0;">📊 审查结论</h2>
            <span id="targetMemberBadge" class="role-badge" style="margin: 0;"></span>
        </div>
        <div id="scoreBadge" class="score-badge"></div>
        <h3 id="foodName" style="text-align: center; margin: 0 0 10px 0; font-size: 1.3rem;"></h3>
        
        <!-- 功能 1：方糖/油脂视觉折算 -->
        <div class="visual-box">
            <h4>💥 糖油刺客实物折算：</h4>
            <p id="visualEquivalent"></p>
        </div>

        <!-- 建议每日最高摄取上限 -->
        <div class="intake-box">
            <h4>⚖️ 专属每日最高摄取上限：</h4>
            <p id="dailyMaxIntake"></p>
        </div>

        <!-- 功能 2：代谢债务与运动自救消耗 -->
        <div class="debt-box">
            <h4>🏃 代谢债务与物理消耗代价：</h4>
            <p id="metabolicDebt"></p>
        </div>

        <!-- 功能 3：高亮排雷重点 -->
        <div style="margin: 12px 0;">
            <strong>🚨 配料表深度排雷（红黄绿划重点）：</strong>
            <div id="riskListTags" class="tag-container"></div>
        </div>

        <p style="line-height: 1.5;"><strong>🫀 针对该成员的生理与代谢影响：</strong><span id="metabolicImpact"></span></p>
        <p style="line-height: 1.5;"><strong>💡 进食与补救建议：</strong><span id="actionAdvice"></span></p>

        <!-- 功能 5：同店/同场景健康点餐公式 -->
        <div id="sameStoreCard" class="menu-box" style="display: none;">
            <h3>🍱 同店 / 同场景“安全点餐公式”</h3>
            <div id="sameStoreList"></div>
        </div>

        <!-- 自动推荐替代方案专区（评分 > 5 分时自动显示） -->
        <div id="substituteCard" class="substitute-box" style="display: none;">
            <h3>🔄 推荐更健康的低负担替代品</h3>
            <div id="substituteList"></div>
        </div>

        <!-- 底部按键 -->
        <div class="action-row">
            <button class="btn-action" onclick="saveAsImage()">🖼️ 保存长图到相册</button>
            <button class="btn-action" onclick="copyResultText()">📋 复制分析文字</button>
        </div>
    </div>

    <script>
        let selectedFile = null;
        let lastAnalysisData = null;
        let currentSlot = 0;

        // 预设 5 个家庭成员默认档案
        const defaultProfiles = [
            { name: "男性", role: "成人控糖与护肝增肌", gender: "男", age: 40, height: 180, weight: 75 },
            { name: "女性", role: "女性抗糖抗炎与轻体", gender: "女", age: 36, height: 165, weight: 52 },
            { name: "青少年", role: "生长发育期青少年(严查添加剂与高果糖，重钙与蛋白)", gender: "男", age: 12, height: 158, weight: 46 },
            { name: "健康长辈", role: "中老年慢病管理(稳血糖/护血管/控钠与反式脂肪)", gender: "男", age: 68, height: 170, weight: 68 },
            { name: "慢性病长辈", role: "中老年慢病管理(稳血糖/护血管/控钠与反式脂肪)", gender: "女", age: 66, height: 160, weight: 58 }
        ];

        let familyProfiles = [];

        window.onload = function() {
            const saved = localStorage.getItem('family_food_profiles_v1');
            if (saved) {
                try {
                    familyProfiles = JSON.parse(saved);
                    if (!Array.isArray(familyProfiles) || familyProfiles.length < 5) {
                        familyProfiles = JSON.parse(JSON.stringify(defaultProfiles));
                    }
                } catch(e) {
                    familyProfiles = JSON.parse(JSON.stringify(defaultProfiles));
                }
            } else {
                familyProfiles = JSON.parse(JSON.stringify(defaultProfiles));
            }
            const lastSlot = parseInt(localStorage.getItem('last_active_slot') || '0', 10);
            updateTabNames();
            switchSlot(isNaN(lastSlot) ? 0 : lastSlot);
        };

        function updateTabNames() {
            for (let i = 0; i < 5; i++) {
                const el = document.getElementById('tab_name_' + i);
                if (el && familyProfiles[i]) {
                    el.innerText = familyProfiles[i].name || ('成员' + (i + 1));
                }
            }
        }

        function switchSlot(index) {
            currentSlot = index;
            localStorage.setItem('last_active_slot', index.toString());
            for (let i = 0; i < 5; i++) {
                const btn = document.getElementById('tab_' + i);
                if (i === index) btn.classList.add('active');
                else btn.classList.remove('active');
            }
            const p = familyProfiles[index];
            document.getElementById('memberName').value = p.name || '';
            document.getElementById('roleFocus').value = p.role || '成人控糖与护肝增肌';
            document.getElementById('gender').value = p.gender || '男';
            document.getElementById('age').value = p.age || 30;
            document.getElementById('height').value = p.height || 170;
            document.getElementById('weight').value = p.weight || 65;
        }

        function saveCurrentSlot() {
            familyProfiles[currentSlot] = {
                name: document.getElementById('memberName').value.trim() || ('成员' + (currentSlot + 1)),
                role: document.getElementById('roleFocus').value,
                gender: document.getElementById('gender').value,
                age: document.getElementById('age').value,
                height: document.getElementById('height').value,
                weight: document.getElementById('weight').value
            };
            localStorage.setItem('family_food_profiles_v1', JSON.stringify(familyProfiles));
            updateTabNames();
        }

        function handleFile(input) {
            if (input.files && input.files[0]) {
                selectedFile = input.files[0];
                const reader = new FileReader();
                reader.onload = function(e) {
                    const img = document.getElementById('preview');
                    img.src = e.target.result;
                    img.style.display = 'block';
                    toggleSubmitBtn();
                }
                reader.readAsDataURL(selectedFile);
            }
        }

        function toggleSubmitBtn() {
            const textVal = document.getElementById('foodText').value.trim();
            const btn = document.getElementById('submitBtn');
            btn.style.display = (selectedFile || textVal) ? 'block' : 'none';
        }

        async function analyze() {
            const foodText = document.getElementById('foodText').value.trim();
            if (!selectedFile && !foodText) {
                alert('请至少上传一张照片或输入食物名称！');
                return;
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('result').style.display = 'none';

            const currentMember = familyProfiles[currentSlot];
            const formData = new FormData();
            formData.append('member_name', currentMember.name);
            formData.append('role_focus', currentMember.role);
            formData.append('gender', currentMember.gender);
            formData.append('age', currentMember.age);
            formData.append('height', currentMember.height);
            formData.append('weight', currentMember.weight);
            if (foodText) formData.append('food_name_input', foodText);
            if (selectedFile) formData.append('file', selectedFile);

            try {
                const res = await fetch('/api/analyze', { method: 'POST', body: formData });
                const resp = await res.json();
                const data = resp.data;
                lastAnalysisData = data;
                lastAnalysisData._memberName = currentMember.name;

                document.getElementById('targetMemberBadge').innerText = `👤 审查对象：${currentMember.name} (${currentMember.age}岁)`;
                document.getElementById('foodName').innerText = data.food_name;
                const badge = document.getElementById('scoreBadge');
                badge.innerText = `${data.rating_level} 级 (${data.verdict_title})`;
                badge.className = 'score-badge ' + (data.rating_level <= 3 ? 'safe' : data.rating_level <= 6 ? 'warning' : 'danger');

                document.getElementById('visualEquivalent').innerText = data.visual_equivalent || '无明显游离糖油折算风险';
                document.getElementById('dailyMaxIntake').innerText = data.daily_max_intake || '按常规膳食摄入即可';
                document.getElementById('metabolicDebt').innerText = data.metabolic_debt || '日常活动即可正常代谢';

                // 功能 3：高亮排雷标签渲染
                const tagsContainer = document.getElementById('riskListTags');
                tagsContainer.innerHTML = '';
                if (data.ingredient_highlights && data.ingredient_highlights.length > 0) {
                    data.ingredient_highlights.forEach(item => {
                        const div = document.createElement('div');
                        const tagClass = item.level === 'red' ? 'tag-red' : item.level === 'yellow' ? 'tag-yellow' : 'tag-green';
                        const itemDesc = item.desc || item.reason || item.description || '';
                        div.className = `ingredient-tag ${tagClass}`;
                        div.innerHTML = `<strong>${item.name}</strong>：${itemDesc}`;
                        tagsContainer.appendChild(div);
                    });
                } else {
                    tagsContainer.innerHTML = '<div class="ingredient-tag tag-green">成分纯净，未检出隐形糖或劣质油脂</div>';
                }

                document.getElementById('metabolicImpact').innerText = data.metabolic_analysis;
                document.getElementById('actionAdvice').innerText = data.action_advice;

                // 功能 5：同店/同场景安全点餐公式渲染
                const storeCard = document.getElementById('sameStoreCard');
                if (data.same_store_safe_combos && data.same_store_safe_combos.length > 0) {
                    document.getElementById('sameStoreList').innerHTML = data.same_store_safe_combos.map(item => {
                        const comboName = item.combo || item.name || '推荐搭配';
                        const comboWhy = item.why || item.reason || item.desc || '';
                        return `<div class="menu-item">• <strong>${comboName}</strong>：${comboWhy}</div>`;
                    }).join('');
                    storeCard.style.display = 'block';
                } else {
                    storeCard.style.display = 'none';
                }

                // 健康替代品渲染（修复 undefined 问题）
                const subCard = document.getElementById('substituteCard');
                if (data.rating_level > 5 && data.healthy_alternatives && data.healthy_alternatives.length > 0) {
                    document.getElementById('substituteList').innerHTML = data.healthy_alternatives.map(item => {
                        const altName = item.name || item.food || '替代方案';
                        const altReason = item.reason || item.desc || item.why || item.description || '低升糖、低代谢负担';
                        return `<div class="sub-item">• <strong>${altName}</strong>：${altReason}</div>`;
                    }).join('');
                    subCard.style.display = 'block';
                } else {
                    subCard.style.display = 'none';
                }

                document.getElementById('result').style.display = 'block';
                document.getElementById('result').scrollIntoView({ behavior: 'smooth' });
            } catch(e) {
                alert('分析失败，请检查网络或重试');
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('submitBtn').disabled = false;
            }
        }

        // 保存长图
        function saveAsImage() {
            const card = document.getElementById('result');
            const actionRow = card.querySelector('.action-row');
            actionRow.style.display = 'none';

            html2canvas(card, {
                scale: 2,
                backgroundColor: '#ffffff',
                useCORS: true
            }).then(canvas => {
                actionRow.style.display = 'flex';
                const link = document.createElement('a');
                const mName = lastAnalysisData && lastAnalysisData._memberName ? lastAnalysisData._memberName : '';
                const fName = lastAnalysisData ? lastAnalysisData.food_name : '食物';
                link.download = `${mName}_${fName}_健康审查结论.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();
            }).catch(() => {
                actionRow.style.display = 'flex';
                alert('截图生成失败，请稍后重试');
            });
        }

        // 复制纯文本
        function copyResultText() {
            if (!lastAnalysisData) return;
            const d = lastAnalysisData;
            let text = `【AI 代谢健康与控糖审查结论】\\n`;
            text += `审查对象：${d._memberName || '默认成员'}\\n`;
            text += `食品名称：${d.food_name}\\n`;
            text += `推荐评级：${d.rating_level} 级 (${d.verdict_title})\\n`;
            text += `实物折算：${d.visual_equivalent}\\n`;
            text += `每日上限：${d.daily_max_intake}\\n`;
            text += `代谢债务：${d.metabolic_debt}\\n`;
            
            if (d.ingredient_highlights && d.ingredient_highlights.length > 0) {
                text += `\\n【配料深度排雷】\\n`;
                d.ingredient_highlights.forEach(item => {
                    const desc = item.desc || item.reason || '';
                    text += `• [${item.level === 'red' ? '高危' : item.level === 'yellow' ? '注意' : '健康'}] ${item.name}：${desc}\\n`;
                });
            }

            text += `\\n生理与代谢影响：${d.metabolic_analysis}\\n`;
            text += `行动建议：${d.action_advice}\\n`;

            if (d.same_store_safe_combos && d.same_store_safe_combos.length > 0) {
                text += `\\n【同店/同场景安全点餐公式】\\n`;
                d.same_store_safe_combos.forEach(item => {
                    text += `• ${item.combo || item.name}：${item.why || item.reason || ''}\\n`;
                });
            }

            if (d.rating_level > 5 && d.healthy_alternatives && d.healthy_alternatives.length > 0) {
                text += `\\n【推荐健康替代品】\\n`;
                d.healthy_alternatives.forEach(item => {
                    const reason = item.reason || item.desc || item.why || '';
                    text += `• ${item.name}：${reason}\\n`;
                });
            }

            navigator.clipboard.writeText(text).then(() => {
                alert('✅ 审查结果已复制到剪贴板！');
            }).catch(() => {
                alert('复制失败，请手动长按复制');
            });
        }
    </script>
</body>
</html>
"""

@app.post("/api/analyze")
async def analyze_api(
    member_name: str = Form("本人"),
    role_focus: str = Form("成人控糖与护肝增肌"),
    gender: str = Form(...),
    age: int = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    food_name_input: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    h_m = height / 100.0
    bmi = round(weight / (h_m * h_m), 1)

    system_prompt = f"""你是一位严格的临床营养、控糖与代谢健康审查专家。
当前进食者档案：
- 称呼：{member_name}
- 核心生理阶段与目标：{role_focus}
- 体征数据：性别 {gender}，年龄 {age}岁，身高 {height}cm，体重 {weight}kg，BMI {bmi}。

审查准则：
1. 一票否决：反式脂肪/氢化植物油/植脂末/代可可脂/起酥油（直接归为 9~10 级）；
2. 核心红线：果葡糖浆（高果糖玉米糖浆）、添加蔗糖、麦芽糊精、高游离果糖；
3. 【人群定制化审查（功能9）】：
   - 若为“生长发育期青少年”：严查人工合成色素、防腐剂（苯甲酸钠等）、隐形咖啡因、高果糖（抑制生长激素峰值及影响钙吸收），评估其对骨骼生长、专注力及性早熟/肥胖的影响；
   - 若为“老龄长辈”：严查高升糖（GI/GL）、高钠隐形盐、氧化劣质油脂与反式脂肪，重点防范餐后血糖剧烈波动、血管内皮炎症及尿酸/血脂负担；
   - 若为“成人控糖/增肌或抗糖轻体”：重点评估肝脏果糖新生脂肪、胰岛素抵抗、内脏脂肪堆积及肌肉合成效率。
4. 【功能1-糖油刺客实物折算】：将该食物单份摄入量中的添加糖或氧化油脂，折算为直观实物（如“约等于吃下 X 块方糖 / 喝下 X 瓷勺反复煎炸氧化油”）。
5. 【功能2-代谢债务与消耗代价】：结合该成员 {age}岁、{weight}kg 的体能特点，给出适合该年龄段的运动消耗对冲方案（如青少年推荐跳绳/篮球/摸高，成人推荐配速跑/抗阻深蹲，老年人推荐餐后快走/八段锦/靠墙静蹲）。
6. 【功能3-配料深度排雷高亮】：按 red(高危/促炎/一票否决)、yellow(隐形糖/升糖刺客/添加剂)、green(天然优质营养) 给出 2~4 个核心成分剖析，字段名严格为 name、desc、level。
7. 【功能5-同店/同场景安全点餐公式】：若用户输入的食物涉及连锁快餐（如麦当劳/肯德基/汉堡王）、茶饮咖啡店（如霸王茶姬/瑞幸/喜茶）、便利店或常见外卖餐厅，必须在 `same_store_safe_combos` 中给出 1~2 套该店能买到的“低升糖高蛋白安全点餐组合”及理由；若为普通生鲜食材（如“提子”），则给出该食材的“控糖黄金搭配吃法”（如搭配原味坚果或无糖希腊酸奶延缓吸收）。
8. 【健康替代品】：评分 > 5 时，必须在 `healthy_alternatives` 中给出 2 种适合该成员年龄段的低负担替代食物，字段名严格为 name 和 reason（严禁留空）。

请严格输出以下 JSON 格式：
{{
  "food_name": "食品准确名称",
  "rating_level": 1到10的整数,
  "verdict_title": "极力推荐/适量谨慎/极力避免",
  "visual_equivalent": "强视觉冲击力的实物折算",
  "daily_max_intake": "针对该成员({member_name}, {age}岁)的每日最高摄入上限与控制理由",
  "metabolic_debt": "贴合该成员年龄与体重({weight}kg)的运动消耗或餐后对冲方案",
  "ingredient_highlights": [
    {{"name": "成分名", "desc": "马甲伪装与对该成员的具体危害或益处", "level": "red或yellow或green"}}
  ],
  "metabolic_analysis": "针对该成员生理阶段（如青少年生长发育/老人血管血糖/成人肝脏内脏脂肪）的深度影响剖析",
  "action_advice": "具体的进食顺序、时间窗口或紧急补救措施",
  "same_store_safe_combos": [
    {{"combo": "同店安全点餐公式或黄金搭配吃法", "why": "为什么这套组合能稳住血糖与代谢"}}
  ],
  "healthy_alternatives": [
    {{"name": "替代食物名称", "reason": "为什么更适合该家庭成员食用"}}
  ]
}}"""

    content_payload = [system_prompt]
    if food_name_input:
        content_payload.append(f"【用户直接输入的食物或品牌名称】：{food_name_input}")
    if file and file.filename:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        content_payload.append(image)
        content_payload.append("请结合上传的包装/配料表/食物照片进行严格审查。")
    else:
        content_payload.append("用户未上传图片，请依据该食物/餐厅的标准配方与常规升糖指数(GI)/果糖及油脂含量进行深度审查。")

    model = genai.GenerativeModel(
        model_name="gemini-3.8-flash",
        generation_config={"response_mime_type": "application/json", "temperature": 0.2}
    )
    response = model.generate_content(content_payload)
    return {"status": "success", "data": json.loads(response.text)}
