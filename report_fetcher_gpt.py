#!/usr/bin/env python3
"""
券商研报AI深度分析系统
功能：
1. 使用GPT模型进行智能摘要
2. 提取关键财务数据和图表信息
3. 同一股票多家券商观点对比
4. 生成投资评级分布图
"""

import requests
import json
import pdfplumber
import re
import os
from datetime import datetime, timedelta
from io import BytesIO
from collections import defaultdict

# OpenAI API配置（使用环境变量）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

def fetch_reports():
    """从东方财富获取研报列表"""
    url = "https://reportapi.eastmoney.com/report/list"
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    
    params = {
        "industryCode": "*",
        "pageNo": 1,
        "pageSize": 30,
        "beginTime": yesterday,
        "endTime": today,
        "qType": 0
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"获取研报列表失败: {e}")
        return []

def fetch_report_content(info_code, encode_url):
    """获取研报PDF"""
    meta_url = "https://reportapi.eastmoney.com/report/content"
    params = {
        "infoCode": info_code,
        "encodeUrl": encode_url
    }
    
    try:
        response = requests.get(meta_url, params=params, timeout=10)
        data = response.json()
        report_data = data.get('data', [{}])[0]
        
        pdf_url = report_data.get('attachUrl', '')
        
        if pdf_url:
            pdf_response = requests.get(pdf_url, timeout=15)
            if pdf_response.status_code == 200:
                text = extract_pdf_text(pdf_response.content)
                return text, pdf_url
        
        return None, None
    except Exception as e:
        return None, None

def extract_pdf_text(pdf_content):
    """从PDF中提取完整文本"""
    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            full_text = ""
            for page in pdf.pages[:5]:  # 读前5页
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            return full_text
    except:
        return None

def gpt_summarize(text, stock_name, broker, rating):
    """使用GPT模型进行智能摘要"""
    if not text or len(text) < 100:
        return None, None, None, None
    
    # 清理文本
    text = re.sub(r'\s+', ' ', text)
    text = text[:6000]  # 限制长度
    
    # 构建prompt
    prompt = f"""请对以下券商研报进行专业分析，提取关键信息：

股票：{stock_name}
券商：{broker}
评级：{rating}

研报内容：
{text}

请按以下格式输出（JSON格式）：
{{
    "投资逻辑": ["要点1", "要点2", "要点3"],
    "关键数据": {{
        "EPS": "xx元",
        "PE": "xx倍",
        "目标价": "xx元",
        "营收": "xx亿"
    }},
    "风险提示": ["风险1", "风险2"],
    "核心结论": "一句话总结"
}}

要求：
1. 投资逻辑要具体、有数据支撑
2. 关键数据要准确，没有的数据写"未披露"
3. 风险提示要具体，不是泛泛而谈
4. 核心结论控制在50字以内"""

    try:
        # 如果有OpenAI API Key，调用GPT
        if OPENAI_API_KEY:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                },
                timeout=30
            )
            result = response.json()
            content = result['choices'][0]['message']['content']
            # 解析JSON
            import json
            parsed = json.loads(content)
            return (
                parsed.get('投资逻辑', []),
                parsed.get('关键数据', {}),
                parsed.get('风险提示', []),
                parsed.get('核心结论', '')
            )
        else:
            # 没有API Key，使用本地规则提取
            return local_extract(text)
    except Exception as e:
        print(f"GPT分析失败: {e}")
        return local_extract(text)

