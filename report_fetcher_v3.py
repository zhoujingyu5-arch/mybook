#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta

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

def get_search_url(report):
    """生成搜索链接（最可靠的方式）"""
    title = report.get('title', '')
    stock = report.get('stockName', '')
    broker = report.get('orgSName', '')
    
    # 使用百度或谷歌搜索研报标题+券商
    search_query = f"{title} {broker} site:pdf.dfcfw.com OR site:eastmoney.com"
    baidu_url = f"https://www.baidu.com/s?wd={requests.utils.quote(search_query)}"
    
    return baidu_url

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
        for i, r in enumerate(categories["个股研报"][:8], 1):
            stock = r.get('stockName', '')
            code = r.get('stockCode', '')
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            rating = r.get('emRatingName', '')
            industry = r.get('indvInduName', '')
            
            # 提取核心观点
            core_view = title.split('：')[-1] if '：' in title else title
            
            # 东方财富研报列表页面
            list_url = f"https://data.eastmoney.com/report/stock.jshtml"
            
            message += f"**{i}. {stock}（{code}）| {broker}"
            if rating:
                message += f" | {rating}"
            message += "**\n\n"
            
            message += f"💡 {core_view}\n"
            if industry:
                message += f"🏭 行业：{industry}\n"
            
            # 提供验证方式
            message += f"\n🔍 验证方式：\n"
            message += f"  1. 东方财富APP → 搜索\"{stock}\" → 研报\n"
            message += f"  2. 券商：{broker}\n"
            message += f"  3. 标题：{title[:30]}...\n\n"
    
    # 行业研究
    if categories["行业研究"]:
        message += "### 🏭 行业研究核心观点\n\n"
        for i, r in enumerate(categories["行业研究"][:5], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            industry = r.get('indvInduName', '')
            
            core_view = title.split('：')[-1] if '：' in title else title
            
            message += f"**{i}. {industry or '行业研究'} | {broker}**\n\n"
            message += f"💡 {core_view}\n\n"
            message += f"🔍 验证：东方财富APP → 行业研报 → {broker}\n\n"
    
    # 宏观策略
    if categories["宏观策略"]:
        message += "### 🌍 宏观策略核心观点\n\n"
        for i, r in enumerate(categories["宏观策略"][:3], 1):
            title = r.get('title', '')
            broker = r.get('orgSName', '')
            
            core_view = title.split('：')[-1] if '：' in title else title
            
            message += f"**{i}. {broker}**\n\n"
            message += f"💡 {core_view}\n\n"
            message += f"🔍 验证：东方财富APP → 搜索\"{broker}\" → 研报\n\n"
    
    message += "---\n"
    message += "📱 *验证方法：下载东方财富APP，搜索股票名称或券商名称，进入\"研报\"栏目查看*\n"
    message += "⏰ *每天早上7:38自动推送*\n"
    message += "📊 *数据来源：东方财富研报中心*"
    
    return message

if __name__ == "__main__":
    msg = format_report_message()
    print(msg)
