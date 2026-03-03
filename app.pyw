from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from trading_api import TradingAPI
import threading
import datetime
import os
import sys
import atexit
import tkinter as tk
from tkinter import messagebox
import webbrowser


app = Flask(__name__)
CORS(app)

# 创建交易API实例
trading_api = TradingAPI(initial_cash=100000.0)

# 全局变量，用于控制服务器状态
server_running = True
server_thread = None

def run_trading_engine():
    """运行交易引擎，定期处理挂单"""
    while True:
        trading_api.process_pending_orders()
        # 每1秒处理一次挂单
        threading.Event().wait(1)

def run_server():
    """运行服务器"""
    app.name = "StockApp"
    app.run(host='0.0.0.0', port=5000, debug=False)

def create_control_window():
    """创建控制窗口"""
    def on_closing():
        """关闭服务器和窗口"""
        global server_running
        if messagebox.askokcancel("关闭服务器", "确定要关闭整个交易系统吗?"):
            server_running = False
            root.destroy()
            # 强制退出所有线程
            os._exit(0)
    
    def open_browser():
        """在浏览器中打开应用"""
        webbrowser.open('http://127.0.0.1:5000')
    
    # 创建主窗口
    root = tk.Tk()
    root.title("股票交易系统控制面板")
    
    # 设置窗口大小并固定（不能全屏）
    root.geometry("320x320")
    root.resizable(False, False)  # 禁止调整大小
    
    # 尝试设置窗口图标
    try:
        # 使用内置图标（可以使用其他图标）
        root.iconbitmap(default='')  # 清除默认图标
        root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file='icon.ico'))
    except:
        # 如果找不到图标文件，使用默认图标
        pass
    
    # 禁用窗口关闭按钮
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    
    # 添加标题
    title_label = tk.Label(
        root, 
        text="股票交易系统控制面板",
        font=("黑体", 14, "bold"),
        fg="#2c3e50",
        pady=10
    )
    title_label.pack()
    
    # 添加分隔线
    separator = tk.Frame(root, height=2, bd=1, relief="sunken", bg="#bdc3c7")
    separator.pack(fill="x", padx=20, pady=5)
    
    # 添加控制按钮框架
    button_frame = tk.Frame(root)
    button_frame.pack(pady=15)
    
    # 打开浏览器按钮
    browser_btn = tk.Button(
        button_frame, 
        text="打开浏览器", 
        command=open_browser,
        width=20,
        height=2,
        bg="#3498db",
        fg="white",
        font=("黑体", 10, "bold"),
        activebackground="#2980b9",
        relief="flat"
    )
    browser_btn.pack(pady=10)
    
    # 关闭服务器按钮
    close_btn = tk.Button(
        button_frame, 
        text="关闭服务器", 
        command=on_closing,
        width=20,
        height=2,
        bg="#e74c3c",
        fg="white",
        font=("黑体", 10, "bold"),
        activebackground="#c0392b",
        relief="flat"
    )
    close_btn.pack(pady=10)
    
    # 添加状态区域
    status_frame = tk.LabelFrame(
        root, 
        text="服务器状态",
        font=("黑体", 10, "bold"),
        padx=10,
        pady=10,
        bd=1,
        relief="groove"
    )
    status_frame.pack(fill="x", padx=20, pady=10)
    
    # 状态标签
    status_label = tk.Label(
        status_frame, 
        text="● 运行中",
        font=("黑体", 10),
        fg="#27ae60"
    )
    status_label.pack(anchor="w")
    
    # 状态信息
    info_label = tk.Label(
        status_frame, 
        text=f"服务地址: http://127.0.0.1:5000\n启动时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        font=("黑体", 8),
        fg="#383838",
        justify="left"
    )
    info_label.pack(anchor="w", pady=5)
    
    # 设置窗口居中显示
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'+{x}+{y}')
    
    # 启动Tkinter主循环
    root.mainloop()

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """获取投资组合信息"""
    portfolio = trading_api.generate_report()
    return jsonify(portfolio)

@app.route('/api/stock/<stock_code>', methods=['GET'])
def get_stock_data(stock_code):
    """获取股票数据"""
    data = trading_api.get_stock_data(stock_code)
    return jsonify(data)

@app.route('/api/buy', methods=['POST'])
def buy_stock():
    """买入股票"""
    data = request.json
    stock_code = data.get('stock')
    price = float(data.get('price'))
    quantity = int(data.get('quantity'))
    
    success, message = trading_api.buy(stock_code, price, quantity, datetime.datetime.now())
    return jsonify({'success': success, 'message': message})

@app.route('/api/sell', methods=['POST'])
def sell_stock():
    """卖出股票"""
    data = request.json
    stock_code = data.get('stock')
    price = float(data.get('price'))
    quantity = int(data.get('quantity'))
    
    success, message = trading_api.sell(stock_code, price, quantity, datetime.datetime.now())
    return jsonify({'success': success, 'message': message})

@app.route('/api/cancel_order', methods=['POST'])
def cancel_order():
    """取消订单"""
    data = request.json
    order_id = data.get('order_id')
    
    success, message = trading_api.cancel_order(order_id, datetime.datetime.now())
    return jsonify({'success': success, 'message': message})

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """获取所有订单"""
    orders = trading_api.get_all_orders()
    return jsonify(orders)

@app.route('/api/history', methods=['GET'])
def get_history():
    """获取交易历史"""
    history = trading_api.get_trade_history()
    return jsonify(history)

@app.route('/api/save_state', methods=['POST'])
def save_state():
    """保存状态"""
    success, message = trading_api.save_state()
    return jsonify({'success': success, 'message': message})

@app.route('/api/load_state', methods=['POST'])
def load_state():
    """加载状态"""
    success, message = trading_api.load_state()
    return jsonify({'success': success, 'message': message})

@app.route('/api/trading_phase', methods=['GET'])
def get_trading_phase():
    """获取当前交易阶段"""
    now = datetime.datetime.now()
    phase = trading_api.get_trading_phase(now)
    return jsonify({'phase': phase})

@app.route('/api/equity_history', methods=['GET'])
def get_equity_history():
    """获取资金曲线历史数据"""
    history = trading_api.get_equity_history()
    return jsonify(history)

if __name__ == '__main__':
    # 确保数据目录存在
    os.makedirs('data', exist_ok=True)

    # 启动交易引擎线程
    engine_thread = threading.Thread(target=run_trading_engine, daemon=True)
    engine_thread.start()

    # 启动服务器线程
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    create_control_window()

