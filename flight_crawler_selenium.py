#!/usr/bin/env python3
"""
机票价格爬虫 - 去哪儿/携程
使用 Selenium + BeautifulSoup 爬取真实价格
"""

import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import random

class FlightCrawler:
    def __init__(self):
        self.driver = None
        self.setup_driver()
        
    def setup_driver(self):
        """初始化浏览器"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        # 禁用图片加载
        chrome_options.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 2
        })
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
        except Exception as e:
            print(f"浏览器初始化失败: {e}")
            print("请确保已安装 Chrome 和 ChromeDriver")
            raise
    
    def search_qunar(self, from_city, to_city, date):
        """
        爬取去哪儿机票
        """
        try:
            # 构建URL
            url = f"https://flight.qunar.com/site/oneway_list.htm"
            params = f"?searchDepartureAirport={from_city}&searchArrivalAirport={to_city}&searchDepartureTime={date}&searchArrivalTime=&nextNDays=0&startSearch=true&fromCode=&toCode=&from=qunarindex&lowestPrice=null"
            full_url = url + params
            
            print(f"正在爬取去哪儿: {from_city} -> {to_city} {date}")
            self.driver.get(full_url)
            
            # 等待页面加载
            time.sleep(3)
            
            # 等待航班列表出现
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "b-airfly"))
                )
            except:
                print("等待超时，尝试解析当前页面")
            
            # 获取页面源码
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            flights = []
            
            # 解析航班列表
            flight_items = soup.find_all('div', class_='b-airfly')
            
            for item in flight_items[:10]:  # 只取前10个
                try:
                    # 航司名称
                    airline_elem = item.find('div', class_='airline-name')
                    airline = airline_elem.text.strip() if airline_elem else ''
                    
                    # 航班号
                    flight_no_elem = item.find('div', class_='airline-num')
                    flight_no = flight_no_elem.text.strip() if flight_no_elem else ''
                    
                    # 出发时间
                    dep_time_elem = item.find('div', class_='air-fly-depart-time')
                    dep_time = dep_time_elem.text.strip() if dep_time_elem else ''
                    
                    # 到达时间
                    arr_time_elem = item.find('div', class_='air-fly-arrive-time')
                    arr_time = arr_time_elem.text.strip() if arr_time_elem else ''
                    
                    # 出发机场
                    dep_airport_elem = item.find('div', class_='air-port-depart')
                    dep_airport = dep_airport_elem.text.strip() if dep_airport_elem else ''
                    
                    # 到达机场
                    arr_airport_elem = item.find('div', class_='air-port-arrive')
                    arr_airport = arr_airport_elem.text.strip() if arr_airport_elem else ''
                    
                    # 价格
                    price_elem = item.find('span', class_='prc')
                    if price_elem:
                        price_text = price_elem.text.strip()
                        price = int(re.findall(r'\d+', price_text)[0]) if re.findall(r'\d+', price_text) else 0
                    else:
                        price = 0
                    
                    if airline and price > 0:
                        flights.append({
                            'airline': airline,
                            'flight_no': flight_no,
                            'dep_time': dep_time,
                            'arr_time': arr_time,
                            'dep_airport': dep_airport,
                            'arr_airport': arr_airport,
                            'price': price,
                            'source': '去哪儿'
                        })
                        
                except Exception as e:
                    continue
            
            flights.sort(key=lambda x: x['price'])
            
            return {
                'success': True,
                'platform': '去哪儿',
                'count': len(flights),
                'flights': flights,
                'lowest_price': flights[0]['price'] if flights else None,
                'search_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'platform': '去哪儿'
            }
    
    def search_ctrip_selenium(self, from_city, to_city, date):
        """
        使用Selenium爬取携程机票
        """
        try:
            # 构建URL
            url = f"https://flights.ctrip.com/online/channel/domestic"
            
            print(f"正在爬取携程: {from_city} -> {to_city} {date}")
            self.driver.get(url)
            
            time.sleep(2)
            
            # 填写出发城市
            from_input = self.driver.find_element(By.ID, "DCityName1")
            from_input.clear()
            from_input.send_keys(from_city)
            time.sleep(0.5)
            
            # 填写到达城市
            to_input = self.driver.find_element(By.ID, "ACityName1")
            to_input.clear()
            to_input.send_keys(to_city)
            time.sleep(0.5)
            
            # 填写日期
            date_input = self.driver.find_element(By.ID, "DDate1")
            self.driver.execute_script(f"arguments[0].value = '{date}';", date_input)
            
            # 点击搜索
            search_btn = self.driver.find_element(By.ID, "btnSearch")
            search_btn.click()
            
            # 等待结果加载
            time.sleep(5)
            
            # 解析结果
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            flights = []
            flight_items = soup.find_all('div', class_='flight-item')
            
            for item in flight_items[:10]:
                try:
                    airline = item.find('div', class_='airline-name').text.strip()
                    flight_no = item.find('div', class_='flight-no').text.strip()
                    
                    dep_time = item.find('div', class_='dep-time').text.strip()
                    arr_time = item.find('div', class_='arr-time').text.strip()
                    
                    price_text = item.find('span', class_='price').text.strip()
                    price = int(re.findall(r'\d+', price_text)[0])
                    
                    flights.append({
                        'airline': airline,
                        'flight_no': flight_no,
                        'dep_time': dep_time,
                        'arr_time': arr_time,
                        'price': price,
                        'source': '携程'
                    })
                except:
                    continue
            
            flights.sort(key=lambda x: x['price'])
            
            return {
                'success': True,
                'platform': '携程',
                'count': len(flights),
                'flights': flights,
                'lowest_price': flights[0]['price'] if flights else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'platform': '携程'
            }
    
    def search_both(self, from_city, to_city, date):
        """
        同时爬取去哪儿和携程
        """
        print(f"\n🔍 开始爬取 {from_city} -> {to_city} {date} 的真实价格...")
        
        # 爬取去哪儿
        qunar_result = self.search_qunar(from_city, to_city, date)
        
        # 随机延迟，避免被封
        time.sleep(random.uniform(2, 4))
        
        # 爬取携程
        ctrip_result = self.search_ctrip_selenium(from_city, to_city, date)
        
        # 合并结果
        all_flights = []
        
        if qunar_result.get('success') and qunar_result.get('flights'):
            all_flights.extend(qunar_result['flights'])
            print(f"✅ 去哪儿: {qunar_result['count']} 个航班，最低 ¥{qunar_result['lowest_price']}")
        else:
            print(f"❌ 去哪儿: {qunar_result.get('error', '无数据')}")
        
        if ctrip_result.get('success') and ctrip_result.get('flights'):
            all_flights.extend(ctrip_result['flights'])
            print(f"✅ 携程: {ctrip_result['count']} 个航班，最低 ¥{ctrip_result['lowest_price']}")
        else:
            print(f"❌ 携程: {ctrip_result.get('error', '无数据')}")
        
        # 按价格排序
        all_flights.sort(key=lambda x: x['price'])
        
        return {
            'success': len(all_flights) > 0,
            'from': from_city,
            'to': to_city,
            'date': date,
            'count': len(all_flights),
            'flights': all_flights[:15],  # 返回前15个
            'lowest_price': all_flights[0]['price'] if all_flights else None,
            'search_time': datetime.now().isoformat(),
            'sources': ['去哪儿' if qunar_result.get('success') else None, 
                       '携程' if ctrip_result.get('success') else None]
        }
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()


def main():
    print("=" * 60)
    print("🛫 机票价格爬虫 - 去哪儿/携程")
    print("=" * 60)
    
    crawler = FlightCrawler()
    
    try:
        # 测试查询
        from_city = input("\n出发城市: ").strip()
        to_city = input("到达城市: ").strip()
        date = input("日期 (如 2025-04-01): ").strip()
        
        result = crawler.search_both(from_city, to_city, date)
        
        if result['success']:
            print(f"\n✅ 共找到 {result['count']} 个航班")
            print(f"💰 最低价格: ¥{result['lowest_price']}")
            print("\n前10个航班:")
            print("-" * 80)
            
            for i, flight in enumerate(result['flights'][:10], 1):
                print(f"{i}. {flight['airline']} {flight['flight_no']}")
                print(f"   时间: {flight['dep_time']} - {flight['arr_time']}")
                print(f"   价格: ¥{flight['price']} [{flight['source']}]")
                print()
        else:
            print("❌ 未找到航班数据")
            
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
