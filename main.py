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
        h2 { font-size: 1.15rem; margin-top: 0; margin-bottom: 14px; color: #0f172a; }
        .form-group { margin-bottom: 12px; }
        label { display: block; font-size: 0.85rem; color: #64748b; margin-bottom: 4px; font-weight: 500; }
        input, select { width: 100%; padding: 12px; border: 1px solid #cbd5e1; border-radius: 10px; box-sizing: border-box; font-size: 0.95rem; }
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
        .substitute-box { background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 12px; padding: 14px; margin-top: 14px; }
        .substitute-box h3 { margin: 0 0 8px 0; color: #15803d; font-size: 1rem; display: flex; align-items: center; gap: 6px; }
        .action-row { display: flex; gap: 10px; margin-top: 16px; }
        .btn-action { flex: 1; padding: 12px 8px; border-radius: 10px; border: 1px solid #cbd5e1; background: #f8fafc; color: #334155; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: 0.15s; }
        .btn-action:active { background: #e2e8f0; }
    </style>
</head>
<body>
    <div class="card">
        <h2>👤 1. 身体档案 <span style="font-size: 0.75rem; color: #16a34a; font-weight: normal;">(已自动记忆保存)</span></h2>
        <div class="form-group">
            <label>性别</label>
            <select id="gender" onchange="saveProfile()"><option value="男">男</option><option value="女">女</option></select>
        </div>
        <div class="form-group">
            <label>年龄</label>
            <input type="number" id="age" value="28" oninput="saveProfile()">
        </div>
        <div class="form-group">
            <label>身高 (cm) / 体重 (kg)</label>
            <div style="display: flex; gap: 10px;">
                <input type="number" id="height" value="175" placeholder="身高" oninput="saveProfile()">
                <input type="number" id="weight" value="70" placeholder="体重" oninput="saveProfile()">
            </div>
        </div>
    </div>

    <div class="card">
        <h2>🍽️ 2. 提供食物信息 (二选一或结合)</h2>
        <div class="form-group">
            <label>方式 A：输入食物或商品名称</label>
            <input type="text" id="foodText" placeholder="如：提子、巨无霸汉堡、黑糖珍珠奶茶" oninput="toggleSubmitBtn()">
        </div>
        <div class="divider">或</div>
        <div class="form-group">
            <label>方式 B：拍摄实物或配料表图片</label>
            <input type="file" id="fileInput" accept="image/*" capture="environment" style="display:none;" onchange="handleFile(this)">
            <button type="button" class="btn" style="background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;" onclick="document.getElementById('fileInput').click()">📸 拍照 / 从相册选择</button>
            <img id="preview">
        </div>
        <button id="submitBtn" class="btn" style="background: #16a34a; margin-top: 10px; display: none;" onclick="analyze()">食物健康审查</button>
        <div id="loading">AI 正在深度审查成分与代谢指标...</div>
    </div>

    <!-- 审查结论卡片 (支持导出长图) -->
    <div class="card" id="result">
        <h2>📊 审查结论</h2>
        <div id="scoreBadge" class="score-badge"></div>
        <h3 id="foodName" style="text-align: center; margin: 0 0 10px 0; font-size: 1.3rem;"></h3>
        
        <!-- 每日最多摄入量推荐 -->
        <div class="intake-box">
            <h4>⚖️ 建议每日最高摄取上限：</h4>
            <p id="dailyMaxIntake"></p>
        </div>

        <p><strong>🚨 风险排查：</strong><span id="riskList"></span></p>
        <p><strong>🫀 代谢影响：</strong><span id="metabolicImpact"></span></p>
        <p><strong>💡 行动建议：</strong><span id="actionAdvice"></span></p>

        <!-- 自动推荐替代方案专区（评分 > 5 分时自动亮起） -->
        <div id="substituteCard" class="substitute-box" style="display: none;">
            <h3>🔄 推荐更健康的低负担替代品</h3>
            <div id="substituteList"></div>
        </div>

        <!-- 底部功能按键：存为图片与复制文字 -->
        <div class="action-row">
            <button class="btn-action" onclick="saveAsImage()">🖼️ 保存长图到相册</button>
            <button class="btn-action" onclick="copyResultText()">📋 复制分析文字</button>
        </div>
    </div>

    <script>
        let selectedFile = null;
        let lastAnalysisData = null;

        window.onload = function() {
            const profile = JSON.parse(localStorage.getItem('user_food_profile') || '{}');
            if (profile.gender) document.getElementById('gender').value = profile.gender;
            if (profile.age) document.getElementById('age').value = profile.age;
            if (profile.height) document.getElementById('height').value = profile.height;
            if (profile.weight) document.getElementById('weight').value = profile.weight;
        };

        function saveProfile() {
            const profile = {
                gender: document.getElementById('gender').value,
                age: document.getElementById('age').value,
                height: document.getElementById('height').value,
                weight: document.getElementById('weight').value
            };
            localStorage.setItem('user_food_profile', JSON.stringify(profile));
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

            const formData = new FormData();
            formData.append('gender', document.getElementById('gender').value);
            formData.append('age', document.getElementById('age').value);
            formData.append('height', document.getElementById('height').value);
            formData.append('weight', document.getElementById('weight').value);
            if (foodText) formData.append('food_name_input', foodText);
            if (selectedFile) formData.append('file', selectedFile);

            try {
                const res = await fetch('/api/analyze', { method: 'POST', body: formData });
                const resp = await res.json();
                const data = resp.data;
                lastAnalysisData = data;

                document.getElementById('foodName').innerText = data.food_name;
                const badge = document.getElementById('scoreBadge');
                badge.innerText = `${data.rating_level} 级 (${data.verdict_title})`;
                badge.className = 'score-badge ' + (data.rating_level <= 3 ? 'safe' : data.rating_level <= 6 ? 'warning' : 'danger');

                document.getElementById('dailyMaxIntake').innerText = data.daily_max_intake;
                document.getElementById('riskList').innerText = data.risk_ingredients.length > 0 ? data.risk_ingredients.join(', ') : '纯净 / 未检出高危成分';
                document.getElementById('metabolicImpact').innerText = data.metabolic_analysis;
                document.getElementById('actionAdvice').innerText = data.action_advice;

                const subCard = document.getElementById('substituteCard');
                if (data.rating_level > 5 && data.healthy_alternatives && data.healthy_alternatives.length > 0) {
                    document.getElementById('substituteList').innerHTML = data.healthy_alternatives.map(item => `<div>• <strong>${item.name}</strong>：${item.reason}</div>`).join('');
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

        // 保存页面结论为长图
        function saveAsImage() {
            const card = document.getElementById('result');
            // 临时隐藏操作按钮避免出现在截图里
            const actionRow = card.querySelector('.action-row');
            actionRow.style.display = 'none';

            html2canvas(card, {
                scale: 2,
                backgroundColor: '#ffffff',
                useCORS: true
            }).then(canvas => {
                actionRow.style.display = 'flex';
                const link = document.createElement('a');
                link.download = `${lastAnalysisData ? lastAnalysisData.food_name : '食物'}_健康审查结论.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();
            }).catch(() => {
                actionRow.style.display = 'flex';
                alert('截图生成失败，请稍后重试');
            });
        }

        // 复制纯文本信息
        function copyResultText() {
            if (!lastAnalysisData) return;
            const d = lastAnalysisData;
            let text = `【AI 代谢健康与控糖审查结论】\n`;
            text += `食品名称：${d.food_name}\n`;
            text += `推荐评级：${d.rating_level} 级 (${d.verdict_title})\n`;
            text += `每日摄入上限：${d.daily_max_intake}\n`;
            text += `风险成分：${d.risk_ingredients.length > 0 ? d.risk_ingredients.join('、') : '无明显高危成分'}\n`;
            text += `代谢影响：${d.metabolic_analysis}\n`;
            text += `行动建议：${d.action_advice}\n`;

            if (d.rating_level > 5 && d.healthy_alternatives && d.healthy_alternatives.length > 0) {
                text += `\n【推荐健康替代品】\n`;
                d.healthy_alternatives.forEach(item => {
                    text += `• ${item.name}：${item.reason}\n`;
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
    gender: str = Form(...),
    age: int = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    food_name_input: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    h_m = height / 100.0
    bmi = round(weight / (h_m * h_m), 1)

    system_prompt = f"""你是一位严格的控糖与内脏脂肪审查专家。
用户信息：性别 {gender}，年龄 {age}岁，身高 {height}cm，体重 {weight}kg，BMI {bmi}。

审查准则：
1. 一票否决：反式脂肪/氢化油/植脂末/代可可脂（归为 9~10 级）；
2. 核心红线：果葡糖浆（高果糖玉米糖浆）、添加蔗糖、高果糖水果；
3. 打分范围：1~10 级（1 级极力推荐，10 级极力避免/内脏脂肪刺客）；
4. 【摄入量上限测算】：必须根据用户该性别、年龄、身高、体重及 BMI 的基础代谢负荷，计算并明确给出用户一天摄取该食物的“绝对最高限量”（如：不超过 50g / 半个 / 0g 坚决不碰），并附带一句控制理由。
5. 【健康替代强制要求】：若最终推荐等级 > 5（即 6~10 级），你必须在 `healthy_alternatives` 中给出 1~3 种同品类、口感接近但低代谢负担的“健康替代品”及理由。若评分 <= 5，则该列表为空。

请严格输出指定 JSON：
{{
  "food_name": "食品准确名称",
  "rating_level": 1到10的整数,
  "verdict_title": "极力推荐/适量谨慎/极力避免",
  "daily_max_intake": "结合用户体征的每日摄入上限量描述（例如：不超过 40 克（约半个），若今日已有主食需降为 0）",
  "risk_ingredients": ["雷区成分1", "雷区成分2"],
  "metabolic_analysis": "对肝脏、胰岛素应激及内脏脂肪的影响简述",
  "action_advice": "摄入建议与频次控制",
  "healthy_alternatives": [
    {{"name": "替代食物名称", "reason": "为什么更健康"}}
  ]
}}"""

    content_payload = [system_prompt]
    if food_name_input:
        content_payload.append(f"【用户直接输入的食物名称】：{food_name_input}")
    if file and file.filename:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        content_payload.append(image)
        content_payload.append("请结合上传的包装/食物照片进行严格审查。")
    else:
        content_payload.append("用户未上传图片，请依据该食物的标准配方与常规升糖指数(GI)/果糖含量进行深度审查。")

    model = genai.GenerativeModel(
        model_name="gemini-3.8-flash",
        generation_config={"response_mime_type": "application/json", "temperature": 0.2}
    )
    response = model.generate_content(content_payload)
    return {"status": "success", "data": json.loads(response.text)}
