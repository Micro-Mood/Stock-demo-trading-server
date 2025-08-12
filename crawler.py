import time
from datetime import datetime
import random
from common import is_trading_day, get_trading_phase
import requests

class StockDataCrawler:
    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.stock_symbol = stock_code.upper()
        self.last_price = random.uniform(5, 100)  # 随机初始价格
        self.prev_close = self.last_price  # 昨日收盘价
        self.last_update = datetime.now()
    
    def _process_price(self, value, precision):
        """处理价格精度转换"""
        if value is None:
            return None
        if precision not in (None, -1, 0):
            value /= (10 ** precision)
        return round(value, 2)  # 保留2位小数

    def _process_volume(self, value):
        """处理成交量/成交额"""
        if value is None:
            return 0
        return round(value, 2)

    def get_current_price(self, max_retries=3):
        """获取股票的最新价"""
        # 辅助函数：处理价格精度
        def process_price(value, precision_field):
            """根据精度字段处理价格值"""
            if value is None:
                return None
                
            # 应用精度转换（如果需要）
            if precision_field not in (None, -1) and isinstance(precision_field, int) and precision_field != 0:
                precision = 10 ** precision_field
                value = value / precision
                
            return value

        # 构造股票代码
        secid = "0." + self.stock_code[2:]  # A股格式
        
        # 只请求必要字段
        fields = "f43,f59"  # 最新价和精度字段
        
        # 构造API URL
        base_url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "invt": 2,
            "fltt": 1,
            "fields": fields,
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": int(time.time() * 1000)  # 当前时间戳
        }
        
        # 发送请求
        try:
            response = requests.get(base_url, params=params, timeout=5)
            response.raise_for_status()
            json_data = response.json()
            
            # 检查API返回的有效性
            if json_data.get("rc") != 0 or "data" not in json_data:
                return {}
                
            data = json_data["data"]
        except Exception as e:
            print(f"获取股票 {secid} 最新价失败: {e}")
            return {}
        
        # 确保包含必要字段
        if "f43" in data and "f59" in data:
            return float(process_price(data["f43"], data["f59"]))
    
    def get_stock_limit_prices(self):
        """获取股票的涨跌停价"""
        # 构造API参数
        market = "0" if self.stock_code.startswith("sz") else "1"
        secid = f"{market}.{self.stock_code[2:]}"
        
        params = {
            "invt": 2,
            "fltt": 1,
            "fields": "f51,f52,f59",  # 涨停价,跌停价,精度
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": int(time.time() * 1000)
        }
        
        try:
            # 发送请求
            response = requests.get(
                "https://push2.eastmoney.com/api/qt/stock/get",
                params=params,
            )
            response.raise_for_status()
            json_data = response.json()

            print(json_data)
            
            # 解析数据
            if json_data.get("rc") == 0 and "data" in json_data:
                data = json_data["data"]
                precision = data.get("f59", 0)
                
                upper_limit = self._process_price(data.get("f51"), precision)
                lower_limit = self._process_price(data.get("f52"), precision)
                
                return upper_limit, lower_limit
        except Exception as e:
            pass
        
        return 0, 0
    
    def get_stock_data(self): 
        """获取股票详细信息"""
        # 构造API参数
        market = "1" if self.stock_code.startswith("sh") else "0"
        secid = f"{market}.{self.stock_code[2:]}"
        
        # 请求所有必要字段
        fields = "f43,f46,f60,f44,f45,f47,f48,f51,f52,"  # 基础字段
        fields += "f19,f20,f17,f18,f15,f16,f13,f14,f11,f12,"  # 买盘五档
        fields += "f39,f40,f37,f38,f35,f36,f33,f34,f31,f32,"  # 卖盘五档
        fields += "f58,f59,f60,f531"  # 名称和精度
        
        params = {
            "invt": 2,
            "fltt": 1,
            "fields": fields,
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": int(time.time() * 1000)
        }
        
        try:
            # 发送请求
            response = requests.get(
                "https://push2.eastmoney.com/api/qt/stock/get",
                params=params,
            )
            response.raise_for_status()
            json_data = response.json()
            print(json_data)
            
            # 解析数据
            if json_data.get("rc") == 0 and "data" in json_data:
                data = json_data["data"]
                precision = data.get("f59", 0)
                
                # 基础价格数据
                current_price = self._process_price(data.get("f43"), precision)
                open_price = self._process_price(data.get("f46"), precision)
                prev_close = self._process_price(data.get("f60"), precision)
                high_price = self._process_price(data.get("f44"), precision)
                low_price = self._process_price(data.get("f45"), precision)
                volume = self._process_volume(data.get("f47", 0))
                amount = self._process_volume(data.get("f48", 0))
                upper_limit = self._process_price(data.get("f51"), precision)
                lower_limit = self._process_price(data.get("f52"), precision)
                
                # 计算涨跌幅
                change = round(current_price - prev_close, 2) if all(p is not None for p in [current_price, prev_close]) else 0
                change_percent = round((change / prev_close) * 100, 2) if prev_close and prev_close != 0 else 0
                
                # 五档买盘
                bid_prices = [
                    self._process_price(data.get("f19"), precision),  # 买一价
                    self._process_price(data.get("f17"), precision),  # 买二价
                    self._process_price(data.get("f15"), precision),  # 买三价
                    self._process_price(data.get("f13"), precision),  # 买四价
                    self._process_price(data.get("f11"), precision)   # 买五价
                ]
                bid_volumes = [
                    self._process_volume(data.get("f20")),  # 买一量
                    self._process_volume(data.get("f18")),  # 买二量
                    self._process_volume(data.get("f16")),  # 买三量
                    self._process_volume(data.get("f14")),  # 买四量
                    self._process_volume(data.get("f12"))   # 买五量
                ]
                
                # 五档卖盘
                ask_prices = [
                    self._process_price(data.get("f39"), precision),  # 卖一价
                    self._process_price(data.get("f37"), precision),  # 卖二价
                    self._process_price(data.get("f35"), precision),  # 卖三价
                    self._process_price(data.get("f33"), precision),  # 卖四价
                    self._process_price(data.get("f31"), precision)   # 卖五价
                ]
                ask_volumes = [
                    self._process_volume(data.get("f40")),  # 卖一量
                    self._process_volume(data.get("f38")),  # 卖二量
                    self._process_volume(data.get("f36")),  # 卖三量
                    self._process_volume(data.get("f34")),  # 卖四量
                    self._process_volume(data.get("f32"))   # 卖五量
                ]
                
                # 股票名称
                name = data.get("f58", f"股票{self.stock_code[-4:]}")
                
                # 构建结果字典
                result = {
                    "code": self.stock_code,
                    "name": name,
                    "current": current_price,
                    "open": open_price,
                    "prev_close": prev_close,
                    "high": high_price,
                    "low": low_price,
                    "volume": volume,
                    "amount": amount,
                    "upper_limit": upper_limit,
                    "lower_limit": lower_limit,
                    "change": change,
                    "change_percent": change_percent,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    # 五档买盘
                    "bid1": bid_prices[0],
                    "bid1_vol": bid_volumes[0],
                    "bid2": bid_prices[1],
                    "bid2_vol": bid_volumes[1],
                    "bid3": bid_prices[2],
                    "bid3_vol": bid_volumes[2],
                    "bid4": bid_prices[3],
                    "bid4_vol": bid_volumes[3],
                    "bid5": bid_prices[4],
                    "bid5_vol": bid_volumes[4],
                    # 五档卖盘
                    "ask1": ask_prices[0],
                    "ask1_vol": ask_volumes[0],
                    "ask2": ask_prices[1],
                    "ask2_vol": ask_volumes[1],
                    "ask3": ask_prices[2],
                    "ask3_vol": ask_volumes[2],
                    "ask4": ask_prices[3],
                    "ask4_vol": ask_volumes[3],
                    "ask5": ask_prices[4],
                    "ask5_vol": ask_volumes[4]
                }
                
                return result
        except Exception as e:
            print(f"获取股票数据失败: {e}")
        
        # 失败时返回默认结构
        return None