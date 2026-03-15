#!/usr/bin/env python3
"""
机票价格爬虫 - 使用 Playwright (更快更稳定)
爬取去哪儿/携程真实价格
"""

import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

class FlightCrawlerPlaywright:
    def __init__(self):
        self.browser = None
        self.context = None
        
    async def init(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
    
    async def search_qunar(self, from_city, to_city, date):
        """
        爬取去哪儿机票
        """
        try:
            page = await self.context.new_page()
            
            # 构建搜索URL
            url = f"https://flight.qunar.com/site/oneway_list.htm?searchDepartureAirport={from_city}&searchArrivalAirport={to_city}&searchDepartureTime={date}&startSearch=true"
            
            print(f"🌐 正在访问: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待航班列表加载
            try:
                await page.wait_for_selector('.b-airfly', timeout=15000)
            except:
                print("⚠️ 等待航班列表超时，检查是否有验证码或反爬")
                # 截图查看页面状态
                await page.screenshot(path='qunar_error.png')
                await page.close()
                return {'success': False, 'error': '页面加载超时或需要验证码'}
            
            # 提取航班数据
            flights = await page.evaluate('''() => {
                const items = document.querySelectorAll('.b-airfly');
                const data = [];
                items.forEach(item => {
                    try {
                        const airline = item.querySelector('.airline-name')?.textContent?.trim() || '';
                        const flightNo = item.querySelector('.airline-num')?.textContent?.trim() || '';
                        const depTime = item.querySelector('.air-fly-depart-time')?.textContent?.trim() || '';
                        const arrTime = item.querySelector('.air-fly-arrive-time')?.textContent?.trim() || '';
                        const depAirport = item.querySelector('.air-port-depart')?.textContent?.trim() || '';
                        const arrAirport = item.querySelector('.air-port-arrive')?.textContent?.trim() || '';
                        const priceText = item.querySelector('.prc')?.textContent?.trim() || '0';
                        const price = parseInt(priceText.replace(/[^\d]/g, '')) || 0;
                        
                        if (airline && price > 0) {
                            data.push({airline, flightNo, depTime, arrTime, depAirport, arrAirport, price});
                        }
                    } catch(e) {}
                });
                return data;
            }''')
            
            await page.close()
            
            # 排序并返回
            flights.sort(key=lambda x: x['price'])
            
            return {
                'success': len(flights) > 0,
                'platform': '去哪儿',
                'count': len(flights),
                'flights': flights[:10],
                'lowest_price': flights[0]['price'] if flights else None,
                'search_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'platform': '去哪儿'}
    
    async def search_ctrip(self, from_city, to_city, date):
        """
        爬取携程机票 - 使用移动端页面（更简单）
        """
        try:
            page = await self.context.new_page()
            
            # 使用携程H5页面（反爬较弱）
            url = f"https://m.ctrip.com/html5/flight/swift/index?depcity={from_city}&arrcity={to_city}&depdate={date}"
            
            print(f"🌐 正在访问携程: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待加载
            await asyncio.sleep(3)
            
            # 提取数据
            flights = await page.evaluate('''() => {
                const items = document.querySelectorAll('.flight-item, .flight-list-item');
                const data = [];
                items.forEach(item => {
                    try {
                        const airline = item.querySelector('.airline-name, .flight-name')?.textContent?.trim() || '';
                        const priceText = item.querySelector('.price, .flight-price')?.textContent?.trim() || '0';
                        const price = parseInt(priceText.replace(/[^\d]/g, '')) || 0;
                        
                        if (airline && price > 0) {
                            data.push({airline, price, source: '携程'});
                        }
                    } catch(e) {}
                });
                return data;
            }''')
            
            await page.close()
            
            return {
                'success': len(flights) > 0,
                'platform': '携程',
                'count': len(flights),
                'flights': flights[:10],
                'lowest_price': flights[0]['price'] if flights else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'platform': '携程'}
    
    async def search_both(self, from_city, to_city, date):
        """
        同时爬取两个平台
        """
        print(f"\n🔍 开始爬取 {from_city} -> {to_city} {date}")
        print("=" * 60)
        
        # 爬取去哪儿
        qunar = await self.search_qunar(from_city, to_city, date)
        
        # 延迟一下
        await asyncio.sleep(2)
        
        # 爬取携程
        ctrip = await self.search_ctrip(from_city, to_city, date)
        
        # 合并结果
        all_flights = []
        if qunar.get('success'): 
            all_flights.extend(qunar['flights'])
            print(f"✅ 去哪儿: {qunar['count']} 个航班，最低 ¥{qunar['lowest_price']}")
        else:
            print(f"❌ 去哪儿: {qunar.get('error', '失败')}")
        
        if ctrip.get('success'):
            all_flights.extend(ctrip['flights'])
            print(f"✅ 携程: {ctrip['count']} 个航班，最低 ¥{ctrip['lowest_price']}")
        else:
            print(f"❌ 携程: {ctrip.get('error', '失败')}")
        
        all_flights.sort(key=lambda x: x['price'])
        
        return {
            'success': len(all_flights) > 0,
            'from': from_city,
            'to': to_city,
            'date': date,
            'count': len(all_flights),
            'flights': all_flights[:15],
            'lowest_price': all_flights[0]['price'] if all_flights else None,
            'search_time': datetime.now().isoformat()
        }
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def main():
    print("=" * 60)
    print("🛫 机票价格爬虫 - Playwright 版本")
    print("=" * 60)
    
    crawler = FlightCrawlerPlaywright()
    await crawler.init()
    
    try:
        # 交互式查询
        from_city = input("\n出发城市: ").strip() or "北京"
        to_city = input("到达城市: ").strip() or "上海"
        date = input("日期 (如 2025-04-01): ").strip() or "2025-04-01"
        
        result = await crawler.search_both(from_city, to_city, date)
        
        if result['success']:
            print(f"\n✅ 共找到 {result['count']} 个航班")
            print(f"💰 最低价格: ¥{result['lowest_price']}")
            print("\n前10个航班:")
            print("-" * 80)
            
            for i, flight in enumerate(result['flights'][:10], 1):
                print(f"{i}. {flight['airline']}")
                if 'flightNo' in flight:
                    print(f"   航班号: {flight['flightNo']}")
                if 'depTime' in flight:
                    print(f"   时间: {flight['depTime']} - {flight['arrTime']}")
                print(f"   价格: ¥{flight['price']}")
                print()
        else:
            print("❌ 未找到航班数据")
            print("可能原因：")
            print("  1. 网站反爬机制（需要验证码）")
            print("  2. 该日期无航班")
            print("  3. 网络连接问题")
            
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())
