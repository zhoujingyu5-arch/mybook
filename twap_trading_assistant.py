#!/usr/bin/env python3
"""
TWAP 交易辅助系统
功能：
1. 实时计算市场VWAP
2. 监控你的成交均价
3. 自动拆单建议
4. 盈亏实时计算
5. 交易提醒
"""

import time
import json
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional

class TWAPTradingAssistant:
    """TWAP交易助手"""
    
    def __init__(self):
        self.instructions = []  # 今日指令列表
        self.trades = []  # 成交记录
        self.market_data = deque(maxlen=1000)  # 市场数据缓存
        self.running = False
        
    def add_instruction(self, symbol: str, side: str, quantity: int, 
                       received_time: Optional[datetime] = None):
        """
        添加基金经理指令
        
        Args:
            symbol: 股票代码
            side: 'BUY' 或 'SELL'
            quantity: 数量
            received_time: 接收时间，默认当前
        """
        if received_time is None:
            received_time = datetime.now()
            
        instruction = {
            'id': len(self.instructions) + 1,
            'symbol': symbol,
            'side': side,  # BUY or SELL
            'quantity': quantity,
            'received_time': received_time,
            'completed': False,
            'executed_qty': 0,
            'avg_price': 0.0,
            'trades': []
        }
        
        self.instructions.append(instruction)
        
        print(f"\n📋 新增指令 #{instruction['id']}")
        print(f"   股票: {symbol}")
        print(f"   方向: {'买入' if side == 'BUY' else '卖出'}")
        print(f"   数量: {quantity}")
        print(f"   时间: {received_time.strftime('%H:%M:%S')}")
        
        # 自动给出交易建议
        self._suggest_strategy(instruction)
        
        return instruction['id']
    
    def _suggest_strategy(self, instruction: Dict):
        """根据当前市场给出交易策略建议"""
        side = instruction['side']
        
        print(f"\n💡 交易策略建议:")
        
        if side == 'BUY':
            print("""
   买入策略:
   1. 观察开盘后走势
   2. 若下跌: 分批买入，越跌越买
      - 每跌1%买入20%
      - 尾盘必须完成
   3. 若上涨: 等待回调
      - 14:30后若无回调，集中买入
   4. 若震荡: 均匀分布在午盘买入
            """)
        else:
            print("""
   卖出策略:
   1. 观察开盘后走势
   2. 若上涨: 分批卖出，越涨越卖
      - 每涨1%卖出20%
      - 尾盘必须完成
   3. 若下跌: 等待反弹
      - 14:30后若无反弹，集中卖出
   4. 若震荡: 均匀分布在午盘卖出
            """)
    
    def record_trade(self, instruction_id: int, price: float, quantity: int):
        """记录成交"""
        instruction = next((i for i in self.instructions if i['id'] == instruction_id), None)
        if not instruction:
            print(f"❌ 指令 #{instruction_id} 不存在")
            return
        
        trade = {
            'time': datetime.now(),
            'price': price,
            'quantity': quantity
        }
        
        instruction['trades'].append(trade)
        instruction['executed_qty'] += quantity
        
        # 计算成交均价
        total_cost = sum(t['price'] * t['quantity'] for t in instruction['trades'])
        instruction['avg_price'] = total_cost / instruction['executed_qty']
        
        # 检查是否完成
        if instruction['executed_qty'] >= instruction['quantity']:
            instruction['completed'] = True
        
        print(f"\n✅ 成交记录 指令#{instruction_id}")
        print(f"   价格: {price:.2f}")
        print(f"   数量: {quantity}")
        print(f"   成交均价: {instruction['avg_price']:.2f}")
        print(f"   完成度: {instruction['executed_qty']}/{instruction['quantity']} " + 
              f"({instruction['executed_qty']/instruction['quantity']*100:.1f}%)")
    
    def update_market_data(self, symbol: str, price: float, volume: int):
        """更新市场数据（用于计算市场VWAP）"""
        self.market_data.append({
            'time': datetime.now(),
            'symbol': symbol,
            'price': price,
            'volume': volume
        })
    
    def calculate_market_vwap(self, symbol: str, start_time: datetime) -> Optional[float]:
        """
        计算市场VWAP（从指令接收时刻到现在）
        
        Returns:
            VWAP价格，如果没有数据返回None
        """
        relevant_data = [
            d for d in self.market_data 
            if d['symbol'] == symbol and d['time'] >= start_time
        ]
        
        if not relevant_data:
            return None
        
        total_value = sum(d['price'] * d['volume'] for d in relevant_data)
        total_volume = sum(d['volume'] for d in relevant_data)
        
        return total_value / total_volume if total_volume > 0 else None
    
    def calculate_pnl(self, instruction_id: int, current_market_vwap: float) -> Dict:
        """
        计算单笔指令盈亏
        
        Returns:
            {
                'pnl_amount': 盈亏金额,
                'pnl_percent': 盈亏百分比,
                'is_profit': 是否盈利
            }
        """
        instruction = next((i for i in self.instructions if i['id'] == instruction_id), None)
        if not instruction:
            return None
        
        side = instruction['side']
        avg_price = instruction['avg_price']
        executed_qty = instruction['executed_qty']
        
        if side == 'BUY':
            # 买入：市场均价 > 成交均价 = 盈利
            pnl_amount = (current_market_vwap - avg_price) * executed_qty
        else:
            # 卖出：成交均价 > 市场均价 = 盈利
            pnl_amount = (avg_price - current_market_vwap) * executed_qty
        
        # 盈亏百分比（相对于成交金额）
        trade_value = avg_price * executed_qty
        pnl_percent = (pnl_amount / trade_value * 100) if trade_value > 0 else 0
        
        return {
            'symbol': instruction['symbol'],
            'side': side,
            'executed_qty': executed_qty,
            'avg_price': avg_price,
            'market_vwap': current_market_vwap,
            'pnl_amount': pnl_amount,
            'pnl_percent': pnl_percent,
            'is_profit': pnl_amount > 0
        }
    
    def get_daily_summary(self) -> Dict:
        """获取当日汇总"""
        total_pnl = 0
        total_trade_value = 0
        completed_instructions = 0
        
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_instructions': len(self.instructions),
            'completed_instructions': 0,
            'total_pnl_amount': 0,
            'total_trade_value': 0,
            'overall_pnl_percent': 0,
            'details': []
        }
        
        for instruction in self.instructions:
            if instruction['executed_qty'] == 0:
                continue
            
            # 计算该指令的市场VWAP（简化，实际应该用实时数据）
            market_vwap = instruction['avg_price']  # 这里应该传入真实VWAP
            
            pnl = self.calculate_pnl(instruction['id'], market_vwap)
            if pnl:
                summary['details'].append(pnl)
                total_pnl += pnl['pnl_amount']
                total_trade_value += instruction['avg_price'] * instruction['executed_qty']
                
            if instruction['completed']:
                summary['completed_instructions'] += 1
        
        summary['total_pnl_amount'] = total_pnl
        summary['total_trade_value'] = total_trade_value
        summary['overall_pnl_percent'] = (total_pnl / total_trade_value * 100) if total_trade_value > 0 else 0
        
        return summary
    
    def print_daily_report(self):
        """打印日终报告"""
        summary = self.get_daily_summary()
        
        print("\n" + "=" * 60)
        print(f"📊 TWAP 交易日报 - {summary['date']}")
        print("=" * 60)
        
        print(f"\n📋 指令统计:")
        print(f"   总指令数: {summary['total_instructions']}")
        print(f"   已完成: {summary['completed_instructions']}")
        
        print(f"\n💰 盈亏汇总:")
        print(f"   总盈亏金额: ¥{summary['total_pnl_amount']:,.2f}")
        print(f"   总成交金额: ¥{summary['total_trade_value']:,.2f}")
        
        pnl_percent = summary['overall_pnl_percent']
        emoji = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
        print(f"   盈亏百分比: {emoji} {pnl_percent:+.3f}%")
        
        if summary['details']:
            print(f"\n📈 明细:")
            for detail in summary['details']:
                emoji = "✅" if detail['is_profit'] else "❌"
                print(f"   {emoji} {detail['symbol']} {detail['side']}: " +
                      f"¥{detail['pnl_amount']:,.2f} ({detail['pnl_percent']:+.3f}%)")
        
        print("\n" + "=" * 60)
    
    def get_urgent_reminders(self) -> List[str]:
        """获取紧急提醒"""
        reminders = []
        now = datetime.now()
        
        for instruction in self.instructions:
            if instruction['completed']:
                continue
            
            progress = instruction['executed_qty'] / instruction['quantity']
            
            # 尾盘提醒
            if now.hour >= 14 and now.minute >= 30 and progress < 1.0:
                reminders.append(
                    f"🚨 尾盘提醒: 指令#{instruction['id']} {instruction['symbol']} " +
                    f"仅完成 {progress*100:.1f}%，请立即完成！"
                )
            # 进度提醒
            elif progress < 0.5 and now.hour >= 11:
                reminders.append(
                    f"⚠️  进度提醒: 指令#{instruction['id']} {instruction['symbol']} " +
                    f"仅完成 {progress*100:.1f}%"
                )
        
        return reminders


