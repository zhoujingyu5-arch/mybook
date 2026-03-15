#!/usr/bin/env python3
import requests
import json
import pdfplumber
import os
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
        "pageSize": 20,  # 限制数量避免太慢
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
    # 1. 获取研报元数据
    meta_url = "https://reportapi.eastmoney.com/report/content"
    params = {
        "infoCode": info_code,
        "encodeUrl": encode_url
    }
    
    try:
        response = requests.get(meta_url, params=params, timeout=10)
        data = response.json()
        report_data = data.get('data', [{}])[0]
        
        # 获取PDF链接
        pdf_url = report_data.get('attachUrl', '')
        
        if pdf_url:
            # 下载PDF
            pdf_response = requests.get(pdf_url, timeout=15)
            if pdf_response.status_code == 200:
                # 提取PDF文本
                text = extract_pdf_summary(pdf_response.content)
                return text, pdf_url
        
        return None, None
    except Exception as e:
        print(f"获取研报内容失败: {e}")
        return None, None

def extract_pdf_summary(pdf_content):
    """从PDF中提取核心摘要"""
    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            full_text = ""
            for page in pdf.pages[:3]:  # 只读前3页
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # 提取核心观点
            summary = extract_key_points(full_text)
            return summary
    except Exception as e:
        print(f"PDF解析失败: {e}")
        return None

def extract_key_points(text):
    """从文本中提取关键信息"""
    if not text:
        return None
    
    key_points = []
    
    # 1. 提取投资要点/核心观点部分
    patterns = [
        r'投资要点[：:]?(.*?)(?=盈利预测|风险提示|$)',
        r'核心观点[：:]?(.*?)(?=盈利预测|风险提示|$)',
        r'事件[：:]?(.*?)(?=点评|分析|$)',
        r'主要观点[：:]?(.*?)(?=盈利预测|风险提示|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # 清理文本
            content = re.sub(r'\s+', ' ', content)
            content = re.sub(r'Table.*?Summary', '', content)
            content = content[:500]  # 限制长度
            if len(content) > 50:
                key_points.append(content)
                break
    
    # 2. 如果没有找到，提取前500字作为摘要
    if not key_points:
        # 去除表格和特殊字符
        clean_text = re.sub(r'[\d\-/]+[\s\w]*', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        key_points.append(clean_text[:400])
    
    return key_points[0] if key_points else None

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
    message += "*正在提取核心摘要，请稍候...*\n"
    message += "---\n\n"
    
    categories = categorize_reports(reports)
    
    # 个股研报（只处理前5篇，避免太慢）
    if categories["个股研报"]:
        message += "### 📈 个股研报核心观点\n\n"
        
        for i, r in enumerate(categories["个股研报"][:5], 1):
            stock = r.get('stockName', '')
            code = r.get('stockCode', '')
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            rating = r.get('emRatingName', '')
            industry = r.get('indvInduName', '')
            info_code = r.get('infoCode', '')
            encode_url = r.get('encodeUrl', '')
            
            message += f"**{i}. {stock}（{code}）| {broker}"
            if rating:
                message += f" | {rating}"
            message += "**\n\n"
            
            # 获取PDF摘要
            print(f"正在提取 {stock} 的研报摘要...")
            summary, pdf_url = fetch_report_content(info_code, encode_url)
            
            if summary:
                # 清理并格式化摘要
                summary = summary.replace('\n', ' ').strip()
                summary = re.sub(r'\s+', ' ', summary)
                message += f"💡 **核心观点**：{summary[:300]}...\n\n"
            else:
                # 使用标题作为备选
                core_view = title.split('：')[-1] if '：' in title else title
                message += f"💡 {core_view}\n\n"
            
            if industry:
                message += f"🏭 行业：{industry}\n"
            
            if pdf_url:
                message += f"📄 [PDF原文]({pdf_url})\n"
            message += "\n"
    
    # 行业研究（简化处理）
    if categories["行业研究"]:
        message += "### 🏭 行业研究\n\n"
        for i, r in enumerate(categories["行业研究"][:3], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            industry = r.get('indvInduName', '')
            
            core_view = title.split('：')[-1] if '：' in title else title
            message += f"**{i}. {industry or '行业研究'} | {broker}**\n"
            message += f"💡 {core_view}\n\n"
    
    message += "---\n"
    message += "⏰ *每天早上7:38自动推送*\n"
    message += "📊 *数据来源：东方财富研报中心*"
    
    return message

if __name__ == "__main__":
    msg = format_report_message()
    print(msg)
