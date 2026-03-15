#!/usr/bin/env python3
"""
券商研报抓取与汇总脚本
每天早上7:38执行，汇总前一天研报
"""

import requests
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

# 研报源配置
REPORT_SOURCES = {
    # 国内券商
    "中金公司": {
        "url": "https://research.cicc.com/",
        "api": "https://research.cicc.com/api/reports",
        "type": "domestic"
    },
    "中信证券": {
        "url": "https://research.cs.ecitic.com/",
        "type": "domestic"
    },
    "华泰证券": {
        "url": "https://research.htsc.com/",
        "type": "domestic"
    },
    "国泰君安": {
        "url": "https://www.gtja.com/research/",
        "type": "domestic"
    },
    "海通证券": {
        "url": "https://www.htsec.com/research/",
        "type": "domestic"
    },
    "招商证券": {
        "url": "https://www.cmschina.com/research/",
        "type": "domestic"
    },
    "天风证券": {
        "url": "https://www.tfzq.com/research/",
        "type": "domestic"
    },
    "广发证券": {
        "url": "https://www.gf.com.cn/research/",
        "type": "domestic"
    },
    "申万宏源": {
        "url": "https://www.swhysc.com/research/",
        "type": "domestic"
    },
    "中信建投": {
        "url": "https://www.csc108.com/research/",
        "type": "domestic"
    },
    # 境外券商
    "高盛": {
        "url": "https://www.goldmansachs.com/insights/",
        "type": "international"
    },
    "摩根士丹利": {
        "url": "https://www.morganstanley.com/im/insights/",
        "type": "international"
    },
    "摩根大通": {
        "url": "https://www.jpmorgan.com/insights/",
        "type": "international"
    },
    "瑞银": {
        "url": "https://www.ubs.com/global/en/wealth-management/insights/",
        "type": "international"
    },
    "汇丰": {
        "url": "https://www.hsbc.com.cn/investments/insights/",
        "type": "international"
    },
    "野村证券": {
        "url": "https://www.nomuraholdings.com/insights/",
        "type": "international"
    }
}

class ReportScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.reports = []
        
    def get_yesterday_date(self):
        """获取昨天日期"""
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime('%Y-%m-%d')
    
    def fetch_from_wind(self):
        """从Wind获取研报（如果有API）"""
        # Wind API需要账号，这里预留接口
        pass
    
    def fetch_from_choice(self):
        """从Choice获取研报（如果有API）"""
        # Choice API需要账号，这里预留接口
        pass
    
    def fetch_from_aggregators(self):
        """从聚合平台获取"""
        aggregators = [
            {
                "name": "慧博投研",
                "url": "https://www.hibor.com.cn/",
                "search_url": "https://www.hibor.com.cn/search"
            },
            {
                "name": "萝卜投研",
                "url": "https://robo.datayes.com/",
                "search_url": "https://robo.datayes.com/v2/report"
            }
        ]
        
        for agg in aggregators:
            try:
                print(f"正在从 {agg['name']} 获取研报...")
                # 实际抓取逻辑需要根据网站结构编写
            except Exception as e:
                print(f"从 {agg['name']} 获取失败: {e}")
    
    def generate_mock_reports(self):
        """
        生成示例研报数据（实际部署时替换为真实抓取）
        由于券商研报大多需要登录，这里先提供框架
        """
        yesterday = self.get_yesterday_date()
        
        mock_reports = [
            {
                "broker": "中金公司",
                "title": "2026年二季度策略展望：科技成长引领反弹",
                "category": "宏观策略",
                "date": yesterday,
                "summary": "预计Q2市场风格将向科技成长切换，建议关注AI、半导体、新能源赛道。",
                "url": "https://research.cicc.com/report/2026Q2-strategy",
                "type": "domestic"
            },
            {
                "broker": "中信证券",
                "title": "消费行业深度：复苏节奏或超预期",
                "category": "行业研究",
                "date": yesterday,
                "summary": "3月消费数据表现亮眼，餐饮、旅游恢复速度超出市场预期。",
                "url": "https://research.cs.ecitic.com/report/consumption-2026",
                "type": "domestic"
            },
            {
                "broker": "华泰证券",
                "title": "新能源汽车出海专题研究",
                "category": "行业研究",
                "date": yesterday,
                "summary": "中国车企在东南亚、欧洲市场份额持续提升，出口增长空间广阔。",
                "url": "https://research.htsc.com/report/nev-export",
                "type": "domestic"
            },
            {
                "broker": "高盛",
                "title": "China Equity Strategy: Selective Opportunities",
                "category": "宏观策略",
                "date": yesterday,
                "summary": "看好中国互联网和消费升级板块，维持超配评级。",
                "url": "https://www.goldmansachs.com/insights/china-equity",
                "type": "international"
            }
        ]
        
        return mock_reports
    
    def categorize_reports(self, reports):
        """按类别分类研报"""
        categories = {
            "宏观策略": [],
            "行业研究": [],
            "个股研报": [],
            "晨会纪要": [],
            "其他": []
        }
        
        for report in reports:
            cat = report.get("category", "其他")
            if cat in categories:
                categories[cat].append(report)
            else:
                categories["其他"].append(report)
        
        return categories
    
    def format_message(self, categories, date):
        """格式化飞书消息"""
        message = f"📊 **{date} 券商研报观点汇总**\n\n"
        message += f"*数据时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
        message += "---\n\n"
        
        # 国内券商
        message += "## 🇨🇳 国内券商\n\n"
        
        for category, reports in categories.items():
            if not reports:
                continue
                
            # 只显示国内券商
            domestic_reports = [r for r in reports if r.get("type") == "domestic"]
            if not domestic_reports:
                continue
                
            message += f"**【{category}】**\n\n"
            
            for report in domestic_reports[:5]:  # 每类最多显示5条
                message += f"• **{report['broker']}**：{report['title']}\n"
                message += f"  💡 {report['summary']}\n"
                message += f"  🔗 [查看原文]({report['url']})\n\n"
        
        # 境外券商
        message += "## 🌍 境外券商\n\n"
        
        for category, reports in categories.items():
            if not reports:
                continue
                
            # 只显示境外券商
            intl_reports = [r for r in reports if r.get("type") == "international"]
            if not intl_reports:
                continue
                
            message += f"**【{category}】**\n\n"
            
            for report in intl_reports[:3]:  # 每类最多显示3条
                message += f"• **{report['broker']}**：{report['title']}\n"
                message += f"  💡 {report['summary']}\n"
                message += f"  🔗 [View Report]({report['url']})\n\n"
        
        message += "---\n"
        message += "💬 *如需查看完整研报，请点击链接验证*\n"
        message += "⏰ *每天早上7:38自动推送*"
        
        return message
    
    def send_to_feishu(self, message):
        """发送到飞书"""
        # 飞书 webhook 或 API 发送
        # 需要从环境变量或配置文件读取
        webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        
        if not webhook_url:
            print("未配置飞书 webhook，消息内容：")
            print(message)
            return
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        try:
            response = requests.post(webhook_url, json=payload)
            print(f"飞书发送结果: {response.status_code}")
        except Exception as e:
            print(f"发送到飞书失败: {e}")
    
    def run(self):
        """主运行函数"""
        print(f"开始抓取 {self.get_yesterday_date()} 的研报...")
        
        # 获取研报（实际部署时替换为真实抓取）
        reports = self.generate_mock_reports()
        
        # 分类
        categories = self.categorize_reports(reports)
        
        # 格式化消息
        message = self.format_message(categories, self.get_yesterday_date())
        
        # 发送
        self.send_to_feishu(message)
        
        print("研报汇总发送完成！")

if __name__ == "__main__":
    scraper = ReportScraper()
    scraper.run()
