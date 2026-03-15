#!/usr/bin/env python3
"""
机票价格爬虫 - 四元投资理论配套工具
支持: 携程、去哪儿、飞猪等平台
"""

import requests
import json
import time
import re
from datetime import datetime, timedelta
from urllib.parse import quote

class FlightPriceScraper:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    def search_ctrip(self, from_city, to_city, date):
        """
        搜索携程机票
        """
        try:
            # 获取城市代码
            from_code = self._get_city_code(from_city)
            to_code = self._get_city_code(to_city)
            
            if not from_code or not to_code:
                return {"error": "城市代码获取失败"}
            
            url = f"https://flights.ctrip.com/itinerary/api/12808/products"
            
            payload = {
                "flightWay": "Oneway",
                "classType": "ALL",
                "hasChild": False,
                "hasBaby": False,
                "searchIndex": 1,
                "airportParams": [{
                    "dcity": from_code,
                    "acity": to_code,
                    "dcityname": from_city,
                    "acityname": to_city,
                    "date": date
                }]
            }
            
            response = self.session.post(url, json=payload, headers=self.headers, timeout=30)
            data = response.json()
            
            if data.get('data') and data['data'].get('routeList'):
                flights = []
                for route in data['data']['routeList']:
                    if 'legs' in route:
                        for leg in route['legs']:
                            flight = leg.get('flight', {})
                            price = leg.get('characteristic', {}).get('lowestPrice', 0)
                            
                            flights.append({
                                'airline': flight.get('airlineName', ''),
                                'flight_no': flight.get('flightNumber', ''),
                                'departure': flight.get('departureAirportInfo', {}).get('airportName', ''),
                                'arrival': flight.get('arrivalAirportInfo', {}).get('airportName', ''),
                                'dep_time': flight.get('departureDate', ''),
                                'arr_time': flight.get('arrivalDate', ''),
                                'price': price,
                                'source': '携程'
                            })
                
                return {
                    "success": True,
                    "platform": "携程",
                    "count": len(flights),
                    "flights": sorted(flights, key=lambda x: x['price'])[:10]  # 返回最便宜的10个
                }
            
            return {"error": "未找到航班数据"}
            
        except Exception as e:
            return {"error": f"携程搜索失败: {str(e)}"}
    
    def search_qunar(self, from_city, to_city, date):
        """
        搜索去哪儿机票
        """
        try:
            # 使用去哪儿API
            url = f"https://flight.qunar.com/twell/flight/SearchFlight"
            
            params = {
                'from': from_city,
                'to': to_city,
                'date': date,
                'fromType': 'na',
                'toType': 'na'
            }
            
            # 去哪儿需要特殊处理，这里返回模拟数据或提示
            return {
                "success": False,
                "platform": "去哪儿",
                "note": "去哪儿需要登录态，建议使用携程或飞猪API"
            }
            
        except Exception as e:
            return {"error": f"去哪儿搜索失败: {str(e)}"}
    
    def search_flightradar(self, from_iata, to_iata, date):
        """
        使用FlightRadar API (需要API key)
        """
        try:
            # 这是一个示例，实际使用需要注册API
            url = f"https://api.flightradar24.com/common/v1/search.json"
            
            return {
                "success": False,
                "note": "需要FlightRadar24 API密钥"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_city_code(self, city_name):
        """
        获取城市代码映射
        """
        city_map = {
            '北京': 'BJS',
            '上海': 'SHA',
            '广州': 'CAN',
            '深圳': 'SZX',
            '成都': 'CTU',
            '杭州': 'HGH',
            '武汉': 'WUH',
            '西安': 'XIY',
            '重庆': 'CKG',
            '青岛': 'TAO',
            '大连': 'DLC',
            '厦门': 'XMN',
            '昆明': 'KMG',
            '天津': 'TSN',
            '南京': 'NKG',
            '长沙': 'CSX',
            '沈阳': 'SHE',
            '哈尔滨': 'HRB',
            '济南': 'TNA',
            '郑州': 'CGO',
            '福州': 'FOC',
            '大阪': 'OSA',
            '东京': 'TYO',
            '首尔': 'SEL',
            '新加坡': 'SIN',
            '曼谷': 'BKK',
            '香港': 'HKG',
            '台北': 'TPE',
            '伦敦': 'LON',
            '巴黎': 'PAR',
            '纽约': 'NYC',
            '洛杉矶': 'LAX',
            '旧金山': 'SFO',
            '悉尼': 'SYD',
            '墨尔本': 'MEL',
        }
        return city_map.get(city_name)
    
    def compare_prices(self, from_city, to_city, date):
        """
        多平台比价
        """
        results = {
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "route": f"{from_city} → {to_city}",
            "date": date,
            "platforms": []
        }
        
        # 携程
        ctrip_result = self.search_ctrip(from_city, to_city, date)
        results["platforms"].append(ctrip_result)
        
        # 去哪儿
        qunar_result = self.search_qunar(from_city, to_city, date)
        results["platforms"].append(qunar_result)
        
        return results
    
    def monitor_price(self, from_city, to_city, date, threshold=None):
        """
        监测价格，低于阈值时返回提醒
        """
        result = self.search_ctrip(from_city, to_city, date)
        
        if result.get('success') and result.get('flights'):
            cheapest = result['flights'][0]
            
            alert = {
                "alert": False,
                "current_lowest": cheapest['price'],
                "threshold": threshold,
                "flight": cheapest
            }
            
            if threshold and cheapest['price'] <= threshold:
                alert['alert'] = True
                alert['message'] = f"🚨 价格提醒：{from_city}→{to_city} 机票价格降至 {cheapest['price']} 元！"
            
            return alert
        
        return {"error": "获取价格失败"}


def main():
    scraper = FlightPriceScraper()
    
    # 示例：搜索北京到大阪的机票
    print("=" * 50)
    print("机票价格查询工具")
    print("=" * 50)
    
    # 获取用户输入
    from_city = input("出发城市（如：北京）: ").strip()
    to_city = input("到达城市（如：大阪）: ").strip()
    date = input("出发日期（如：2026-03-20）: ").strip()
    
    print(f"\n正在查询 {from_city} → {to_city} {date} 的机票...")
    print("-" * 50)
    
    result = scraper.search_ctrip(from_city, to_city, date)
    
    if result.get('success'):
        print(f"✅ 找到 {result['count']} 个航班")
        print(f"\n最便宜的前10个航班：")
        print("-" * 80)
        
        for i, flight in enumerate(result['flights'], 1):
            print(f"{i}. {flight['airline']} {flight['flight_no']}")
            print(f"   出发：{flight['departure']} {flight['dep_time']}")
            print(f"   到达：{flight['arrival']} {flight['arr_time']}")
            print(f"   价格：¥{flight['price']}")
            print()
    else:
        print(f"❌ 查询失败：{result.get('error', '未知错误')}")


if __name__ == "__main__":
    main()
