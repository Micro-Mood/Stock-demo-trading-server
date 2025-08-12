# 更新为白色主题配色方案
import datetime
import holidays

# 颜色配置（白色主题）
BG_COLOR = "#f5f7fa"          # 浅灰色背景
ACCENT_COLOR = "#3b82f6"       # 强调色 - 蓝色
POSITIVE_COLOR = "#10b981"     # 盈利色 - 绿色
NEGATIVE_COLOR = "#ef4444"     # 亏损色 - 红色
TEXT_COLOR = "#1e293b"         # 文本色 - 深蓝色
WARNING_COLOR = "#f59e0b"      # 警告色 - 琥珀色

# 辅助颜色
HEADER_COLOR = "#ffffff"       # 标题栏颜色 - 白色
BUTTON_BG = "#e2e8f0"          # 按钮背景色
BUTTON_HOVER = "#cbd5e1"       # 按钮悬停色
TABLE_HEADER_BG = "#f1f5f9"    # 表格标题背景
TABLE_ROW_BG = "#ffffff"       # 表格行背景
TABLE_ROW_ALT_BG = "#f8fafc"   # 表格交替行背景
TABLE_SELECTED_BG = "#dbeafe"  # 表格选中行背景
FRAME_BG = "#ffffff"           # 框架背景色
ENTRY_BG = "#ffffff"           # 输入框背景色
ENTRY_FG = "#1e293b"           # 输入框文字颜色
SCROLLBAR_BG = "#cbd5e1"       # 滚动条背景
SCROLLBAR_HOVER = "#94a3b8"    # 滚动条悬停色
TAB_BG = "#f1f5f9"             # 选项卡背景
TAB_SELECTED_BG = "#3b82f6"    # 选中选项卡背景

# 日期时间格式
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# 交易时段规则
TRADING_RULES = {
    "pre_open": {"start": (9, 15), "end": (9, 20), "can_cancel": True},
    "open_call_no_cancel": {"start": (9, 20), "end": (9, 25), "can_cancel": False},
    "open_call": {"start": (9, 25), "end": (9, 30), "can_cancel": False},
    "continuous_am": {"start": (9, 30), "end": (11, 30), "can_cancel": True},
    "break": {"start": (11, 30), "end": (13, 0), "can_cancel": False},
    "continuous_pm": {"start": (13, 0), "end": (14, 57), "can_cancel": True},
    "close_call": {"start": (14, 57), "end": (15, 0), "can_cancel": False},
    "post_market": {"start": (15, 0), "end": (15, 30), "can_cancel": False},
    "non_trading": {"start": (0, 0), "end": (0, 0), "can_cancel": False},
    "closed": {"start": (15, 30), "end": (9, 15), "can_cancel": False}
}

# 中国节假日
cn_holidays = holidays.CountryHoliday('CN')

# #测试用
# def is_trading_day(dt):
#     """检查是否为交易日（跳过周末）"""
#     return True  # 0-4为周一到周五
# #测试用
# def get_trading_phase(dt):
#     """获取当前交易阶段"""
#     return "continuous_am"

def is_trading_day(dt):
    """检查是否为交易日（跳过周末和节假日）"""
    # 周六、周日非交易日
    if dt.weekday() >= 5:
        return False
    
    # 检查是否节假日
    return dt.date() not in cn_holidays

def get_trading_phase(dt):
    """获取当前交易阶段"""
    if not is_trading_day(dt):
        return "non_trading"
    
    t = dt.time()
    
    # 检查所有定义的交易阶段
    for phase, rules in TRADING_RULES.items():
        start_time = datetime.time(rules["start"][0], rules["start"][1])
        end_time = datetime.time(rules["end"][0], rules["end"][1])
        
        # 处理跨天的情况（如闭市时段）
        if start_time > end_time:
            if t >= start_time or t < end_time:
                return phase
        else:
            if start_time <= t < end_time:
                return phase
    
    return "closed"

def calculate_commission(amount, is_buy):
    """计算交易费用"""
    # 买入费用：佣金（最低5元）+ 过户费
    if is_buy:
        commission = max(amount * 0.00025, 5)  # 佣金万2.5，最低5元
        transfer_fee = amount * 0.00001  # 过户费万0.1
        return commission + transfer_fee
    
    # 卖出费用：佣金（最低5元）+ 印花税 + 过户费
    commission = max(amount * 0.00025, 5)  # 佣金万2.5，最低5元
    stamp_duty = amount * 0.001  # 印花税千1
    transfer_fee = amount * 0.00001  # 过户费万0.1
    return commission + stamp_duty + transfer_fee