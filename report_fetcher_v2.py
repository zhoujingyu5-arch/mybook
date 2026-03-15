#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta
import base64

def fetch_reports():
    """从东方财富获取研报"""
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
        print(f"获取研报失败: {e}")
        return []

def get_report_url(report):
    """获取研报查看链接"""
    info_code = report.get('infoCode', '')
    encode_url = report.get('encodeUrl', '')
    
    # 方式1: 东方财富研报详情页
    detail_url = f"https://data.eastmoney.com/report/stock.jshtml?infocode={info_code}"
    
    # 方式2: 直接PDF链接（需要解码encodeUrl）
    # PDF链接格式: https://pdf.dfcfw.com/pdf/H2_{encodeUrl}_1.pdf
    if encode_url:
        pdf_url = f"https://pdf.dfcfw.com/pdf/H2_{encode_url}_1.pdf"
    else:
        pdf_url = None
    
    return detail_url, pdf_url

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
    message += "---\n\n"
    
    categories = categorize_reports(reports)
    
    # 个股研报
    if categories["个股研报"]:
        message += "### 📈 个股研报核心观点\n\n"
        for i, r in enumerate(categories["个股研报"][:8], 1):  # 最多8篇
            stock = r.get('stockName', '')
            code = r.get('stockCode', '')
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            rating = r.get('emRatingName', '')
            
            # 提取核心观点（从标题中提取）
            core_view = title.split('：')[-1] if '：' in title else title
            
            detail_url, pdf_url = get_report_url(r)
            
            message += f"**{i}. {stock}（{code}）| {broker}"
            if rating:
                message += f" | {rating}"
            message += "**\n\n"
            
            message += f"💡 {core_view}\n\n"
            
            # 提供两种链接
            message += f"📄 [研报详情]({detail_url})"
            if pdf_url:
                message += f" | [PDF下载]({pdf_url})"
            message += "\n\n"
    
    # 行业研究
    if categories["行业研究"]:
        message += "### 🏭 行业研究核心观点\n\n"
        for i, r in enumerate(categories["行业研究"][:5], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            industry = r.get('indvInduName', '')
            
            core_view = title.split('：')[-1] if '：' in title else title
            
            detail_url, pdf_url = get_report_url(r)
            
            message += f"**{i}. {industry or '行业研究'} | {broker}**\n\n"
            message += f"💡 {core_view}\n\n"
            message += f"📄 [研报详情]({detail_url})"
            if pdf_url:
                message += f" | [PDF下载]({pdf_url})"
            message += "\n\n"
    
    # 宏观策略
    if categories["宏观策略"]:
        message += "### 🌍 宏观策略核心观点\n\n"
        for i, r in enumerate(categories["宏观策略"][:3], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            
            core_view = title.split('：')[-1] if '：' in title else title
            
            detail_url, pdf_url = get_report_url(r)
            
            message += f"**{i}. {broker}**\n\n"
            message += f"💡 {core_view}\n\n"
            message += f"📄 [研报详情]({detail_url})"
            if pdf_url:
                message += f" | [PDF下载]({pdf_url})"
            message += "\n\n"
    
    message += "---\n"
    message += "💬 *点击链接查看研报原文（PDF链接可直接下载）*\n"
    message += "⏰ *每天早上7:38自动推送*\n"
    message += "📊 *数据来源：东方财富研报中心*"
    
    return message

if __name__ == "__main__":
    msg = format_report_message()
    print(msg)
