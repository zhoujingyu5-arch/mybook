#!/usr/bin/env python3
"""
机票价格爬虫 - 低频稳定版
降低频率，避免反爬，支持代理
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

class FlightCrawlerStable:
    def __init__(self):
        self.browser = None
        self.context = None
        self.last_request_time = 0
        self.min_interval = 15  # 最小请求间隔15秒
        self.max_retries = 3    # 最大重试次数
        
    async def init(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        # 启动参数 - 更像真实用户
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        # 创建上下文 - 模拟真实用户
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )
        
        # 添加脚本隐藏 webdriver 特征
        await self.context.add_init_script('''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        ''')
    
    async def _rate_limit(self):
        """速率限制 - 确保请求间隔"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed + random.uniform(1, 5)
            print(f"⏱️  等待 {wait_time:.1f} 秒...")
            await asyncio.sleep(wait_time)
        self.last_request_time = time.time()
    
    async def search_qunar_with_retry(self, from_city, to_city, date, retry=0):
        """
        带重试的去哪儿搜索
        """
        try:
            await self._rate_limit()
            
            page = await self.context.new_page()
            
            # 随机化窗口大小
            width = random.randint(1200, 1920)
            height = random.randint(700, 1080)
            await page.set_viewport_size({'width': width, 'height': height})
            
            # 构建URL
            url = f"https://flight.qunar.com/site/oneway_list.htm"
            params = f"?searchDepartureAirport={from_city}&searchArrivalAirport={to_city}&searchDepartureTime={date}&startSearch=true"
            
            print(f"🌐 [{retry+1}/{self.max_retries}] 正在访问去哪儿...")
            
            # 先访问首页
            await page.goto("https://flight.qunar.com", wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # 再访问搜索结果页
            await page.goto(url + params, wait_until='networkidle', timeout=30000)
            
            # 等待页面加载 - 随机等待时间
            wait_time = random.uniform(5, 10)
            print(f"⏳ 等待页面加载 {wait_time:.1f} 秒...")
            await asyncio.sleep(wait_time)
            
            # 检查是否有验证码
            captcha = await page.query_selector('.captcha, .verify-code, #captcha')
            if captcha:
                print("⚠️  检测到验证码，保存截图...")
                await page.screenshot(path=f'captcha_{int(time.time())}.png')
                await page.close()
                if retry < self.max_retries - 1:
                    print(f"🔄 等待后重试...")
                    await asyncio.sleep(random.uniform(30, 60))  # 等待更长时间
                    return await self.search_qunar_with_retry(from_city, to_city, date, retry + 1)
                return {'success': False, 'error': '需要验证码，已达到最大重试次数'}
            
            # 等待航班列表
            try:
                await page.wait_for_selector('.b-airfly', timeout=10000)
            except:
                # 检查页面内容
                content = await page.content()
                if '验证码' in content or 'verify' in content.lower():
                    await page.screenshot(path=f'verify_{int(time.time())}.png')
                    await page.close()
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(random.uniform(30, 60))
                        return await self.search_qunar_with_retry(from_city, to_city, date, retry + 1)
                    return {'success': False, 'error': '页面需要验证'}
                
                print("⚠️  未找到航班列表，尝试解析页面...")
            
            # 提取航班数据
            flights = await page.evaluate('''() => {
                const items = document.querySelectorAll('.b-airfly');
                const data = [];
                items.forEach((item, index) => {
                    if (index > 10) return; // 只取前10个
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
            
            if not flights and retry < self.max_retries - 1:
                print(f"🔄 未获取到数据，等待后重试...")
                await asyncio.sleep(random.uniform(20, 40))
                return await self.search_qunar_with_retry(from_city, to_city, date, retry + 1)
            
            flights.sort(key=lambda x: x['price'])
            
            return {
                'success': len(flights) > 0,
                'platform': '去哪儿',
                'count': len(flights),
                'flights': flights,
                'lowest_price': flights[0]['price'] if flights else None,
                'search_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            if retry < self.max_retries - 1:
                await asyncio.sleep(random.uniform(10, 20))
                return await self.search_qunar_with_retry(from_city, to_city, date, retry + 1)
            return {'success': False, 'error': str(e), 'platform': '去哪儿'}
    
    async def search_ctrip_mobile(self, from_city, to_city, date, retry=0):
        """
        爬取携程H5页面（反爬较弱）
        """
        try:
            await self._rate_limit()
            
            page = await self.context.new_page()
            
            # 设置移动端UA
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
            })
            
            # 携程H5搜索页
            url = f"https://m.ctrip.com/html5/flight/swift/index"
            
            print(f"🌐 [{retry+1}/{self.max_retries}] 正在访问携程H5...")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(random.uniform(3, 5))
            
            # 填写表单
            await page.fill('input[placeholder*="出发"]', from_city)
            await asyncio.sleep(random.uniform(0.5, 1))
            await page.fill('input[placeholder*="到达"]', to_city)
            await asyncio.sleep(random.uniform(0.5, 1))
            
            # 点击搜索
            await page.click('.search-btn, .btn-search')
            await asyncio.sleep(random.uniform(5, 8))
            
            # 提取数据
            flights = await page.evaluate('''() => {
                const items = document.querySelectorAll('.flight-item');
                const data = [];
                items.forEach((item, index) => {
                    if (index > 8) return;
                    try {
                        const airline = item.querySelector('.airline')?.textContent?.trim() || '';
                        const priceText = item.querySelector('.price')?.textContent?.trim() || '0';
                        const price = parseInt(priceText.replace(/[^\d]/g, '')) || 0;
                        if (airline && price > 0) {
                            data.push({airline, price});
                        }
                    } catch(e) {}
                });
                return data;
            }''')
            
            await page.close()
            
            return {
                'success': len(flights) > 0,
                'platform': '携程H5',
                'count': len(flights),
                'flights': flights,
                'lowest_price': flights[0]['price'] if flights else None
            }
            
        except Exception as e:
            if retry < self.max_retries - 1:
                await asyncio.sleep(random.uniform(10, 20))
                return await self.search_ctrip_mobile(from_city, to_city, date, retry + 1)
            return {'success': False, 'error': str(e), 'platform': '携程'}
    
    async def search(self, from_city, to_city, date, platforms=None):
        """
        搜索机票 - 可指定平台
        """
        if platforms is None:
            platforms = ['qunar']
        
        print(f"\n🔍 开始搜索 {from_city} -> {to_city} {date}")
        print(f"📋 搜索平台: {', '.join(platforms)}")
        print("=" * 60)
        
        all_results = []
        
        if 'qunar' in platforms:
            result = await self.search_qunar_with_retry(from_city, to_city, date)
            if result.get('success'):
                all_results.append(result)
                print(f"✅ 去哪儿: {result['count']} 个航班，最低 ¥{result['lowest_price']}")
            else:
                print(f"❌ 去哪儿: {result.get('error', '失败')}")
        
        if 'ctrip' in platforms:
            result = await self.search_ctrip_mobile(from_city, to_city, date)
            if result.get('success'):
                all_results.append(result)
                print(f"✅ 携程: {result['count']} 个航班，最低 ¥{result['lowest_price']}")
            else:
                print(f"❌ 携程: {result.get('error', '失败')}")
        
        # 合并所有结果
        all_flights = []
        for r in all_results:
            all_flights.extend(r.get('flights', []))
        
        all_flights.sort(key=lambda x: x['price'])
        
        return {
            'success': len(all_flights) > 0,
            'from': from_city,
            'to': to_city,
            'date': date,
            'count': len(all_flights),
            'flights': all_flights[:15],
            'lowest_price': all_flights[0]['price'] if all_flights else None,
            'search_time': datetime.now().isoformat(),
            'sources': [r['platform'] for r in all_results]
        }
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def main():
    print("=" * 60)
    print("🛫 机票价格爬虫 - 低频稳定版")
    print("=" * 60)
    print("\n⚙️  配置:")
    print("  - 请求间隔: 15秒+")
    print("  - 最大重试: 3次")
    print("  - 随机延迟: 启用")
    print("  - 反爬隐藏: 启用")
    
    crawler = FlightCrawlerStable()
    await crawler.init()
    
    try:
        # 交互式查询
        from_city = input("\n出发城市: ").strip() or "北京"
        to_city = input("到达城市: ").strip() or "上海"
        date = input("日期 (如 2025-04-01): ").strip() or "2025-04-01"
        
        # 只搜索去哪儿（更稳定）
        result = await crawler.search(from_city, to_city, date, platforms=['qunar'])
        
        if result['success']:
            print(f"\n✅ 共找到 {result['count']} 个航班")
            print(f"💰 最低价格: ¥{result['lowest_price']}")
            print(f"📊 数据来源: {', '.join(result['sources'])}")
            print("\n前10个航班:")
            print("-" * 80)
            
            for i, flight in enumerate(result['flights'][:10], 1):
                print(f"{i}. {flight['airline']} {flight.get('flightNo', '')}")
                if 'depTime' in flight:
                    print(f"   时间: {flight['depTime']} - {flight['arrTime']}")
                    print(f"   机场: {flight['depAirport']} → {flight['arrAirport']}")
                print(f"   价格: ¥{flight['price']}")
                print()
        else:
            print("\n❌ 未找到航班数据")
            print("\n可能原因：")
            print("  1. 网站反爬机制（出现验证码）")
            print("  2. 该日期无航班或已售罄")
            print("  3. 网络连接问题")
            print("\n建议：")
            print("  - 等待几分钟后重试")
            print("  - 更换搜索日期")
            print("  - 使用代理IP")
            
    finally:
        await crawler.close()
        print("\n✅ 爬虫已关闭")


if __name__ == "__main__":
    asyncio.run(main())
