#!/usr/bin/env python3
"""
机票价格完整监测系统
功能：定时监测、价格提醒、历史追踪、多日期比价、往返查询
"""

import requests
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime, timedelta
from pathlib import Path
import schedule
import threading

class FlightPriceMonitor:
    def __init__(self):
        self.data_dir = Path("flight_data")
        self.data_dir.mkdir(exist_ok=True)
        
        # 邮件配置
        self.email_config = {
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 465,
            'sender': '470528113@qq.com',
            'auth_code': 'wxudoynlksbabjha',
            'receiver': '470528113@qq.com'
        }
        
        # 城市代码
        self.city_codes = {
            '北京': {'iata': 'PEK', 'ctrip': 'BJS'},
            '上海': {'iata': 'SHA', 'ctrip': 'SHA'},
            '广州': {'iata': 'CAN', 'ctrip': 'CAN'},
            '深圳': {'iata': 'SZX', 'ctrip': 'SZX'},
            '成都': {'iata': 'CTU', 'ctrip': 'CTU'},
            '杭州': {'iata': 'HGH', 'ctrip': 'HGH'},
            '大阪': {'iata': 'KIX', 'ctrip': 'OSA'},
            '东京': {'iata': 'NRT', 'ctrip': 'TYO'},
            '首尔': {'iata': 'ICN', 'ctrip': 'SEL'},
            '新加坡': {'iata': 'SIN', 'ctrip': 'SIN'},
            '曼谷': {'iata': 'BKK', 'ctrip': 'BKK'},
            '香港': {'iata': 'HKG', 'ctrip': 'HKG'},
        }
        
        # 监测任务列表
        self.watch_list_file = self.data_dir / "watch_list.json"
        self.watch_list = self._load_watch_list()
    
    def _load_watch_list(self):
        """加载监测列表"""
        if self.watch_list_file.exists():
            with open(self.watch_list_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_watch_list(self):
        """保存监测列表"""
        with open(self.watch_list_file, 'w', encoding='utf-8') as f:
            json.dump(self.watch_list, f, ensure_ascii=False, indent=2)
    
    def search_ctrip(self, from_city, to_city, date):
        """查询携程机票"""
        try:
            from_info = self.city_codes.get(from_city)
            to_info = self.city_codes.get(to_city)
            
            if not from_info or not to_info:
                return {"error": "不支持的城市"}
            
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
                    "date": date
                }]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Referer': f'https://flights.ctrip.com/',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                flights = []
                
                if data.get('data') and data['data'].get('routeList'):
                    for route in data['data']['routeList']:
                        if 'legs' in route:
                            for leg in route['legs']:
                                flight_info = leg.get('flight', {})
                                price_info = leg.get('characteristic', {})
                                
                                flights.append({
                                    'airline': flight_info.get('airlineName', ''),
                                    'flight_no': flight_info.get('flightNumber', ''),
                                    'dep_airport': flight_info.get('departureAirportInfo', {}).get('airportName', ''),
                                    'arr_airport': flight_info.get('arrivalAirportInfo', {}).get('airportName', ''),
                                    'dep_time': flight_info.get('departureDate', ''),
                                    'arr_time': flight_info.get('arrivalDate', ''),
                                    'price': price_info.get('lowestPrice', 0),
                                    'source': '携程'
                                })
                
                flights.sort(key=lambda x: x['price'])
                return {
                    'success': True,
                    'count': len(flights),
                    'flights': flights,
                    'lowest_price': flights[0]['price'] if flights else None
                }
            
            return {'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'error': str(e)}
    
    def search_round_trip(self, from_city, to_city, go_date, back_date):
        """往返票查询"""
        print(f"\n🔄 查询往返票: {from_city} ↔ {to_city}")
        print(f"   去程: {go_date} | 返程: {back_date}")
        
        go_result = self.search_ctrip(from_city, to_city, go_date)
        back_result = self.search_ctrip(to_city, from_city, back_date)
        
        return {
            'go': go_result,
            'back': back_result,
            'total_lowest': (
                go_result.get('lowest_price', 0) + back_result.get('lowest_price', 0)
                if go_result.get('success') and back_result.get('success') else None
            )
        }
    
    def search_multi_dates(self, from_city, to_city, start_date, days=7):
        """多日期比价 - 查询一周内最低价格"""
        print(f"\n📅 查询 {days} 天内价格走势: {from_city} → {to_city}")
        
        results = []
        start = datetime.strptime(start_date, '%Y-%m-%d')
        
        for i in range(days):
            date = (start + timedelta(days=i)).strftime('%Y-%m-%d')
            result = self.search_ctrip(from_city, to_city, date)
            
            if result.get('success'):
                results.append({
                    'date': date,
                    'lowest_price': result.get('lowest_price'),
                    'flight_count': result.get('count'),
                    'cheapest_flight': result['flights'][0] if result['flights'] else None
                })
            else:
                results.append({
                    'date': date,
                    'error': result.get('error')
                })
            
            time.sleep(0.5)  # 避免请求过快
        
        # 找出最低价日期
        valid_results = [r for r in results if r.get('lowest_price')]
        if valid_results:
            cheapest = min(valid_results, key=lambda x: x['lowest_price'])
            print(f"\n💡 推荐出行日期: {cheapest['date']} (¥{cheapest['lowest_price']})")
        
        return results
    
    def add_watch(self, from_city, to_city, date, threshold_price, note=""):
        """添加价格监测任务"""
        watch_id = f"{from_city}_{to_city}_{date}_{int(time.time())}"
        
        task = {
            'id': watch_id,
            'from': from_city,
            'to': to_city,
            'date': date,
            'threshold': threshold_price,
            'note': note,
            'created_at': datetime.now().isoformat(),
            'active': True,
            'last_check': None,
            'last_price': None,
            'alert_sent': False
        }
        
        self.watch_list.append(task)
        self._save_watch_list()
        
        print(f"✅ 已添加监测任务: {from_city}→{to_city} {date}")
        print(f"   提醒阈值: ¥{threshold_price}")
        return watch_id
    
    def remove_watch(self, watch_id):
        """移除监测任务"""
        self.watch_list = [w for w in self.watch_list if w['id'] != watch_id]
        self._save_watch_list()
        print(f"✅ 已移除监测任务: {watch_id}")
    
    def list_watches(self):
        """列出所有监测任务"""
        if not self.watch_list:
            print("暂无监测任务")
            return
        
        print("\n📋 当前监测任务:")
        print("-" * 80)
        for i, task in enumerate(self.watch_list, 1):
            status = "🟢 运行中" if task['active'] else "🔴 已暂停"
            last_price = f"¥{task['last_price']}" if task['last_price'] else "未查询"
            print(f"{i}. [{status}] {task['from']}→{task['to']} {task['date']}")
            print(f"   阈值: ¥{task['threshold']} | 当前: {last_price}")
            if task['note']:
                print(f"   备注: {task['note']}")
            print()
    
    def check_all_watches(self):
        """检查所有监测任务"""
        print(f"\n🔍 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始检查监测任务...")
        
        for task in self.watch_list:
            if not task['active']:
                continue
            
            result = self.search_ctrip(task['from'], task['to'], task['date'])
            
            if result.get('success') and result.get('lowest_price'):
                current_price = result['lowest_price']
                task['last_price'] = current_price
                task['last_check'] = datetime.now().isoformat()
                
                print(f"   {task['from']}→{task['to']}: ¥{current_price} (阈值: ¥{task['threshold']})")
                
                # 价格低于阈值且未发送过提醒
                if current_price <= task['threshold'] and not task['alert_sent']:
                    self.send_price_alert(task, current_price, result['flights'][0])
                    task['alert_sent'] = True
                
                # 保存历史数据
                self._save_price_history(task, current_price)
        
        self._save_watch_list()
        print("✅ 检查完成")
    
    def send_price_alert(self, task, price, flight):
        """发送价格提醒邮件"""
        try:
            subject = f"🚨 机票价格提醒: {task['from']}→{task['to']} 降至 ¥{price}"
            
            content = f"""
您好！您关注的机票价格已降至设定阈值以下。

📍 航线: {task['from']} → {task['to']}
📅 日期: {task['date']}
💰 当前价格: ¥{price}
🎯 提醒阈值: ¥{task['threshold']}

✈️ 推荐航班:
   航司: {flight['airline']}
   航班号: {flight['flight_no']}
   出发: {flight['dep_airport']} {flight['dep_time']}
   到达: {flight['arr_airport']} {flight['arr_time']}

🔗 立即预订:
   携程: https://flights.ctrip.com/

---
本邮件由机票价格监测系统自动发送
发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            msg = MIMEText(content, 'plain', 'utf-8')
            msg['From'] = formataddr(('机票监测系统', self.email_config['sender']))
            msg['To'] = self.email_config['receiver']
            msg['Subject'] = subject
            
            server = smtplib.SMTP_SSL(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.login(self.email_config['sender'], self.email_config['auth_code'])
            server.sendmail(self.email_config['sender'], [self.email_config['receiver']], msg.as_string())
            server.quit()
            
            print(f"   📧 已发送价格提醒邮件: ¥{price}")
            
        except Exception as e:
            print(f"   ❌ 邮件发送失败: {e}")
    
    def _save_price_history(self, task, price):
        """保存价格历史"""
        history_file = self.data_dir / f"history_{task['from']}_{task['to']}.json"
        
        history = []
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        history.append({
            'date': task['date'],
            'check_time': datetime.now().isoformat(),
            'price': price
        })
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def show_price_trend(self, from_city, to_city):
        """显示价格走势"""
        history_file = self.data_dir / f"history_{from_city}_{to_city}.json"
        
        if not history_file.exists():
            print(f"暂无 {from_city}→{to_city} 的历史价格数据")
            return
        
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        print(f"\n📈 {from_city}→{to_city} 价格走势:")
        print("-" * 60)
        
        for record in history[-20:]:  # 显示最近20条
            print(f"{record['check_time'][:16]} | ¥{record['price']}")
    
    def run_scheduler(self):
        """启动定时监测"""
        print("\n⏰ 启动定时监测服务...")
        print("   每天 9:00、12:00、18:00 自动检查")
        
        # 设置定时任务
        schedule.every().day.at("09:00").do(self.check_all_watches)
        schedule.every().day.at("12:00").do(self.check_all_watches)
        schedule.every().day.at("18:00").do(self.check_all_watches)
        
        # 立即执行一次
        self.check_all_watches()
        
        # 保持运行
        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    monitor = FlightPriceMonitor()
    
    print("=" * 80)
    print("🛫 机票价格完整监测系统")
    print("=" * 80)
    print("\n功能菜单:")
    print("1. 单次查询")
    print("2. 往返票查询")
    print("3. 多日期比价")
    print("4. 添加价格监测")
    print("5. 查看监测任务")
    print("6. 删除监测任务")
    print("7. 查看价格走势")
    print("8. 立即检查所有任务")
    print("9. 启动定时监测服务")
    print("0. 退出")
    print("=" * 80)
    
    while True:
        choice = input("\n请选择功能 (0-9): ").strip()
        
        if choice == '1':
            from_city = input("出发城市: ").strip()
            to_city = input("到达城市: ").strip()
            date = input("日期 (如 2026-03-25): ").strip()
            result = monitor.search_ctrip(from_city, to_city, date)
            if result.get('success'):
                print(f"\n✅ 找到 {result['count']} 个航班")
                for i, f in enumerate(result['flights'][:5], 1):
                    print(f"{i}. {f['airline']} {f['flight_no']} ¥{f['price']}")
            else:
                print(f"❌ {result.get('error')}")
        
        elif choice == '2':
            from_city = input("出发城市: ").strip()
            to_city = input("到达城市: ").strip()
            go_date = input("去程日期: ").strip()
            back_date = input("返程日期: ").strip()
            result = monitor.search_round_trip(from_city, to_city, go_date, back_date)
            if result.get('total_lowest'):
                print(f"\n💰 往返最低总价: ¥{result['total_lowest']}")
        
        elif choice == '3':
            from_city = input("出发城市: ").strip()
            to_city = input("到达城市: ").strip()
            start_date = input("开始日期: ").strip()
            days = int(input("查询天数 (默认7): ") or 7)
            results = monitor.search_multi_dates(from_city, to_city, start_date, days)
            for r in results:
                if r.get('lowest_price'):
                    print(f"{r['date']}: ¥{r['lowest_price']}")
        
        elif choice == '4':
            from_city = input("出发城市: ").strip()
            to_city = input("到达城市: ").strip()
            date = input("日期: ").strip()
            threshold = int(input("提醒阈值 (元): ").strip())
            note = input("备注 (可选): ").strip()
            monitor.add_watch(from_city, to_city, date, threshold, note)
        
        elif choice == '5':
            monitor.list_watches()
        
        elif choice == '6':
            monitor.list_watches()
            watch_id = input("输入要删除的任务ID: ").strip()
            monitor.remove_watch(watch_id)
        
        elif choice == '7':
            from_city = input("出发城市: ").strip()
            to_city = input("到达城市: ").strip()
            monitor.show_price_trend(from_city, to_city)
        
        elif choice == '8':
            monitor.check_all_watches()
        
        elif choice == '9':
            print("\n⚠️  启动后将持续运行，按 Ctrl+C 停止")
            confirm = input("确认启动? (y/n): ").strip().lower()
            if confirm == 'y':
                monitor.run_scheduler()
        
        elif choice == '0':
            print("再见!")
            break


if __name__ == "__main__":
    main()
