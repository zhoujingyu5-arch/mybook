#!/usr/bin/env python3
"""
机票价格监测工具 - 支持多平台比价
使用方法: python3 flight_monitor.py
"""

import requests
import json
import time
import re
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode
import sys

class FlightMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        # 城市代码映射
        self.city_codes = {
            '北京': {'iata': 'PEK', 'ctrip': 'BJS'},
            '上海': {'iata': 'SHA', 'ctrip': 'SHA'},
            '广州': {'iata': 'CAN', 'ctrip': 'CAN'},
            '深圳': {'iata': 'SZX', 'ctrip': 'SZX'},
            '成都': {'iata': 'CTU', 'ctrip': 'CTU'},
            '杭州': {'iata': 'HGH', 'ctrip': 'HGH'},
            '武汉': {'iata': 'WUH', 'ctrip': 'WUH'},
            '西安': {'iata': 'XIY', 'ctrip': 'XIY'},
            '重庆': {'iata': 'CKG', 'ctrip': 'CKG'},
            '青岛': {'iata': 'TAO', 'ctrip': 'TAO'},
            '大连': {'iata': 'DLC', 'ctrip': 'DLC'},
            '厦门': {'iata': 'XMN', 'ctrip': 'XMN'},
            '昆明': {'iata': 'KMG', 'ctrip': 'KMG'},
            '天津': {'iata': 'TSN', 'ctrip': 'TSN'},
            '南京': {'iata': 'NKG', 'ctrip': 'NKG'},
            '长沙': {'iata': 'CSX', 'ctrip': 'CSX'},
            '沈阳': {'iata': 'SHE', 'ctrip': 'SHE'},
            '哈尔滨': {'iata': 'HRB', 'ctrip': 'HRB'},
            '济南': {'iata': 'TNA', 'ctrip': 'TNA'},
            '郑州': {'iata': 'CGO', 'ctrip': 'CGO'},
            '福州': {'iata': 'FOC', 'ctrip': 'FOC'},
            '大阪': {'iata': 'KIX', 'ctrip': 'OSA'},
            '东京': {'iata': 'NRT', 'ctrip': 'TYO'},
            '首尔': {'iata': 'ICN', 'ctrip': 'SEL'},
            '新加坡': {'iata': 'SIN', 'ctrip': 'SIN'},
            '曼谷': {'iata': 'BKK', 'ctrip': 'BKK'},
            '香港': {'iata': 'HKG', 'ctrip': 'HKG'},
            '台北': {'iata': 'TPE', 'ctrip': 'TPE'},
            '伦敦': {'iata': 'LHR', 'ctrip': 'LON'},
            '巴黎': {'iata': 'CDG', 'ctrip': 'PAR'},
            '纽约': {'iata': 'JFK', 'ctrip': 'NYC'},
            '洛杉矶': {'iata': 'LAX', 'ctrip': 'LAX'},
            '旧金山': {'iata': 'SFO', 'ctrip': 'SFO'},
            '悉尼': {'iata': 'SYD', 'ctrip': 'SYD'},
            '墨尔本': {'iata': 'MEL', 'ctrip': 'MEL'},
        }
    
    def get_city_info(self, city_name):
        """获取城市信息"""
        return self.city_codes.get(city_name, None)
    
    def search_ctrip_api(self, from_city, to_city, date):
        """
        使用携程API搜索机票
        """
        try:
            from_info = self.get_city_info(from_city)
            to_info = self.get_city_info(to_city)
            
            if not from_info or not to_info:
                return {"error": f"不支持的城市: {from_city} 或 {to_city}"}
            
            # 携程搜索URL
            url = "https://flights.ctrip.com/itinerary/api/12808/products"
            
            payload = {
                "flightWay": "Oneway",
                "classType": "ALL",
                "hasChild": False,
                "hasBaby": False,
                "searchIndex": 1,
                "airportParams": [{
                    "dcity": from_info['ctrip'],
                    "acity": to_info['ctrip'],
                    "dcityname": from_city,
                    "acityname": to_city,
                    "date": date,
                    "dcityid": 1,
                    "acityid": 1
                }]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Referer': f'https://flights.ctrip.com/itinerary/oneway/{from_info["ctrip"]}-{to_info["ctrip"]}?date={date}',
                'Origin': 'https://flights.ctrip.com'
            }
            
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('data') and data['data'].get('routeList'):
                    flights = []
                    
                    for route in data['data']['routeList']:
                        if 'legs' in route:
                            for leg in route['legs']:
                                flight_info = leg.get('flight', {})
                                price_info = leg.get('characteristic', {})
                                
                                flight = {
                                    'platform': '携程',
                                    'airline': flight_info.get('airlineName', ''),
                                    'flight_no': flight_info.get('flightNumber', ''),
                                    'dep_airport': flight_info.get('departureAirportInfo', {}).get('airportName', ''),
                                    'arr_airport': flight_info.get('arrivalAirportInfo', {}).get('airportName', ''),
                                    'dep_time': flight_info.get('departureDate', ''),
                                    'arr_time': flight_info.get('arrivalDate', ''),
                                    'price': price_info.get('lowestPrice', 0),
                                    'discount': price_info.get('discount', ''),
                                    'flight_time': flight_info.get('duration', '')
                                }
                                flights.append(flight)
                    
                    # 按价格排序
                    flights.sort(key=lambda x: x['price'])
                    
                    return {
                        'success': True,
                        'platform': '携程',
                        'count': len(flights),
                        'flights': flights[:15]  # 返回前15个
                    }
                else:
                    return {'error': '未找到航班数据', 'raw_response': data}
            else:
                return {'error': f'HTTP {response.status_code}', 'response': response.text[:500]}
                
        except Exception as e:
            return {'error': f'携程查询异常: {str(e)}'}
    
    def search_skyscanner(self, from_city, to_city, date):
        """
        Skyscanner 搜索 (国际航班)
        """
        try:
            from_info = self.get_city_info(from_city)
            to_info = self.get_city_info(to_city)
            
            if not from_info or not to_info:
                return {"error": "城市代码未找到"}
            
            # Skyscanner URL
            url = f"https://www.skyscanner.com/transport/flights/{from_info['iata'].lower()}/{to_info['iata'].lower()}/{date.replace('-', '')}/"
            
            return {
                'success': True,
                'platform': 'Skyscanner',
                'url': url,
                'note': '请访问链接查看详细价格'
            }
            
        except Exception as e:
            return {'error': f'Skyscanner查询异常: {str(e)}'}
    
    def search_google_flights(self, from_city, to_city, date):
        """
        Google Flights 搜索链接
        """
        try:
            from_info = self.get_city_info(from_city)
            to_info = self.get_city_info(to_city)
            
            if not from_info or not to_info:
                return {"error": "城市代码未找到"}
            
            # 构建Google Flights URL
            base_url = "https://www.google.com/travel/flights"
            params = {
                'hl': 'zh-CN',
                'curr': 'CNY'
            }
            
            # Google Flights 使用特定格式
            url = f"{base_url}?q=Flights+to+{to_info['iata']}+from+{from_info['iata']}+on+{date}"
            
            return {
                'success': True,
                'platform': 'Google Flights',
                'url': url,
                'note': '请访问链接查看详细价格'
            }
            
        except Exception as e:
            return {'error': f'Google Flights查询异常: {str(e)}'}
    
    def compare_all(self, from_city, to_city, date):
        """
        多平台比价
        """
        print(f"\n🔍 正在查询 {from_city} → {to_city} ({date}) 的机票价格...")
        print("=" * 80)
        
        results = {
            'search_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'route': f'{from_city} → {to_city}',
            'date': date,
            'results': []
        }
        
        # 携程
        print("\n📱 正在查询携程...")
        ctrip = self.search_ctrip_api(from_city, to_city, date)
        results['results'].append(ctrip)
        
        if ctrip.get('success'):
            print(f"✅ 携程: 找到 {ctrip['count']} 个航班")
            if ctrip['flights']:
                cheapest = ctrip['flights'][0]
                print(f"   最低价: ¥{cheapest['price']} ({cheapest['airline']} {cheapest['flight_no']})")
        else:
            print(f"❌ 携程: {ctrip.get('error', '查询失败')}")
        
        # Skyscanner
        print("\n🌐 Skyscanner链接...")
        sky = self.search_skyscanner(from_city, to_city, date)
        results['results'].append(sky)
        
        if sky.get('success'):
            print(f"✅ Skyscanner: {sky['url']}")
        
        # Google Flights
        print("\n🌐 Google Flights链接...")
        google = self.search_google_flights(from_city, to_city, date)
        results['results'].append(google)
        
        if google.get('success'):
            print(f"✅ Google Flights: {google['url']}")
        
        return results
    
    def print_flights(self, result):
        """
        打印航班详情
        """
        if not result.get('success'):
            print(f"❌ 查询失败: {result.get('error', '未知错误')}")
            return
        
        flights = result.get('flights', [])
        
        if not flights:
            print("未找到航班")
            return
        
        print(f"\n📋 找到 {len(flights)} 个航班 (按价格排序):")
        print("-" * 100)
        print(f"{'排名':<4} {'航司':<10} {'航班号':<10} {'出发':<20} {'到达':<20} {'价格':<10}")
        print("-" * 100)
        
        for i, f in enumerate(flights[:10], 1):
            dep = f"{f['dep_airport']} {f['dep_time'][11:16] if len(f['dep_time']) > 10 else f['dep_time']}"
            arr = f"{f['arr_airport']} {f['arr_time'][11:16] if len(f['arr_time']) > 10 else f['arr_time']}"
            print(f"{i:<4} {f['airline']:<10} {f['flight_no']:<10} {dep:<20} {arr:<20} ¥{f['price']:<10}")
        
        print("-" * 100)
        
        # 显示推荐
        if flights:
            cheapest = flights[0]
            print(f"\n💡 推荐: {cheapest['airline']} {cheapest['flight_no']} 仅 ¥{cheapest['price']}")
    
    def save_to_json(self, results, filename=None):
        """
        保存结果到JSON文件
        """
        if not filename:
            filename = f"flight_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存到: {filename}")


def main():
    monitor = FlightMonitor()
    
    print("=" * 80)
    print("🛫 机票价格监测工具")
    print("=" * 80)
    print("\n支持城市: 北京、上海、广州、深圳、成都、杭州、大阪、东京、首尔等")
    print("=" * 80)
    
    # 获取输入
    from_city = input("\n出发城市: ").strip()
    to_city = input("到达城市: ").strip()
    
    # 默认明天
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    date_input = input(f"出发日期 (默认 {tomorrow}): ").strip()
    date = date_input if date_input else tomorrow
    
    # 查询
    results = monitor.compare_all(from_city, to_city, date)
    
    # 打印详情
    for result in results['results']:
        if result.get('success') and 'flights' in result:
            monitor.print_flights(result)
    
    # 保存结果
    save = input("\n是否保存结果到JSON文件? (y/n): ").strip().lower()
    if save == 'y':
        monitor.save_to_json(results)
    
    print("\n✅ 查询完成!")


if __name__ == "__main__":
    main()
