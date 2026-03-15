#!/usr/bin/env python3
"""
Amadeus Flight API 集成模块
真实机票价格查询
"""

import requests
import json
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class AmadeusFlightAPI:
    """
    Amadeus 航班搜索 API 客户端
    文档: https://developers.amadeus.com/self-service/category/air/api-doc/flight-offers-search
    """
    
    def __init__(self, api_key: str, api_secret: str, test_mode: bool = True):
        """
        初始化
        
        Args:
            api_key: Amadeus API Key
            api_secret: Amadeus API Secret
            test_mode: True=测试环境, False=生产环境
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.test_mode = test_mode
        
        # API 基础URL
        if test_mode:
            self.base_url = "https://test.api.amadeus.com"
        else:
            self.base_url = "https://api.amadeus.com"
        
        self.access_token = None
        self.token_expires = None
        
    def _get_access_token(self) -> str:
        """获取访问令牌"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
        
        url = f"{self.base_url}/v1/security/oauth2/token"
        
        # Base64 编码 credentials
        credentials = base64.b64encode(
            f"{self.api_key}:{self.api_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials"
        }
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        # 提前5分钟过期
        expires_in = token_data.get("expires_in", 1799)
        self.token_expires = datetime.now() + timedelta(seconds=expires_in - 300)
        
        return self.access_token
    
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        return_date: Optional[str] = None,
        children: int = 0,
        infants: int = 0,
        travel_class: Optional[str] = None,  # ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
        max_results: int = 10,
        currency: str = "CNY"
    ) -> Dict:
        """
        搜索航班
        
        Args:
            origin: 出发地 IATA 代码 (如 PEK)
            destination: 目的地 IATA 代码 (如 SHA)
            departure_date: 出发日期 (YYYY-MM-DD)
            adults: 成人数量
            return_date: 返程日期 (往返查询)
            children: 儿童数量
            infants: 婴儿数量
            travel_class: 舱位等级
            max_results: 最大结果数
            currency: 货币代码
            
        Returns:
            航班搜索结果
        """
        token = self._get_access_token()
        
        url = f"{self.base_url}/v2/shopping/flight-offers"
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
            "currencyCode": currency
        }
        
        if return_date:
            params["returnDate"] = return_date
        if children > 0:
            params["children"] = children
        if infants > 0:
            params["infants"] = infants
        if travel_class:
            params["travelClass"] = travel_class
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return self._parse_flight_offers(response.json())
        else:
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
    
    def _parse_flight_offers(self, data: Dict) -> Dict:
        """解析航班报价数据"""
        flights = []
        
        for offer in data.get("data", []):
            # 获取价格
            price = offer.get("price", {})
            total_price = float(price.get("total", 0))
            currency = price.get("currency", "CNY")
            
            # 获取行程信息
            itineraries = offer.get("itineraries", [])
            if not itineraries:
                continue
                
            itinerary = itineraries[0]  # 单程取第一个
            segments = itinerary.get("segments", [])
            if not segments:
                continue
            
            # 提取航班信息
            first_segment = segments[0]
            last_segment = segments[-1]
            
            # 航空公司
            carrier = first_segment.get("carrierCode", "")
            airline_name = self._get_airline_name(carrier)
            
            # 航班号
            flight_number = first_segment.get("number", "")
            
            # 出发信息
            departure = first_segment.get("departure", {})
            dep_airport = departure.get("iataCode", "")
            dep_time = departure.get("at", "")
            
            # 到达信息
            arrival = last_segment.get("arrival", {})
            arr_airport = arrival.get("iataCode", "")
            arr_time = arrival.get("at", "")
            
            # 计算飞行时间
            duration = itinerary.get("duration", "")
            
            # 转机次数
            stops = len(segments) - 1
            
            flights.append({
                "airline_code": carrier,
                "airline": airline_name,
                "flight_no": f"{carrier}{flight_number}",
                "dep_airport": dep_airport,
                "arr_airport": arr_airport,
                "dep_time": dep_time,
                "arr_time": arr_time,
                "dep_time_short": dep_time[11:16] if len(dep_time) > 10 else dep_time,
                "arr_time_short": arr_time[11:16] if len(arr_time) > 10 else arr_time,
                "price": total_price,
                "currency": currency,
                "duration": duration,
                "stops": stops,
                "source": "Amadeus"
            })
        
        # 按价格排序
        flights.sort(key=lambda x: x["price"])
        
        return {
            "success": True,
            "platform": "Amadeus",
            "count": len(flights),
            "flights": flights,
            "lowest_price": flights[0]["price"] if flights else None,
            "search_time": datetime.now().isoformat(),
            "currency": currency
        }
    
    def _get_airline_name(self, code: str) -> str:
        """获取航空公司名称"""
        airlines = {
            "CA": "中国国际航空",
            "MU": "中国东方航空",
            "CZ": "中国南方航空",
            "HU": "海南航空",
            "MF": "厦门航空",
            "ZH": "深圳航空",
            "SC": "山东航空",
            "3U": "四川航空",
            "9C": "春秋航空",
            "HO": "吉祥航空",
            "JL": "日本航空",
            "NH": "全日空",
            "KE": "大韩航空",
            "OZ": "韩亚航空",
            "SQ": "新加坡航空",
            "CX": "国泰航空",
            "TG": "泰国航空",
            "BA": "英国航空",
            "AF": "法国航空",
            "LH": "汉莎航空",
            "AA": "美国航空",
            "UA": "美联航",
            "DL": "达美航空",
            "QF": "澳洲航空",
        }
        return airlines.get(code, code)
    
    def search_round_trip(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        **kwargs
    ) -> Dict:
        """往返查询"""
        return self.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            **kwargs
        )
    
    def search_multi_dates(
        self,
        origin: str,
        destination: str,
        start_date: str,
        days: int = 7,
        **kwargs
    ) -> Dict:
        """多日期查询"""
        results = []
        start = datetime.strptime(start_date, "%Y-%m-%d")
        
        for i in range(days):
            date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            result = self.search_flights(
                origin=origin,
                destination=destination,
                departure_date=date,
                max_results=3,  # 每天只取前3个
                **kwargs
            )
            
            if result.get("success"):
                results.append({
                    "date": date,
                    "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][
                        (start + timedelta(days=i)).weekday()
                    ],
                    "lowest_price": result.get("lowest_price"),
                    "flights": result.get("flights", [])
                })
        
        # 找出最低价日期
        valid_results = [r for r in results if r.get("lowest_price")]
        cheapest = min(valid_results, key=lambda x: x["lowest_price"]) if valid_results else None
        
        return {
            "success": len(results) > 0,
            "route": f"{origin} → {destination}",
            "days": days,
            "results": results,
            "cheapest_date": cheapest
        }


# 城市代码映射
CITY_CODES = {
    "北京": "PEK",
    "上海": "SHA",  # 虹桥
    "上海浦东": "PVG",
    "广州": "CAN",
    "深圳": "SZX",
    "成都": "CTU",
    "杭州": "HGH",
    "武汉": "WUH",
    "西安": "XIY",
    "重庆": "CKG",
    "青岛": "TAO",
    "大连": "DLC",
    "厦门": "XMN",
    "昆明": "KMG",
    "天津": "TSN",
    "南京": "NKG",
    "长沙": "CSX",
    "沈阳": "SHE",
    "哈尔滨": "HRB",
    "济南": "TNA",
    "郑州": "CGO",
    "福州": "FOC",
    "大阪": "KIX",
    "东京": "NRT",
    "首尔": "ICN",
    "新加坡": "SIN",
    "曼谷": "BKK",
    "香港": "HKG",
    "台北": "TPE",
    "伦敦": "LHR",
    "巴黎": "CDG",
    "纽约": "JFK",
    "洛杉矶": "LAX",
    "旧金山": "SFO",
    "悉尼": "SYD",
    "墨尔本": "MEL",
}


def get_city_code(city_name: str) -> str:
    """获取城市 IATA 代码"""
    return CITY_CODES.get(city_name, city_name)


# ========== 使用示例 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("🛫 Amadeus Flight API - 真实机票价格查询")
    print("=" * 60)
    print("\n⚠️  请先设置 API Key 和 Secret:")
    print("export AMADEUS_API_KEY=your_api_key")
    print("export AMADEUS_API_SECRET=your_api_secret")
    print("\n或者修改代码中的 api_key 和 api_secret 变量")
    print("=" * 60)
    
    # 从环境变量读取（推荐）
    import os
    api_key = os.getenv("AMADEUS_API_KEY", "YOUR_API_KEY")
    api_secret = os.getenv("AMADEUS_API_SECRET", "YOUR_API_SECRET")
    
    if api_key == "YOUR_API_KEY":
        print("\n❌ 未设置 API Key，请先注册 Amadeus 账号")
        print("注册地址: https://developers.amadeus.com")
        exit(1)
    
    # 初始化客户端
    client = AmadeusFlightAPI(api_key, api_secret, test_mode=True)
    
    # 测试查询
    print("\n🔍 测试查询: 北京(PEK) → 上海(SHA) 2025-04-15")
    
    result = client.search_flights(
        origin="PEK",
        destination="SHA",
        departure_date="2025-04-15",
        max_results=5
    )
    
    if result["success"]:
        print(f"\n✅ 找到 {result['count']} 个航班")
        print(f"💰 最低价格: {result['currency']} {result['lowest_price']}")
        print("\n航班列表:")
        print("-" * 80)
        
        for i, flight in enumerate(result["flights"][:5], 1):
            print(f"{i}. {flight['airline']} {flight['flight_no']}")
            print(f"   出发: {flight['dep_airport']} {flight['dep_time_short']}")
            print(f"   到达: {flight['arr_airport']} {flight['arr_time_short']}")
            print(f"   价格: {flight['currency']} {flight['price']}")
            if flight['stops'] > 0:
                print(f"   转机: {flight['stops']} 次")
            print()
    else:
        print(f"\n❌ 查询失败: {result.get('error')}")
