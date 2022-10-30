'''
Author: Jakcy Chang
Date: 2022-10-20 16:04:54
LastEditors: Jakcy Chang
LastEditTime: 2022-10-28 17:57:52
Description: 
'''
'''
## 5分钟级别、三均线策略
- 10, 20, 120 均线
- 120 均线做 多空 过滤
- MA120之上
  - MA10 上穿 MA20 金叉 做多
  - MA10 下穿 MA20 死叉 平多
- MA120之下
  - MA10 下穿 MA20 死叉 做空
  - MA10 上穿 MA20 金叉 平空
- Strategy_TripleMa_v0.1.py
'''
from vnpy.trader.constant import Interval, Direction, Offset
from vnpy.trader.object import Interval

from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)


class JackyStrategyTripleMa01(CtaTemplate):
    author = "用Python的交易员"
    
    bar_window = 60
    fast_window = 7
    slow_window = 30
    filter_window = 120
    # 每次开仓资金，计算开仓数量
    trade_money = 10
    # 止盈百分比
    per_win = 0.07
    # 止损百分比
    per_lose = 0.01

    # 多头进场价格
    long_entry_price = 0.0
    # 空头进场价格
    short_entry_price = 0.0

    # 快线当前交易数据
    fast_ma0 = 0.0
    # 快线后一个交易数据
    fast_ma1 = 0.0

    # 慢线当前交易数据
    slow_ma0 = 0.0
    # 慢线后一个交易数据
    slow_ma1 = 0.0

    # 120 过滤多空线当前交易数据
    filter_ma0 = 0.0
    filter_ma1 = 0.0

    parameters = ["bar_window", "fast_window", "slow_window", "filter_window", "trade_money", "per_win","per_lose"]
    variables = ["fast_ma0", "fast_ma1", "slow_ma0", "slow_ma1", "filter_ma0", "filter_ma1"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 5 分钟柱状图
        self.bg = BarGenerator(
            self.on_bar, 
            window=self.bar_window, 
            on_window_bar=self.on_min_bar, 
            interval=Interval.MINUTE
        )
        # 初始化 120根柱状图
        self.am = ArrayManager(200)

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        # 加载前3的数据
        self.load_bar(3)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")
        self.put_event()

    def on_stop(self):
        
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

        self.put_event()

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)
    
    def on_bar(self, bar:BarData):
        self.bg.update_bar(bar)

    def on_min_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.cancel_all()       #   先撤单
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        fast_ma = am.sma(self.fast_window, array=True)
        self.fast_ma0 = fast_ma[-1]
        self.fast_ma1 = fast_ma[-2]

        slow_ma = am.sma(self.slow_window, array=True)
        self.slow_ma0 = slow_ma[-1]
        self.slow_ma1 = slow_ma[-2]

        filter_ma = am.sma(self.filter_window, array=True)
        self.filter_ma0 = filter_ma[-1]
        self.filter_ma1 = filter_ma[-2]
        # print('filter_ma0 ====  ', self.filter_ma0)

        # 上穿
        cross_over = (self.fast_ma0 > self.slow_ma0) and (self.fast_ma1 < self.slow_ma1)
        # 下穿
        cross_below = (self.fast_ma0 < self.slow_ma0) and (self.fast_ma1 > self.slow_ma1)

        
        # - MA120之上
        #   - MA10 上穿 MA20 金叉 做多
        #   - MA10 下穿 MA20 死叉 平多
        # filter_up = (self.fast_ma0 > self.filter_ma0) and (self.fast_ma1 > self.filter_ma0) and (self.slow_ma0 > self.filter_ma0) and (self.slow_ma1 > self.filter_ma0) 
        filter_up = bar.close_price > self.filter_ma0
        # print('filter_up ======= ', filter_up)
        
        
        # - MA120之下
        #   - MA10 下穿 MA20 死叉 做空
        #   - MA10 上穿 MA20 金叉 平空
        # filter_down = (self.fast_ma0 < self.filter_ma0) and (self.fast_ma1 < self.filter_ma0) and (self.slow_ma0 < self.filter_ma0) and (self.slow_ma1 < self.filter_ma0)
        filter_down = bar.close_price < self.filter_ma0
        # print('filter_down ====== ', filter_down)

        # 120 趋势线向上走，不开空单
        filter_up_run = self.filter_ma0 >= self.filter_ma1
        # 120 趋势线向下走，不开多单
        filter_down_run = self.filter_ma0 <= self.filter_ma1

        # 为开仓，执行开仓条件
        if self.pos == 0:
            if cross_over and filter_up:                        #   金叉做多
                self.buy(bar.close_price, self.trade_money/bar.close_price)
            if cross_below and filter_down:                     #   死叉做空
                self.short(bar.close_price, self.trade_money/bar.close_price)
        elif self.pos > 0:
            if filter_up:
                if cross_below:
                    self.sell(bar.close_price, abs(self.pos))   #   死叉平多
                else:   
                    self.sell(self.long_entry_price * (1-self.per_lose), abs(self.pos), stop=True)       #   多头进场后，下跌%1止损
                    self.sell(self.long_entry_price * (1+self.per_win), abs(self.pos))                  #   多单止盈
        elif self.pos < 0:
            if filter_down:
                if cross_over:
                    self.cover(bar.close_price, abs(self.pos))  #   金叉平空
                else:
                    self.cover(self.short_entry_price * (1-self.per_win), abs(self.pos))                #   空单止盈
                    self.cover(self.short_entry_price * (1+self.per_lose), abs(self.pos), stop=True)     #   空头进场后，上涨1%止损

        # else:
        #     if cross_below and filter_up and self.pos > 0:      
        #         self.sell(bar.close_price, abs(self.pos))
        #     if cross_over and filter_down and self.pos < 0:     #   金叉平空
        #         self.cover(bar.close_price, abs(self.pos))


        # if filter_up:
        #     if cross_over:                          #   金叉做多
        #         if self.pos == 0:
        #             self.buy(bar.close_price, 1)
        #         elif self.pos < 0:
        #             self.cover(bar.close_price, 1)
        #             self.buy(bar.close_price, 1)
        #     elif cross_below:                       #   死叉平多
        #         if self.pos > 0:
        #             self.sell(bar.close_price, 1)

        # if filter_down:
        #     if cross_below:                         #   死叉做空
        #         if self.pos == 0:                     
        #             self.short(bar.close_price, 1)
        #         if self.pos > 0:
        #             self.sell(bar.close_price, 1)
        #             self.short(bar.close_price, 1)
        #     elif cross_over:                        #   金叉平空
        #         if self.pos < 0:
        #             self.cover(bar.close_price, 1)
            
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        if self.pos != 0:
            # 记录多头进场价格
            if trade.direction == Direction.LONG and trade.offset == Offset.OPEN:
                self.long_entry_price = trade.price
            # 记录空头进场价格
            elif trade.direction == Direction.SHORT and trade.offset == Offset.OPEN:
                self.short_entry_price = trade.price
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass

