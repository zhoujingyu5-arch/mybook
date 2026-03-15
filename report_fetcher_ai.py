#!/usr/bin/env python3
import requests
import json
import pdfplumber
import re
from datetime import datetime, timedelta
from io import BytesIO

def fetch_reports():
    """从东方财富获取研报列表"""
    url = "https://reportapi.eastmoney.com/report/list"
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    
    params = {
        "industryCode": "*",
        "pageNo": 1,
        "pageSize": 15,  # 限制数量保证质量
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
    """获取研报详细内容和PDF"""
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
        print(f"获取研报内容失败: {e}")
        return None, None

def extract_pdf_text(pdf_content):
    """从PDF中提取完整文本"""
    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            full_text = ""
            for page in pdf.pages[:4]:  # 读前4页获取更多信息
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            return full_text
    except Exception as e:
        print(f"PDF解析失败: {e}")
        return None

def ai_summarize(text, stock_name, broker):
    """使用AI模型对研报进行智能摘要"""
    if not text:
        return None, None, None
    
    # 清理文本
    text = re.sub(r'\s+', ' ', text)
    text = text[:8000]  # 限制长度避免超出处理能力
    
    # 提取关键信息
    summary = extract_investment_points(text)
    predictions = extract_predictions(text)
    risks = extract_risks(text)
    
    return summary, predictions, risks

def extract_investment_points(text):
    """提取投资要点/核心逻辑"""
    points = []
    
    # 匹配投资要点部分
    patterns = [
        r'投资要点[：:]?(.*?)(?=盈利预测|风险提示|核心逻辑|$)',
        r'核心逻辑[：:]?(.*?)(?=盈利预测|风险提示|$)',
        r'事件[：:]?(.*?)(?=点评|分析|核心观点|$)',
        r'主要观点[：:]?(.*?)(?=盈利预测|风险提示|$)',
        r'核心观点[：:]?(.*?)(?=盈利预测|风险提示|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # 分割成要点
            bullet_points = re.split(r'[◼➢•●]|[\d]+[、\.]', content)
            for point in bullet_points:
                point = point.strip()
                point = re.sub(r'\s+', ' ', point)
                if len(point) > 20 and len(point) < 200:
                    points.append(point)
            if points:
                break
    
    # 如果没找到，提取文本中的关键句子
    if not points:
        sentences = re.split(r'[。；]', text)
        for sent in sentences:
            if any(kw in sent for kw in ['增长', '提升', '改善', '受益', '领先', '优势', '推荐', '买入']):
                if len(sent) > 30 and len(sent) < 150:
                    points.append(sent.strip())
            if len(points) >= 3:
                break
    
    return points[:3]  # 返回最多3个要点

def extract_predictions(text):
    """提取盈利预测和目标价"""
    predictions = {}
    
    # 提取EPS
    eps_match = re.search(r'EPS.*?([\d\.]+).*?([\d\.]+).*?([\d\.]+)', text)
    if eps_match:
        predictions['EPS'] = [eps_match.group(1), eps_match.group(2), eps_match.group(3)]
    
    # 提取PE
    pe_match = re.search(r'PE.*?([\d\.]+).*?([\d\.]+).*?([\d\.]+)', text)
    if pe_match:
        predictions['PE'] = [pe_match.group(1), pe_match.group(2), pe_match.group(3)]
    
    # 提取目标价
    target_price_match = re.search(r'目标价.*?([\d\.]+)', text)
    if target_price_match:
        predictions['目标价'] = target_price_match.group(1)
    
    # 提取营收预测
    revenue_match = re.search(r'营收.*?([\d\.]+).*?亿', text)
    if revenue_match:
        predictions['营收'] = revenue_match.group(1) + '亿'
    
    return predictions

def extract_risks(text):
    """提取风险提示"""
    risks = []
    
    # 匹配风险提示部分
    pattern = r'风险提示[：:]?(.*?)(?=投资建议|盈利预测|$)'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        content = match.group(1).strip()
        # 分割风险点
        risk_points = re.split(r'[◼➢•●]|[\d]+[、\.]', content)
        for risk in risk_points:
            risk = risk.strip()
            risk = re.sub(r'\s+', ' ', risk)
            if len(risk) > 10 and len(risk) < 100:
                risks.append(risk)
    
    return risks[:3]  # 返回最多3个风险

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
    
    message = f"📊 **{yesterday} 券商研报观点汇总**\n\n"
    message += f"*数据来源：东方财富 | 共 {len(reports)} 篇研报*\n"
    message += "*已使用AI提取核心要点、盈利预测和风险提示*\n"
    message += "---\n\n"
    
    categories = categorize_reports(reports)
    
    # 个股研报（处理前5篇）
    if categories["个股研报"]:
        message += "## 📈 个股研报深度分析\n\n"
        
        for i, r in enumerate(categories["个股研报"][:5], 1):
            stock = r.get('stockName', '')
            code = r.get('stockCode', '')
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            rating = r.get('emRatingName', '')
            industry = r.get('indvInduName', '')
            info_code = r.get('infoCode', '')
            encode_url = r.get('encodeUrl', '')
            
            message += f"### {i}. {stock}（{code}）| {broker}"
            if rating:
                message += f" | {rating}"
            message += "\n\n"
            
            if industry:
                message += f"🏭 **行业**：{industry}\n\n"
            
            # 获取并分析PDF
            print(f"正在AI分析 {stock} 的研报...")
            text, pdf_url = fetch_report_content(info_code, encode_url)
            summary, predictions, risks = ai_summarize(text, stock, broker)
            
            # 核心投资逻辑
            if summary:
                message += "💡 **核心投资逻辑**：\n\n"
                for point in summary:
                    message += f"• {point}\n"
                message += "\n"
            
            # 盈利预测
            if predictions:
                message += "📊 **关键数据**：\n"
                if 'EPS' in predictions:
                    message += f"• EPS预测：{' / '.join(predictions['EPS'])} 元\n"
                if 'PE' in predictions:
                    message += f"• PE估值：{' / '.join(predictions['PE'])} 倍\n"
                if '目标价' in predictions:
                    message += f"• 目标价：{predictions['目标价']} 元\n"
                if '营收' in predictions:
                    message += f"• 营收预测：{predictions['营收']}\n"
                message += "\n"
            
            # 风险提示
            if risks:
                message += "⚠️ **风险提示**：\n"
                for risk in risks:
                    message += f"• {risk}\n"
                message += "\n"
            
            # PDF链接
            if pdf_url:
                message += f"📄 [点击下载PDF原文]({pdf_url})\n"
            message += "\n---\n\n"
    
    # 行业研究（简化）
    if categories["行业研究"]:
        message += "## 🏭 行业研究精选\n\n"
        for i, r in enumerate(categories["行业研究"][:3], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            industry = r.get('indvInduName', '')
            
            core_view = title.split('：')[-1] if '：' in title else title
            message += f"**{i}. {industry or '行业研究'} | {broker}**\n"
            message += f"💡 {core_view}\n\n"
    
    # 宏观策略
    if categories["宏观策略"]:
        message += "## 🌍 宏观策略观点\n\n"
        for i, r in enumerate(categories["宏观策略"][:2], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            
            core_view = title.split('：')[-1] if '：' in title else title
            message += f"**{i}. {broker}**：{core_view}\n\n"
    
    message += "---\n"
    message += "⏰ *每天早上7:38自动推送*\n"
    message += "🤖 *AI智能摘要 | 数据来源：东方财富*\n"
    message += "💡 *投资有风险，研报观点仅供参考*"
    
    return message

if __name__ == "__main__":
    msg = format_report_message()
    print(msg)
