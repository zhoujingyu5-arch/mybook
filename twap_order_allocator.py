#!/usr/bin/env python3
"""
TWAP 最优指令量分配策略
目标：最大化相对市场VWAP的超额收益
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class TWAPOrderAllocator:
    """TWAP指令量分配器"""
    
    def __init__(self):
        self.time_slots = self._generate_time_slots()
    
    def _generate_time_slots(self) -> List[Tuple[str, str, float]]:
        """
        生成交易时间段及权重
        权重基于历史波动率和流动性分析
        """
        slots = [
            # (开始时间, 结束时间, 权重)
            ("09:30", "09:45", 0.8),   # 开盘波动大，谨慎
            ("09:45", "10:30", 1.2),   # 早盘活跃，机会多
            ("10:30", "11:30", 1.0),   # 正常交易
            ("13:00", "14:00", 0.9),   # 午盘开始
            ("14:00", "14:30", 1.1),   # 下午活跃
            ("14:30", "14:50", 1.5),   # 尾盘关键，必须完成
            ("14:50", "15:00", 2.0),   # 最后10分钟，扫单
        ]
        return slots
    
    def allocate_buy_order(self, total_quantity: int, market_trend: str = "unknown") -> List[Dict]:
        """
        买入指令最优分配策略
        
        Args:
            total_quantity: 总买入数量
            market_trend: 市场趋势 ("up", "down", "flat", "unknown")
            
        Returns:
            分配计划列表
        """
        allocations = []
        
        if market_trend == "down":
            # 下跌趋势：前少后多，越跌越买
            weights = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0]  # 尾盘权重高
            strategy = "下跌买入法：前少后多，越跌越买"
            
        elif market_trend == "up":
            # 上涨趋势：前多后少，避免追高
            weights = [2.0, 1.5, 1.0, 0.8, 0.5, 0.2, 0.0]  # 尾盘少买
            strategy = "上涨买入法：前多后少，避免追高"
            
        elif market_trend == "flat":
            # 震荡：均匀分布
            weights = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            strategy = "震荡买入法：均匀分布"
            
        else:  # unknown
            # 未知：保守策略，均匀+尾盘保障
            weights = [0.8, 1.0, 1.0, 1.0, 1.0, 1.5, 1.7]
            strategy = "保守买入法：均匀+尾盘保障"
        
        # 计算分配量
        total_weight = sum(weights)
        remaining = total_quantity
        
        for i, (start, end, base_weight) in enumerate(self.time_slots):
            if i == len(self.time_slots) - 1:
                # 最后一个时间段，分配剩余全部
                qty = remaining
            else:
                # 按比例分配
                qty = int(total_quantity * weights[i] / total_weight)
                qty = min(qty, remaining)
            
            if qty > 0:
                allocations.append({
                    "time_slot": f"{start}-{end}",
                    "quantity": qty,
                    "percentage": qty / total_quantity * 100,
                    "strategy": "买入",
                    "note": self._get_buy_note(market_trend, i)
                })
                remaining -= qty
        
        return {
            "side": "BUY",
            "total_quantity": total_quantity,
            "market_trend": market_trend,
            "strategy": strategy,
            "allocations": allocations,
            "key_points": self._get_buy_key_points(market_trend)
        }
    
    def allocate_sell_order(self, total_quantity: int, market_trend: str = "unknown") -> List[Dict]:
        """
        卖出指令最优分配策略
        """
        allocations = []
        
        if market_trend == "up":
            # 上涨趋势：前少后多，越涨越卖
            weights = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0]
            strategy = "上涨卖出法：前少后多，越涨越卖"
            
        elif market_trend == "down":
            # 下跌趋势：前多后少，避免杀跌
            weights = [2.5, 2.0, 1.5, 1.0, 0.5, 0.3, 0.2]
            strategy = "下跌卖出法：前多后少，避免杀跌"
            
        elif market_trend == "flat":
            weights = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            strategy = "震荡卖出法：均匀分布"
            
        else:
            weights = [1.5, 1.3, 1.1, 1.0, 0.9, 0.8, 0.4]
            strategy = "保守卖出法：前多后少"
        
        total_weight = sum(weights)
        remaining = total_quantity
        
        for i, (start, end, base_weight) in enumerate(self.time_slots):
            if i == len(self.time_slots) - 1:
                qty = remaining
            else:
                qty = int(total_quantity * weights[i] / total_weight)
                qty = min(qty, remaining)
            
            if qty > 0:
                allocations.append({
                    "time_slot": f"{start}-{end}",
                    "quantity": qty,
                    "percentage": qty / total_quantity * 100,
                    "strategy": "卖出",
                    "note": self._get_sell_note(market_trend, i)
                })
                remaining -= qty
        
        return {
            "side": "SELL",
            "total_quantity": total_quantity,
            "market_trend": market_trend,
            "strategy": strategy,
            "allocations": allocations,
            "key_points": self._get_sell_key_points(market_trend)
        }
    
    def _get_buy_note(self, trend: str, slot_index: int) -> str:
        """获取买入时间段备注"""
        notes = {
            "down": ["观察", "试探买入", "继续买入", "加仓", "重仓", "满仓", "扫单"],
            "up": ["抢筹", "追涨", "减仓买入", "观望", "等待", "尾盘补单", "必须完成"],
            "flat": ["均匀买入"] * 7,
            "unknown": ["试探", "观察", "均匀", "均匀", "均匀", "加仓", "必须完成"]
        }
        return notes.get(trend, notes["unknown"])[slot_index]
    
    def _get_sell_note(self, trend: str, slot_index: int) -> str:
        """获取卖出时间段备注"""
        notes = {
            "up": ["观察", "试探卖出", "继续卖出", "加仓卖", "重仓卖", "满仓卖", "扫单"],
            "down": ["抢跑", "杀跌止损", "减仓", "观望", "等待", "尾盘补卖", "必须完成"],
            "flat": ["均匀卖出"] * 7,
            "unknown": ["试探", "观察", "均匀", "均匀", "均匀", "减仓", "必须完成"]
        }
        return notes.get(trend, notes["unknown"])[slot_index]
    
    def _get_buy_key_points(self, trend: str) -> List[str]:
        """获取买入关键点"""
        points = {
            "down": [
                "每跌1-2%加仓一次",
                "尾盘14:50前完成80%",
                "最后10分钟扫单完成",
                "成交均价会低于市场VWAP"
            ],
            "up": [
                "开盘积极买入",
                "10:30后减少买入",
                "14:30后视情况补单",
                "避免追高，宁可尾盘买"
            ],
            "flat": [
                "均匀分布在全天",
                "每30分钟买入一次",
                "尾盘确保完成"
            ],
            "unknown": [
                "早盘试探性买入",
                "观察趋势后再加仓",
                "尾盘必须完成指令"
            ]
        }
        return points.get(trend, points["unknown"])
    
    def _get_sell_key_points(self, trend: str) -> List[str]:
        """获取卖出关键点"""
        points = {
            "up": [
                "每涨1-2%减仓一次",
                "尾盘14:50前完成80%",
                "最后10分钟扫单完成",
                "成交均价会高于市场VWAP"
            ],
            "down": [
                "开盘积极卖出",
                "10:30后减少卖出",
                "14:30后视情况补单",
                "避免杀跌，宁可尾盘卖"
            ],
            "flat": [
                "均匀分布在全天",
                "每30分钟卖出一次",
                "尾盘确保完成"
            ],
            "unknown": [
                "早盘试探性卖出",
                "观察趋势后再加仓",
                "尾盘必须完成指令"
            ]
        }
        return points.get(trend, points["unknown"])


def print_allocation_plan(plan: Dict):
    """打印分配计划"""
    print("\n" + "=" * 70)
    print(f"📊 TWAP 最优指令分配方案")
    print("=" * 70)
    
    side_emoji = "🟢" if plan["side"] == "BUY" else "🔴"
    print(f"\n{side_emoji} 指令方向: {'买入' if plan['side'] == 'BUY' else '卖出'}")
    print(f"📈 市场趋势: {plan['market_trend']}")
    print(f"📋 总数量: {plan['total_quantity']:,}")
    print(f"💡 策略: {plan['strategy']}")
    
    print("\n" + "-" * 70)
    print(f"{'时间段':<15} {'数量':<10} {'占比':<8} {'操作提示':<20}")
    print("-" * 70)
    
    for alloc in plan["allocations"]:
        print(f"{alloc['time_slot']:<15} {alloc['quantity']:<10,} " +
              f"{alloc['percentage']:<7.1f}% {alloc['note']:<20}")
    
    print("-" * 70)
    print(f"{'合计':<15} {plan['total_quantity']:<10,} {'100.0%':<8}")
    
    print("\n🎯 关键执行要点:")
    for i, point in enumerate(plan["key_points"], 1):
        print(f"   {i}. {point}")
    
    print("\n⚠️  风险控制:")
    print("   • 14:50必须完成80%以上")
    print("   • 14:55必须完成100%")
    print("   • 宁可价格差，不可未完成")
    print("=" * 70)


def demo():
    """演示不同场景下的分配策略"""
    allocator = TWAPOrderAllocator()
    
    print("\n" + "=" * 70)
    print("TWAP 最优指令量分配策略演示")
    print("=" * 70)
    
    scenarios = [
        # (方向, 数量, 趋势)
        ("BUY", 100000, "down"),
        ("BUY", 100000, "up"),
        ("SELL", 50000, "up"),
        ("SELL", 50000, "down"),
    ]
    
    for side, qty, trend in scenarios:
        if side == "BUY":
            plan = allocator.allocate_buy_order(qty, trend)
        else:
            plan = allocator.allocate_sell_order(qty, trend)
        
        print_allocation_plan(plan)
        input("\n按回车查看下一个方案...")


def interactive():
    """交互式使用"""
    allocator = TWAPOrderAllocator()
    
    print("\n" + "=" * 70)
    print("🤖 TWAP 指令分配助手")
    print("=" * 70)
    
    # 获取用户输入
    side = input("\n指令方向 (BUY/SELL): ").strip().upper()
    while side not in ["BUY", "SELL"]:
        side = input("请输入 BUY 或 SELL: ").strip().upper()
    
    quantity = int(input("总数量: ").strip())
    
    print("\n市场趋势选项:")
    print("  1. up - 上涨")
    print("  2. down - 下跌")
    print("  3. flat - 震荡")
    print("  4. unknown - 未知")
    
    trend_choice = input("选择趋势 (1-4): ").strip()
    trends = {"1": "up", "2": "down", "3": "flat", "4": "unknown"}
    trend = trends.get(trend_choice, "unknown")
    
    # 生成方案
    if side == "BUY":
        plan = allocator.allocate_buy_order(quantity, trend)
    else:
        plan = allocator.allocate_sell_order(quantity, trend)
    
    print_allocation_plan(plan)
    
    # 保存到文件
    save = input("\n是否保存方案到文件? (y/n): ").strip().lower()
    if save == "y":
        filename = f"twap_plan_{side}_{trend}_{datetime.now().strftime('%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        print(f"✅ 方案已保存到: {filename}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        interactive()
