import os
import json
import pickle
import uuid
import random
import time
import datetime
import threading
from collections import deque, defaultdict
from common import (
    DATE_FORMAT, DATETIME_FORMAT, 
    is_trading_day, get_trading_phase, 
    calculate_commission, TRADING_RULES
)
from crawler import StockDataCrawler

class TradingAPI:
    def __init__(self, initial_cash=100000.0, t_plus=1, data_source=None, filename="data/trading.pkl"):
        self.cash = initial_cash
        self.positions = defaultdict(list)  # {股票代码: [[数量, 成本价, 买入日期]]}
        self.frozen_positions = defaultdict(int)  # 冻结的持仓 {股票代码: 冻结数量}
        self.frozen_cash = 0.0  # 冻结的资金
        self.t_plus = t_plus
        self.trade_history = []  # 已完成交易记录
        self.pending_orders = deque()  # 挂单队列
        self.order_book = {}  # 订单簿 {order_id: order}
        self.initial_cash = initial_cash
        self.today_profit = 0.0
        self.filename = filename
        self.last_trading_day = datetime.datetime.now().date()
        self.data_source = data_source
        self.equity_history = []
        self.stock_prices = {}  # 股票当前价格缓存
        self.lock = threading.Lock()  # 线程锁
        self.last_save_time = datetime.datetime.now()
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        
        # 自动加载状态
        self.load_state()
        
        # 启动自动保存线程
        self.start_auto_save()

    def start_auto_save(self):
        """启动自动保存线程"""
        def auto_save_loop():
            while True:
                # 每10秒检查一次是否需要保存
                threading.Event().wait(1)
                self.auto_save()
        
        save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        save_thread.start()
    
    def auto_save(self):
        """自动保存状态"""
        with self.lock:
            # 如果距离上次保存超过30秒，或者有重要变更，则保存
            now = datetime.datetime.now()
            if (now - self.last_save_time).total_seconds() > 30:
                self.save_state()
                self.last_save_time = now

    def get_trading_phase(self, dt):
        """获取当前交易阶段"""
        return get_trading_phase(dt)
    
    def is_pre_market(self, dt):
        """是否为盘前交易时间"""
        phase = get_trading_phase(dt)
        return phase in ["pre_open", "open_call", "open_call_no_cancel"]
    
    def can_cancel_order(self, dt):
        """检查当前时间是否允许撤单"""
        # 在非交易时段或集合竞价时段不允许撤单
        if not is_trading_day(dt):
            return False
        
        phase = get_trading_phase(dt)
        return TRADING_RULES.get(phase, {}).get("can_cancel", False)
    
    def can_place_order(self, dt):
        """检查当前时间是否允许下单"""
        phase = get_trading_phase(dt)
        return phase not in ["non_trading", "closed"]
    
    def can_sell(self, stock_code, trade_date):
        """检查是否可以卖出（T+X规则）"""
        if stock_code not in self.positions:
            return False
        
        # 获取该股票的持仓明细（支持多次买入）
        for position in self.positions[stock_code]:
            buy_date = position[2]
            
            # 计算交易日差
            trade_date_dt = trade_date.date()
            days_diff = (trade_date_dt - buy_date).days
            
            # T+X规则：买入后至少X个交易日才能卖出
            if days_diff > self.t_plus:
                return False
        
        return True
    
    def get_current_price(self, stock_code, max_retries=3):
        """获取股票的最新价"""
        try:
            # 使用缓存，避免频繁请求
            if stock_code in self.stock_prices and time.time() - self.stock_prices[stock_code]['timestamp'] < 1:
                return self.stock_prices[stock_code]['price']
            
            crawler = StockDataCrawler(stock_code)
            price = crawler.get_current_price()
            self.stock_prices[stock_code] = {
                'price': price,
                'timestamp': time.time()
            }
            return price
        except Exception as e:
            print(f"获取实时价格失败: {str(e)}")
            return 0.0
    
    def get_stock_data(self, stock_code):
        """获取股票详细信息"""
        try:
            crawler = StockDataCrawler(stock_code)
            return crawler.get_stock_data()
        except Exception as e:
            print(f"获取股票数据失败: {str(e)}")
            return {}
    
    def get_stock_limit_prices(self, stock_code):
        """获取股票的涨跌停价"""
        try:
            crawler = StockDataCrawler(stock_code)
            return crawler.get_stock_limit_prices()
        except Exception as e:
            print(f"获取涨跌停价失败: {str(e)}")
            return (0, 0)
    
    def place_order(self, order_type, stock_code, price, quantity, trade_dt):
        """下单（买入或卖出）"""
        with self.lock:
            # 股票代码格式检查
            if not stock_code or len(stock_code) < 2:
                return None, "股票代码格式错误"
            
            if price <= 0:
                return None, "价格必须大于0"
            
            if quantity <= 0 or quantity % 100 != 0:
                return None, "数量必须是100的整数倍"
            
            # 检查交易时间
            if not self.can_place_order(trade_dt):
                return None, "当前时段不允许下单"
            
            # 检查涨跌停限制
            upper_limit, lower_limit = self.get_stock_limit_prices(stock_code)
            if order_type == "买入" and price > upper_limit:
                return None, f"委托价格超过涨停价 ¥{upper_limit:.2f}"
            if order_type == "卖出" and price < lower_limit:
                return None, f"委托价格低于跌停价 ¥{lower_limit:.2f}"
            
            # 卖出时检查可用持仓
            if order_type == "卖出":
                # 计算可用持仓 = 总持仓 - 已冻结持仓
                total_holdings = sum(pos[0] for pos in self.positions.get(stock_code, []))
                available_holdings = total_holdings - self.frozen_positions.get(stock_code, 0)
                
                if available_holdings < quantity:
                    return None, "可用持仓数量不足"
                
                # 检查T+1规则
                if not self.can_sell(stock_code, trade_dt):
                    return None, "T+1规则限制，当日买入的股票不可卖出"
                
                # 冻结相应数量的股票
                self.frozen_positions[stock_code] = self.frozen_positions.get(stock_code, 0) + quantity
            
            # 买入时检查可用资金
            if order_type == "买入":
                # 计算总成本 = 价格 * 数量 + 手续费
                total_cost = price * quantity
                commission_fee = calculate_commission(total_cost, is_buy=True)
                total_amount = total_cost + commission_fee
                
                # 可用资金 = 现金 - 已冻结资金
                available_cash = self.cash - self.frozen_cash
                
                if total_amount > available_cash:
                    return None, "可用资金不足"
                
                # 冻结相应资金
                self.frozen_cash += total_amount
            
            # 生成唯一订单ID
            order_id = str(uuid.uuid4())
            
            # 创建订单对象
            order = {
                'order_id': order_id,
                'type': order_type,
                'stock': stock_code,
                'price': price,
                'quantity': quantity,
                'status': 'pending',
                'created_at': trade_dt.strftime(DATETIME_FORMAT),
                'updated_at': trade_dt.strftime(DATETIME_FORMAT),
                'attempts': 0,
                'expiry': (trade_dt + datetime.timedelta(minutes=30)).strftime(DATETIME_FORMAT)
            }
            
            # 添加到挂单队列和订单簿
            self.pending_orders.append(order_id)
            self.order_book[order_id] = order
            
            # 保存状态
            self.save_state()
            
            return order_id, "订单已提交"
    
    def cancel_order(self, order_id, trade_dt):
        """撤单"""
        with self.lock:
            if order_id not in self.order_book:
                return False, "订单不存在"
            
            order = self.order_book[order_id]
            
            if order['status'] != 'pending':
                return False, "订单已完成或已取消，无法撤单"
            
            # 检查当前时间是否允许撤单
            if not self.can_cancel_order(trade_dt):
                return False, "当前时段不允许撤单"
            
            # 根据订单类型解冻资金或持仓
            if order['type'] == '买入':
                # 计算冻结的资金
                total_cost = float(order['price']) * int(order['quantity'])
                commission_fee = calculate_commission(total_cost, is_buy=True)
                total_amount = total_cost + commission_fee
                
                # 解冻资金
                self.frozen_cash -= total_amount
            else:  # 卖出
                # 解冻持仓
                stock_code = order['stock']
                quantity = int(order['quantity'])
                self.frozen_positions[stock_code] = max(0, self.frozen_positions.get(stock_code, 0) - quantity)
            
            # 更新订单状态
            order['status'] = 'canceled'
            order['updated_at'] = trade_dt.strftime(DATETIME_FORMAT)
            
            # 从挂单队列中移除
            if order_id in self.pending_orders:
                self.pending_orders.remove(order_id)
            
            # 保存状态
            self.save_state()
            
            return True, "撤单成功"
    
    def expire_old_orders(self):
        """检查并过期超时订单"""
        current_time = datetime.datetime.now()
        expired = False
        
        for order_id in list(self.pending_orders):
            order = self.order_book[order_id]
            expiry_time = datetime.datetime.strptime(order['expiry'], DATETIME_FORMAT)
            
            if current_time > expiry_time:
                # 根据订单类型解冻资金或持仓
                if order['type'] == '买入':
                    total_cost = float(order['price']) * int(order['quantity'])
                    commission_fee = calculate_commission(total_cost, is_buy=True)
                    total_amount = total_cost + commission_fee
                    self.frozen_cash -= total_amount
                else:  # 卖出
                    stock_code = order['stock']
                    quantity = int(order['quantity'])
                    self.frozen_positions[stock_code] = max(0, self.frozen_positions.get(stock_code, 0) - quantity)
                
                # 更新订单状态
                order['status'] = 'expired'
                self.pending_orders.remove(order_id)
                expired = True
        
        if expired:
            self.save_state()
        
        return expired
    
    def process_pending_orders(self):
        """处理挂单队列，尝试成交"""
        with self.lock:
            current_time = datetime.datetime.now()
            processed = False
            
            # 先处理过期订单
            self.expire_old_orders()
            
            # 获取当前交易阶段
            phase = get_trading_phase(current_time)
            
            # 在非交易时段或集合竞价时段不处理挂单
            if phase in ["non_trading", "closed", "break"]:
                return False
            
            # 获取当前市场价格
            market_prices = {}
            for order_id in list(self.pending_orders):
                order = self.order_book[order_id]
                stock_code = order['stock']
                
                if stock_code not in market_prices:
                    market_prices[stock_code] = self.get_current_price(stock_code)
                
                current_price = market_prices[stock_code]
                
                # 增加尝试次数
                order['attempts'] += 1
                order['updated_at'] = current_time.strftime(DATETIME_FORMAT)
                
                # 修复：正确的价格比较逻辑
                if order['type'] == '买入' and current_price <= float(order['price']) and current_price > 0:
                    # 尝试执行交易
                    success, _ = self.execute_trade(order)
                    if success:
                        processed = True
                        # 成交后从挂单队列中移除
                        if order_id in self.pending_orders:
                            self.pending_orders.remove(order_id)
                elif order['type'] == '卖出' and current_price >= float(order['price']) and current_price > 0:
                    # 尝试执行交易
                    success, _ = self.execute_trade(order)
                    if success:
                        processed = True
                        # 成交后从挂单队列中移除
                        if order_id in self.pending_orders:
                            self.pending_orders.remove(order_id)
                elif order['attempts'] > 10:
                    # 尝试超过10次仍未成交，自动取消
                    order['status'] = 'canceled'
                    if order_id in self.pending_orders:
                        self.pending_orders.remove(order_id)
                    processed = True
            
            # 如果有订单成交或取消，保存状态
            if processed:
                self.save_state()
            
            return processed
    
    def execute_trade(self, order):
        """执行交易（实际成交）"""
        stock_code = order['stock']
        price = float(order['price'])  # 使用订单价格作为成交价
        quantity = int(order['quantity'])
        trade_dt = datetime.datetime.now()
        
        if order['type'] == '买入':
            # 获取涨跌停价
            upper_limit, _ = self.get_stock_limit_prices(stock_code)
            if price > upper_limit:
                return False, f"价格超过涨停价 ¥{upper_limit:.2f}"
            
            total_cost = price * quantity
            
            # 计算交易费用
            commission_fee = calculate_commission(total_cost, is_buy=True)
            total_amount = total_cost + commission_fee
            
            # 检查资金是否充足（此时资金已冻结，理论上应该充足）
            if total_amount > (self.cash - self.frozen_cash):
                return False, "资金不足"
            
            # 解冻资金（因为要实际扣款）
            self.frozen_cash -= total_amount
            
            # 执行交易
            self.cash -= total_amount
            
            # 更新持仓 - 记录每次买入的成本和日期
            buy_date = trade_dt.date()
            self.positions[stock_code].append([quantity, price, buy_date])
            
            # 记录交易
            trade_record = {
                'order_id': order['order_id'],
                'type': '买入',
                'stock': stock_code,
                'price': price,
                'quantity': quantity,
                'amount': total_cost,
                'commission': commission_fee,
                'datetime': trade_dt.strftime(DATETIME_FORMAT),
                'profit': 0  # 买入没有利润
            }
            self.trade_history.append(trade_record)
            
            # 更新订单状态
            order['status'] = 'filled'
            order['updated_at'] = trade_dt.strftime(DATETIME_FORMAT)

            self.update_equity_history()
            self.save_state()
            
            return True, f"买入成功，成交价: ¥{price:.2f}"
        
        else:  # 卖出
            if stock_code not in self.positions or not self.positions[stock_code]:
                return False, "无此股票持仓"
            
            # 检查T+1规则
            if not self.can_sell(stock_code, trade_dt):
                return False, f"T+{self.t_plus}规则限制，不能卖出"
            
            # 解冻持仓
            self.frozen_positions[stock_code] = max(0, self.frozen_positions.get(stock_code, 0) - quantity)
            
            # 执行卖出 - 使用先进先出(FIFO)原则
            remaining_quantity = quantity
            total_profit = 0
            total_amount = 0
            
            while remaining_quantity > 0 and self.positions[stock_code]:
                position = self.positions[stock_code][0]
                pos_quantity, cost_price, buy_date = position
                
                # 计算本次卖出的数量
                sell_quantity = min(pos_quantity, remaining_quantity)
                
                # 计算本次卖出的金额
                sell_amount = price * sell_quantity
                total_amount += sell_amount
                
                # 计算交易费用
                commission_fee = calculate_commission(sell_amount, is_buy=False)
                
                # 计算本次卖出的盈亏
                profit = (price - cost_price) * sell_quantity - commission_fee
                total_profit += profit
                
                # 更新现金
                self.cash += (sell_amount - commission_fee)
                
                # 更新持仓
                if sell_quantity == pos_quantity:
                    # 全部卖出该批次
                    self.positions[stock_code].pop(0)
                else:
                    # 部分卖出
                    self.positions[stock_code][0][0] -= sell_quantity
                
                # 记录交易
                trade_record = {
                    'order_id': order['order_id'],
                    'type': '卖出',
                    'stock': stock_code,
                    'price': price,
                    'quantity': sell_quantity,
                    'amount': sell_amount,
                    'profit': profit,
                    'commission': commission_fee,
                    'datetime': trade_dt.strftime(DATETIME_FORMAT)
                }
                self.trade_history.append(trade_record)
                
                remaining_quantity -= sell_quantity
            
            # 更新当日盈亏
            self.today_profit += total_profit
            
            # 更新订单状态
            order['status'] = 'filled'
            order['updated_at'] = trade_dt.strftime(DATETIME_FORMAT)

            self.update_equity_history()
            self.save_state()
            
            return True, f"卖出成功，成交价: ¥{price:.2f}"
    
    def buy(self, stock_code, price, quantity, trade_dt=None):
        """买入股票 - 支持盘前盘后交易"""
        trade_dt = trade_dt or datetime.datetime.now()
        
        if not self.can_place_order(trade_dt):
            return False, "非交易时间"
        
        # 在盘前交易时段，使用限价单
        if self.is_pre_market(trade_dt):
            return self.place_order('买入', stock_code, price, quantity, trade_dt)
        else:
            # 正常交易时段，尝试立即执行
            return self.execute_immediate_trade('买入', stock_code, price, quantity, trade_dt)
    
    def sell(self, stock_code, price, quantity, trade_dt=None):
        """卖出股票 - 支持盘前盘后交易"""
        trade_dt = trade_dt or datetime.datetime.now()
        
        if not self.can_place_order(trade_dt):
            return False, "非交易时间"
        
        # 在盘前交易时段，使用限价单
        if self.is_pre_market(trade_dt):
            return self.place_order('卖出', stock_code, price, quantity, trade_dt)
        else:
            # 正常交易时段，尝试立即执行
            return self.execute_immediate_trade('卖出', stock_code, price, quantity, trade_dt)
    
    def execute_immediate_trade(self, trade_type, stock_code, price, quantity, trade_dt):
        """在正常交易时段立即执行交易"""
        # 获取最新价
        current_price = self.get_current_price(stock_code)
        if current_price <= 0:
            return False, "无法获取当前股价"
        
        # 检查价格是否符合规则
        if trade_type == "买入" and price < current_price:
            return False, f"买入价格(¥{price:.2f})低于当前价(¥{current_price:.2f})"
        elif trade_type == "卖出" and price > current_price:
            return False, f"卖出价格(¥{price:.2f})高于当前价(¥{current_price:.2f})"
        
        # 创建临时订单对象
        order = {
            'order_id': str(uuid.uuid4()),
            'type': trade_type,
            'stock': stock_code,
            'price': price,
            'quantity': quantity,
            'status': 'pending',
            'created_at': trade_dt.strftime(DATETIME_FORMAT),
            'updated_at': trade_dt.strftime(DATETIME_FORMAT),
            'attempts': 0,
            'expiry': (trade_dt + datetime.timedelta(minutes=30)).strftime(DATETIME_FORMAT)
        }
        
        # 尝试立即执行
        success, message = self.execute_trade(order)
        if success:
            return True, message
        else:
            # 如果无法立即成交，转为挂单
            self.pending_orders.append(order['order_id'])
            self.order_book[order['order_id']] = order
            
            # 冻结资金或持仓
            if trade_type == '买入':
                total_cost = price * quantity
                commission_fee = calculate_commission(total_cost, is_buy=True)
                total_amount = total_cost + commission_fee
                self.frozen_cash += total_amount
            else:
                self.frozen_positions[stock_code] = self.frozen_positions.get(stock_code, 0) + quantity
            
            return True, f"订单已转为挂单，订单号: {order['order_id']}"
    
    def get_portfolio_value(self):
        """计算投资组合价值"""
        return self.cash + self.get_stock_value()
    
    def get_total_profit(self):
        """计算总盈亏"""
        return (self.cash + self.get_stock_value()) - self.initial_cash
    
    def get_stock_value(self):
        """计算股票市值"""
        stock_value = 0.0
        for stock, positions in self.positions.items():
            # 计算该股票的总持仓数量
            total_quantity = sum(pos[0] for pos in positions)
            current_price = self.get_current_price(stock)
            stock_value += current_price * total_quantity
        return stock_value
    
    def get_available_cash(self):
        """获取可用资金"""
        return self.cash - self.frozen_cash
    
    def get_available_quantity(self, stock_code):
        """获取可用持仓数量"""
        total_holdings = sum(pos[0] for pos in self.positions.get(stock_code, []))
        frozen = self.frozen_positions.get(stock_code, 0)
        return total_holdings - frozen
    
    def get_total_assets(self):
        """计算总资产"""
        return self.cash + self.get_stock_value()
    
    def save_state(self, filename=None):
        """保存当前状态到文件"""
        filename = filename or self.filename
        state = {
            'cash': self.cash,
            'positions': dict(self.positions),
            'frozen_positions': dict(self.frozen_positions),
            'frozen_cash': self.frozen_cash,
            't_plus': self.t_plus,
            'trade_history': self.trade_history,
            'pending_orders': list(self.pending_orders),
            'order_book': self.order_book,
            'initial_cash': self.initial_cash,
            'today_profit': self.today_profit,
            'last_trading_day': self.last_trading_day,
            'equity_history': self.equity_history
        }
        try:
            with open(filename, 'wb') as f:
                pickle.dump(state, f)
            return True, "状态保存成功"
        except Exception as e:
            print(f"保存状态失败: {str(e)}")
            return False, f"保存状态失败: {str(e)}"
    
    def load_state(self, filename=None):
        """从文件加载状态"""
        filename = filename or self.filename
        try:
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    state = pickle.load(f)
                self.cash = state['cash']
                self.positions = defaultdict(list, state.get('positions', {}))
                self.frozen_positions = defaultdict(int, state.get('frozen_positions', {}))
                self.frozen_cash = state.get('frozen_cash', 0.0)
                self.t_plus = state.get('t_plus', 1)
                self.trade_history = state.get('trade_history', [])
                self.pending_orders = deque(state.get('pending_orders', []))
                self.order_book = state.get('order_book', {})
                self.initial_cash = state.get('initial_cash', 100000.0)
                self.today_profit = state.get('today_profit', 0.0)
                self.last_trading_day = state.get('last_trading_day', datetime.datetime.now().date())
                self.equity_history = state.get('equity_history', [])
                return True, "状态加载成功"
            return False, "状态文件不存在"
        except Exception as e:
            print(f"加载状态失败: {str(e)}")
            # 创建初始状态
            self.save_state()
            return False, f"加载状态失败: {str(e)}，已创建初始状态"
    
    def generate_report(self):
        """生成投资组合报告"""
        # 计算持仓股票的当前价格
        stock_prices = {}
        for stock in self.positions.keys():
            stock_prices[stock] = self.get_current_price(stock)
        
        # 计算总资产
        total_assets = self.get_total_assets()
        
        # 计算持仓详情
        position_details = {}
        for stock, positions in self.positions.items():
            total_quantity = sum(pos[0] for pos in positions)
            
            # 修复：过滤持仓为0的股票
            if total_quantity <= 0:
                continue
                
            total_cost = 0.0
            earliest_buy_date = None
            
            # 计算总数量、总成本和最早买入日期
            for pos in positions:
                quantity, cost_price, buy_date = pos
                total_cost += quantity * cost_price
                
                # 记录最早买入日期
                if not earliest_buy_date or buy_date < earliest_buy_date:
                    earliest_buy_date = buy_date
            
            # 计算平均成本价
            avg_cost = total_cost / total_quantity if total_quantity > 0 else 0
            current_price = stock_prices.get(stock, 0)
            market_value = current_price * total_quantity
            profit = (current_price - avg_cost) * total_quantity
            
            position_details[stock] = {
                'quantity': total_quantity,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'market_value': market_value,
                'profit': profit,
                'buy_date': earliest_buy_date.strftime(DATE_FORMAT) if earliest_buy_date else "未知"
            }
        
        return {
            'cash': self.cash,
            'frozen_cash': self.frozen_cash,
            'positions': position_details,
            'frozen_positions': dict(self.frozen_positions),
            'stock_prices': stock_prices,
            'num_positions': len(self.positions),
            'trade_count': len(self.trade_history),
            'pending_orders': len(self.pending_orders),
            'last_trade': self.trade_history[-1] if self.trade_history else None,
            'total_profit': self.get_total_profit(),
            'today_profit': self.today_profit,
            'total_assets': total_assets,
            'stock_value': self.get_stock_value(),
            'equity_history': self.equity_history
        }
    
    def get_all_orders(self):
        """获取所有订单"""
        return list(self.order_book.values())
    
    def get_trade_history(self):
        """获取交易历史"""
        return self.trade_history
    
    def update_equity_history(self):
        """更新资金曲线历史"""
        now = datetime.datetime.now()
        total_assets = self.get_total_assets()
        
        # 避免重复记录相同时间点的数据
        if self.equity_history and self.equity_history[-1]['timestamp'] == now.strftime(DATETIME_FORMAT):
            self.equity_history[-1] = {
                'timestamp': now.strftime(DATETIME_FORMAT),
                'total_assets': total_assets,
                'cash': self.cash,
                'stock_value': self.get_stock_value()
            }
        else:
            self.equity_history.append({
                'timestamp': now.strftime(DATETIME_FORMAT),
                'total_assets': total_assets,
                'cash': self.cash,
                'stock_value': self.get_stock_value()
            })
        
        # 只保留最近100条记录
        if len(self.equity_history) > 100:
            self.equity_history = self.equity_history[-100:]

    def get_equity_history(self):
        """获取资金曲线历史"""
        return self.equity_history