from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from typing import Optional
import google.generativeai as genai
from PIL import Image
import io
import json


app = FastAPI()

# 配置 Gemini
genai.configure(
    api_key="AQ.Ab8RN6Kku-4I3jyKj6qaDciRVQbVsUUrIDr9N10YnuCx4Q_ksw",
    transport="rest"
)

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 代谢健康与控糖审查</title>
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
            .substitute-box { background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 12px; padding: 14px; margin-top: 14px; }
            .substitute-box h3 { margin: 0 0 8px 0; color: #15803d; font-size: 1rem; display: flex; align-items: center; gap: 6px; }
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

            <button id="submitBtn" class="btn" style="background: #16a34a; margin-top: 10px; display: none;" onclick="analyze()">🚀 开始 AI 审查</button>
            <div id="loading">AI 正在深度审查成分与代谢指标...</div>
        </div>

        <div class="card" id="result">
            <h2>📊 审查结论</h2>
            <div id="scoreBadge" class="score-badge"></div>
            <h3 id="foodName" style="text-align: center; margin: 0 0 10px 0; font-size: 1.3rem;"></h3>
            <p><strong>🚨 风险排查：</strong><span id="riskList"></span></p>
            <p><strong>🫀 代谢影响：</strong><span id="metabolicImpact"></span></p>
            <p><strong>💡 行动建议：</strong><span id="actionAdvice"></span></p>

            <!-- 自动推荐替代方案专区（评分 > 5 分时自动亮起） -->
            <div id="substituteCard" class="substitute-box" style="display: none;">
                <h3>🔄 推荐更健康的低负担替代品</h3>
                <div id="substituteList"></div>
            </div>
        </div>

        <script>
            let selectedFile = null;

            // 页面加载时自动从本地恢复身体档案
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
                if (selectedFile || textVal) {
                    btn.style.display = 'block';
                } else {
                    btn.style.display = 'none';
                }
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

                    document.getElementById('foodName').innerText = data.food_name;
                    const badge = document.getElementById('scoreBadge');
                    badge.innerText = `${data.rating_level} 级 (${data.verdict_title})`;
                    badge.className = 'score-badge ' + (data.rating_level <= 3 ? 'safe' : data.rating_level <= 6 ? 'warning' : 'danger');

                    document.getElementById('riskList').innerText = data.risk_ingredients.length > 0 ? data.risk_ingredients.join(', ') : '纯净 / 未检出高危成分';
                    document.getElementById('metabolicImpact').innerText = data.metabolic_analysis;
                    document.getElementById('actionAdvice').innerText = data.action_advice;

                    // 关键特性：如果评级 > 5（中高风险），高亮展示健康替代品
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
    # 计算体征指标
    h_m = height / 100.0
    bmi = round(weight / (h_m * h_m), 1)

    system_prompt = f"""你是一位严格的控糖与内脏脂肪审查专家。
用户信息：性别 {gender}，年龄 {age}岁，身高 {height}cm，体重 {weight}kg，BMI {bmi}。

审查准则：
1. 一票否决：反式脂肪/氢化油/植脂末/代可可脂（归为 9~10 级）；
2. 核心红线：果葡糖浆（高果糖玉米糖浆）、添加蔗糖、高果糖水果；
3. 打分范围：1~10 级（1 级极力推荐，10 级极力避免/内脏脂肪刺客）；
4. 【核心强制要求】：若最终推荐等级 > 5（即 6~10 级），你必须在 `healthy_alternatives` 中给出 1~3 种同品类、口感接近但低代谢负担的“健康替代品”以及推荐理由（如：可乐 -> 无糖可乐/气泡水；葡萄/提子 -> 蓝莓/草莓；油炸点心 -> 原味坚果）。若评分 <= 5，则该列表为空。

请严格输出指定 JSON：
{{
  "food_name": "食品准确名称",
  "rating_level": 1到10的整数,
  "verdict_title": "极力推荐/适量谨慎/极力避免",
  "risk_ingredients": ["雷区成分1", "雷区成分2"],
  "metabolic_analysis": "对肝脏、胰岛素应激及内脏脂肪的影响简述",
  "action_advice": "摄入建议与频次控制",
  "healthy_alternatives": [
    {{"name": "替代食物名称", "reason": "为什么它更健康（例如低GI、不加重肝脏代谢等）"}}
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