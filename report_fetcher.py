#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta

def fetch_reports():
    """从东方财富获取研报"""
    url = "https://reportapi.eastmoney.com/report/list"
    
    # 获取昨天的日期
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
        # 根据标题关键词分类
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
        message += "## 📈 个股研报\n\n"
        for r in categories["个股研报"][:10]:  # 最多10篇
            stock = r.get('stockName', '')
            code = r.get('stockCode', '')
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            rating = r.get('emRatingName', '')
            industry = r.get('indvInduName', '')
            
            # 构建研报链接
            info_code = r.get('infoCode', '')
            report_url = f"https://data.eastmoney.com/report/stock.jshtml?infocode={info_code}"
            
            message += f"**{stock}** ({code}) | {broker} | {rating}\n"
            message += f"{title}\n"
            if industry:
                message += f"行业：{industry}\n"
            message += f"🔗 [查看研报]({report_url})\n\n"
    
    # 行业研究
    if categories["行业研究"]:
        message += "## 🏭 行业研究\n\n"
        for r in categories["行业研究"][:5]:
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            industry = r.get('indvInduName', '')
            info_code = r.get('infoCode', '')
            report_url = f"https://data.eastmoney.com/report/industry.jshtml?infocode={info_code}"
            
            message += f"• **{broker}**：{title}\n"
            if industry:
                message += f"  行业：{industry}\n"
            message += f"  🔗 [查看研报]({report_url})\n\n"
    
    # 宏观策略
    if categories["宏观策略"]:
        message += "## 🌍 宏观策略\n\n"
        for r in categories["宏观策略"][:3]:
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            info_code = r.get('infoCode', '')
            report_url = f"https://data.eastmoney.com/report/stock.jshtml?infocode={info_code}"
            
            message += f"• **{broker}**：{title}\n"
            message += f"  🔗 [查看研报]({report_url})\n\n"
    
    message += "---\n"
    message += "💬 *点击链接可查看完整研报原文*\n"
    message += "⏰ *每天早上7:38自动推送*\n"
    message += "📊 *数据来源：东方财富研报中心*"
    
    return message

if __name__ == "__main__":
    msg = format_report_message()
    print(msg)