# ========== 使用示例 ==========

def demo():
    """演示如何使用"""
    print("=" * 60)
    print("🤖 TWAP 交易辅助系统")
    print("=" * 60)
    
    assistant = TWAPTradingAssistant()
    
    # 模拟接收指令
    print("\n--- 早盘接收指令 ---")
    
    # 买入指令
    id1 = assistant.add_instruction('000001.SZ', 'BUY', 10000)
    
    # 卖出指令
    id2 = assistant.add_instruction('000002.SZ', 'SELL', 5000)
    
    print("\n--- 模拟交易过程 ---")
    
    # 模拟成交
    assistant.record_trade(id1, 10.5, 2000)  # 买入2000股，价格10.5
    assistant.record_trade(id1, 10.3, 3000)  # 买入3000股，价格10.3
    
    assistant.record_trade(id2, 25.2, 2000)  # 卖出2000股，价格25.2
    assistant.record_trade(id2, 25.5, 3000)  # 卖出3000股，价格25.5
    
    # 模拟市场数据更新
    assistant.update_market_data('000001.SZ', 10.4, 100000)
    assistant.update_market_data('000002.SZ', 25.3, 50000)
    
    # 获取紧急提醒
    reminders = assistant.get_urgent_reminders()
    if reminders:
        print("\n🔔 提醒:")
        for r in reminders:
            print(f"   {r}")
    
    # 打印日终报告
    assistant.print_daily_report()


if __name__ == "__main__":
    demo()