def local_extract(text):
    """本地规则提取（备用方案）"""
    # 提取投资要点
    points = []
    patterns = [
        r'投资要点[：:]?(.*?)(?=盈利预测|风险提示|核心逻辑|$)',
        r'核心逻辑[：:]?(.*?)(?=盈利预测|风险提示|$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            bullet_points = re.split(r'[◼➢•●]|[\d]+[、\.]', content)
            for point in bullet_points:
                point = point.strip()
                point = re.sub(r'\s+', ' ', point)
                if len(point) > 20 and len(point) < 200:
                    points.append(point)
            if points:
                break
    
    # 提取关键数据
    data = {}
    eps_match = re.search(r'EPS.*?([\d\.]+).*?([\d\.]+).*?([\d\.]+)', text)
    if eps_match:
        data['EPS'] = f"{eps_match.group(1)} / {eps_match.group(2)} / {eps_match.group(3)} 元"
    
    pe_match = re.search(r'PE.*?([\d\.]+).*?([\d\.]+).*?([\d\.]+)', text)
    if pe_match:
        data['PE'] = f"{pe_match.group(1)} / {pe_match.group(2)} / {pe_match.group(3)} 倍"
    
    target_match = re.search(r'目标价.*?([\d\.]+)', text)
    if target_match:
        data['目标价'] = f"{target_match.group(1)} 元"
    
    # 提取风险
    risks = []
    risk_pattern = r'风险提示[：:]?(.*?)(?=投资建议|盈利预测|$)'
    match = re.search(risk_pattern, text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        risk_points = re.split(r'[◼➢•●]|[\d]+[、\.]', content)
        for risk in risk_points:
            risk = risk.strip()
            if len(risk) > 10 and len(risk) < 100:
                risks.append(risk)
    
    # 核心结论
    conclusion = points[0] if points else ""
    
    return points[:3], data, risks[:3], conclusion[:80]

def group_by_stock(reports):
    """按股票分组，用于对比分析"""
    stock_groups = defaultdict(list)
    for r in reports:
        stock_code = r.get('stockCode', '')
        if stock_code:
            stock_groups[stock_code].append(r)
    return stock_groups

def analyze_stock_consensus(stock_groups):
    """分析同一股票的多券商观点"""
    consensus = {}
    for stock_code, reports in stock_groups.items():
        if len(reports) > 1:  # 只有多家券商覆盖才有对比价值
            ratings = [r.get('emRatingName', '') for r in reports]
            brokers = [r.get('orgSName', '') for r in reports]
            
            # 统计评级分布
            rating_counts = defaultdict(int)
            for r in ratings:
                if r:
                    rating_counts[r] += 1
            
            consensus[stock_code] = {
                'stockName': reports[0].get('stockName', ''),
                'brokers': brokers,
                'ratings': rating_counts,
                'count': len(reports)
            }
    return consensus

def generate_rating_chart(consensus):
    """生成评级分布的文本图表"""
    charts = []
    for stock_code, data in consensus.items():
        stock_name = data['stockName']
        ratings = data['ratings']
        
        chart = f"**{stock_name}（{stock_code}）**\n"
        chart += f"共{data['count']}家券商覆盖：{', '.join(data['brokers'])}\n\n"
        
        # 评级分布
        for rating, count in sorted(ratings.items(), key=lambda x: -x[1]):
            bar = "█" * count + "░" * (data['count'] - count)
            chart += f"{rating}: {bar} ({count})\n"
        
        charts.append(chart)
    
    return charts

def categorize_reports(reports):
    """分类研报"""
    categories = {
        "宏观策略": [],
        "行业研究": [],
        "个股研报": [],
        "其他": []
    }
    
    for r in reports:
        title = r.get('title', '')
        if any(kw in title for kw in ['策略', '市场', '宏观', '大势', '季度', '年度']):
            categories["宏观策略"].append(r)
        elif any(kw in title for kw in ['行业', '产业', '板块', '专题']):
            categories["行业研究"].append(r)
        elif r.get('stockName'):
            categories["个股研报"].append(r)
        else:
            categories["其他"].append(r)
    
    return categories

def format_report_message():
    """格式化研报消息"""
    reports = fetch_reports()
    
    if not reports:
        return "暂无研报数据"
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y年%m月%d日')
    
    # 按股票分组
    stock_groups = group_by_stock(reports)
    consensus = analyze_stock_consensus(stock_groups)
    
    message = f"📊 **{yesterday} 券商研报AI深度分析**\n\n"
    message += f"*数据来源：东方财富 | 共 {len(reports)} 篇研报*\n"
    message += f"*AI模型：{"GPT-3.5" if OPENAI_API_KEY else "本地NLP"} | 覆盖 {len(stock_groups)} 只股票*\n"
    message += "---\n\n"
    
    # 一、多券商观点对比（热点股票）
    if consensus:
        message += "## 🔥 热点股票：多券商观点对比\n\n"
        charts = generate_rating_chart(consensus)
        for chart in charts[:3]:  # 最多显示3只
            message += chart + "\n"
        message += "---\n\n"
    
    # 二、个股深度分析
    categories = categorize_reports(reports)
    
    if categories["个股研报"]:
        message += "## 📈 个股深度分析\n\n"
        
        # 选择重点股票（多家覆盖或市值大的）
        priority_stocks = []
        for stock_code, data in sorted(consensus.items(), key=lambda x: -x[1]['count']):
            priority_stocks.append(stock_code)
        
        # 分析前4只重点股票
        analyzed = 0
        analyzed_codes = set()
        for r in categories["个股研报"]:
            if analyzed >= 4:
                break
            
            stock = r.get('stockName', '')
            code = r.get('stockCode', '')
            
            # 跳过已分析的重复股票
            if code in analyzed_codes:
                continue
            
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            rating = r.get('emRatingName', '')
            industry = r.get('indvInduName', '')
            info_code = r.get('infoCode', '')
            encode_url = r.get('encodeUrl', '')
            
            message += f"### {stock}（{code}）\n\n"
            
            if industry:
                message += f"🏭 **行业**：{industry}\n"
            message += f"📊 **券商**：{broker}"
            if rating:
                message += f" | **评级**：{rating}"
            message += "\n\n"
            
            # AI分析
            print(f"AI深度分析 {stock}...")
            text, pdf_url = fetch_report_content(info_code, encode_url)
            points, data, risks, conclusion = gpt_summarize(text, stock, broker, rating)
            
            # 核心结论
            if conclusion:
                message += f"💡 **核心结论**：{conclusion}\n\n"
            
            # 投资逻辑
            if points:
                message += "📋 **投资逻辑**：\n"
                for i, point in enumerate(points, 1):
                    message += f"{i}. {point}\n"
                message += "\n"
            
            # 关键数据
            if data:
                message += "📊 **关键数据**：\n"
                for key, value in data.items():
                    message += f"• {key}：{value}\n"
                message += "\n"
            
            # 风险提示
            if risks:
                message += "⚠️ **风险提示**：\n"
                for risk in risks:
                    message += f"• {risk}\n"
                message += "\n"
            
            # 同股票其他券商观点
            if code in consensus and consensus[code]['count'] > 1:
                message += "🏦 **其他券商观点**：\n"
                for other_broker in consensus[code]['brokers']:
                    if other_broker != broker:
                        message += f"• {other_broker} 也覆盖此股\n"
                message += "\n"
            
            if pdf_url:
                message += f"📄 [下载PDF原文]({pdf_url})\n"
            message += "\n---\n\n"
            
            analyzed_codes.add(code)
            analyzed += 1
    
    # 三、行业研究
    if categories["行业研究"]:
        message += "## 🏭 行业研究精选\n\n"
        for i, r in enumerate(categories["行业研究"][:4], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            industry = r.get('indvInduName', '')
            info_code = r.get('infoCode', '')
            encode_url = r.get('encodeUrl', '')
            
            # 获取PDF链接
            _, pdf_url = fetch_report_content(info_code, encode_url) if encode_url else (None, None)
            
            core_view = title.split('：')[-1] if '：' in title else title
            message += f"**{i}. {industry or '行业研究'} | {broker}**\n"
            message += f"💡 {core_view}\n"
            if pdf_url:
                message += f"📄 [下载PDF原文]({pdf_url})\n"
            message += "\n"
    
    # 四、宏观策略
    if categories["宏观策略"]:
        message += "## 🌍 宏观策略\n\n"
        for i, r in enumerate(categories["宏观策略"][:2], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            info_code = r.get('infoCode', '')
            encode_url = r.get('encodeUrl', '')
            
            # 获取PDF链接
            _, pdf_url = fetch_report_content(info_code, encode_url) if encode_url else (None, None)
            
            core_view = title.split('：')[-1] if '：' in title else title
            message += f"**{i}. {broker}**：{core_view}\n"
            if pdf_url:
                message += f"📄 [下载PDF原文]({pdf_url})\n"
            message += "\n"
    
    message += "---\n"
    message += "⏰ *每天早上7:38自动推送*\n"
    message += f"🤖 *AI模型：{"GPT-3.5 Turbo" if OPENAI_API_KEY else "本地NLP引擎"}*\n"
    message += "📊 *数据来源：东方财富研报中心*\n"
    message += "⚠️ *投资有风险，研报观点仅供参考，不构成投资建议*"
    
    return message

if __name__ == "__main__":
    msg = format_report_message()
    print(msg)
