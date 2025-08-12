// 全局变量
let currentStock = 'sh600519';
let portfolioData = [];
let ordersData = [];
let historyData = [];
let equityChart = null;
// 全局分页变量
let currentPage = 1;
const ordersPerPage = 100; // 每页显示15条订单
let currentPositionPage = 1;
const positionsPerPage = 100;
let currentHistoryPage = 1;
const historyPerPage = 100;

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initPage();
    
    // 设置定时器
    setInterval(updateClock, 1000);
    setInterval(updateTradingPhase, 5000);
    setInterval(updateStockData, 5000);
    setInterval(updatePortfolio, 10000);
    setInterval(updateOrders, 10000);
    setInterval(updateHistory, 10000);
    
    // 事件监听
    document.getElementById('search-stock').addEventListener('click', searchStock);
    document.getElementById('buy-btn').addEventListener('click', buyStock);
    document.getElementById('sell-btn').addEventListener('click', sellStock);
    
    document.querySelectorAll('.sample-stocks button').forEach(button => {
        button.addEventListener('click', function() {
            currentStock = this.dataset.code;
            document.getElementById('stock-code').value = currentStock;
            searchStock();
        });
    });
    
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            // 移除所有active类
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            
            // 添加active类到当前标签
            this.classList.add('active');
            
            // 显示对应的面板
            const panelId = `${this.dataset.tab}-panel`;
            document.getElementById(panelId).classList.add('active');
        });
    });

    // 分页事件监听
    document.getElementById('prev-page').addEventListener('click', function() {
        if (currentPage > 1) {
            currentPage--;
            updateOrders();
        }
    });
    
    document.getElementById('next-page').addEventListener('click', function() {
        currentPage++;
        updateOrders();
    });
    
    // 订单搜索
    document.getElementById('search-orders').addEventListener('click', function() {
        currentPage = 1;
        updateOrders();
    });
    
    document.getElementById('order-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            currentPage = 1;
            updateOrders();
        }
    });

    // 持仓分页事件监听
    document.getElementById('position-prev').addEventListener('click', function() {
        if (currentPositionPage > 1) {
            currentPositionPage--;
            updatePortfolio();
        }
    });
    
    document.getElementById('position-next').addEventListener('click', function() {
        currentPositionPage++;
        updatePortfolio();
    });
    
    // 持仓搜索
    document.getElementById('search-positions').addEventListener('click', function() {
        currentPositionPage = 1;
        updatePortfolio();
    });
    
    document.getElementById('position-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            currentPositionPage = 1;
            updatePortfolio();
        }
    });

    // 历史分页事件监听
    document.getElementById('history-prev').addEventListener('click', function() {
        if (currentHistoryPage > 1) {
            currentHistoryPage--;
            updateHistory();
        }
    });
    
    document.getElementById('history-next').addEventListener('click', function() {
        currentHistoryPage++;
        updateHistory();
    });
    
    // 历史搜索
    document.getElementById('search-history').addEventListener('click', function() {
        currentHistoryPage = 1;
        updateHistory();
    });
    
    document.getElementById('history-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            currentHistoryPage = 1;
            updateHistory();
        }
    });

    // 事件委托处理撤单按钮
    document.getElementById('orders-body').addEventListener('click', function(e) {
        if (e.target.classList.contains('cancel-order') || e.target.closest('.cancel-order')) {
            const button = e.target.classList.contains('cancel-order') ? e.target : e.target.closest('.cancel-order');
            const orderId = button.dataset.id;
            cancelOrder(orderId);
        }
    });
});

// 初始化页面
function initPage() {
    updateClock();
    updateTradingPhase();
    searchStock();
    updatePortfolio();
    updateOrders();
    updateHistory();
    initEquityChart();
}

function initEquityChart() {
    const ctx = document.getElementById('equity-chart').getContext('2d');
    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '总资产',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                pointRadius: 3,
                pointBackgroundColor: '#3b82f6',
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#e2e8f0'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(30, 41, 59, 0.9)',
                    titleColor: '#e2e8f0',
                    bodyColor: '#e2e8f0',
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return `¥${context.raw.toLocaleString('zh-CN')}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value) {
                            return '¥' + value.toLocaleString('zh-CN', {maximumFractionDigits: 0});
                        }
                    },
                    beginAtZero: false
                }
            }
        }
    });
}

// 更新时钟
function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerHTML = `<i class="fas fa-clock"></i> <b>${now.toLocaleString('zh-CN')}</b>`;
}

// 更新交易阶段
function updateTradingPhase() {
    fetch('/api/trading_phase')
        .then(response => response.json())
        .then(data => {
            const phaseNames = {
                "pre_open": "开盘集合竞价(可撤单)",
                "open_call_no_cancel": "开盘集合竞价(不可撤单)",
                "open_call": "开盘集合竞价",
                "continuous_am": "早盘连续竞价",
                "break": "午间休市",
                "continuous_pm": "午盘连续竞价",
                "close_call": "收盘集合竞价",
                "post_market": "盘后交易",
                "non_trading": "非交易日",
                "closed": "闭市"
            };
            
            const phaseText = phaseNames[data.phase] || "未知交易阶段";
            const phaseElement = document.getElementById('trading-phase');
            phaseElement.innerHTML = `<i class="fas fa-exchange-alt"></i> <b>交易阶段: ${phaseText}</b>`;
            
            // 根据交易阶段改变颜色
            if (data.phase.includes('continuous')) {
                phaseElement.style.backgroundColor = '#10b981';
            } else if (data.phase === 'non_trading' || data.phase === 'closed') {
                phaseElement.style.backgroundColor = '#64748b';
            } else {
                phaseElement.style.backgroundColor = '#f59e0b';
            }
        })
        .catch(error => {
            console.error('获取交易阶段失败:', error);
        });
}

// 查询股票数据
function searchStock() {
    const stockCode = document.getElementById('stock-code').value.trim();
    if (!stockCode) {
        setStatusMessage('错误: 股票代码不能为空', 'error');
        return;
    }
    
    setStatusMessage(`正在获取 ${stockCode} 股票数据...`, 'info');
    
    fetch(`/api/stock/${stockCode}`)
        .then(response => response.json())
        .then(data => {
            if (Object.keys(data).length === 0) {
                setStatusMessage(`获取股票 ${stockCode} 数据失败`, 'error');
                return;
            }
            
            currentStock = stockCode;
            updateStockDisplay(data);
            setStatusMessage(`成功获取 ${data.name} 数据`, 'success');
            
            // 更新价格输入框
            document.getElementById('trade-price').value = data.current.toFixed(2);
        })
        .catch(error => {
            console.error('获取股票数据失败:', error);
            setStatusMessage(`获取数据时出错: ${error.message}`, 'error');
        });
}

// 更新股票数据显示
function updateStockDisplay(data) {
    document.getElementById('stock-name').innerHTML = `<i class="fas fa-chart-bar"></i> ${data.name} (${data.code.toUpperCase()})`;
    document.getElementById('current-price').textContent = data.current.toFixed(2);
    
    const change = data.current - data.prev_close;
    const changePercent = (change / data.prev_close) * 100;
    
    const priceChangeElement = document.getElementById('price-change');
    priceChangeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePercent.toFixed(2)}%)`;
    priceChangeElement.className = change >= 0 ? 'price-up' : 'price-down';
    
    // 基础数据
    document.getElementById('open-price').textContent = data.open.toFixed(2);
    document.getElementById('prev-close').textContent = data.prev_close.toFixed(2);
    document.getElementById('high-price').textContent = data.high.toFixed(2);
    document.getElementById('low-price').textContent = data.low.toFixed(2);
    document.getElementById('volume').textContent = data.volume.toLocaleString();
    document.getElementById('amount').textContent = formatCurrency(data.amount, false, true);
    
    // 买卖盘数据
    document.getElementById('bid1-price').textContent = data.bid1.toFixed(2);
    document.getElementById('bid1-vol').textContent = data.bid1_vol.toLocaleString();
    document.getElementById('bid2-price').textContent = data.bid2.toFixed(2);
    document.getElementById('bid2-vol').textContent = data.bid2_vol.toLocaleString();
    document.getElementById('bid3-price').textContent = data.bid3.toFixed(2);
    document.getElementById('bid3-vol').textContent = data.bid3_vol.toLocaleString();
    document.getElementById('bid4-price').textContent = data.bid4.toFixed(2);
    document.getElementById('bid4-vol').textContent = data.bid4_vol.toLocaleString();
    document.getElementById('bid5-price').textContent = data.bid5.toFixed(2);
    document.getElementById('bid5-vol').textContent = data.bid5_vol.toLocaleString();
    
    document.getElementById('ask1-price').textContent = data.ask1.toFixed(2);
    document.getElementById('ask1-vol').textContent = data.ask1_vol.toLocaleString();
    document.getElementById('ask2-price').textContent = data.ask2.toFixed(2);
    document.getElementById('ask2-vol').textContent = data.ask2_vol.toLocaleString();
    document.getElementById('ask3-price').textContent = data.ask3.toFixed(2);
    document.getElementById('ask3-vol').textContent = data.ask3_vol.toLocaleString();
    document.getElementById('ask4-price').textContent = data.ask4.toFixed(2);
    document.getElementById('ask4-vol').textContent = data.ask4_vol.toLocaleString();
    document.getElementById('ask5-price').textContent = data.ask5.toFixed(2);
    document.getElementById('ask5-vol').textContent = data.ask5_vol.toLocaleString();
}

// 更新股票数据
function updateStockData() {
    if (!currentStock) return;
    
    fetch(`/api/stock/${currentStock}`)
        .then(response => response.json())
        .then(data => {
            if (Object.keys(data).length > 0) {
                updateStockDisplay(data);
            }
        })
        .catch(error => {
            console.error('更新股票数据失败:', error);
        });
}

// 买入股票
function buyStock() {
    const price = parseFloat(document.getElementById('trade-price').value);
    const quantity = parseInt(document.getElementById('trade-quantity').value);
    
    if (!price || price <= 0) {
        setStatusMessage('错误: 价格必须大于0', 'error');
        return;
    }
    
    if (!quantity || quantity <= 0) {
        setStatusMessage('错误: 数量必须大于0', 'error');
        return;
    }
    
    // 转换为股数 (1手 = 100股)
    const shares = quantity * 100;
    
    setStatusMessage('正在执行买入操作...', 'info');
    
    fetch('/api/buy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            stock: currentStock,
            price: price,
            quantity: shares
        })
    })
    .then(response => response.json())
    .then(data => {
        setStatusMessage(data.message, data.success ? 'success' : 'error');
        if (data.success) {
            // 手动刷新数据
            updatePortfolio();
            updateOrders();
            updateHistory();
        }
    })
    .catch(error => {
        console.error('买入操作失败:', error);
        setStatusMessage('买入操作失败', 'error');
    });
}

// 卖出股票
function sellStock() {
    const price = parseFloat(document.getElementById('trade-price').value);
    const quantity = parseInt(document.getElementById('trade-quantity').value);
    
    if (!price || price <= 0) {
        setStatusMessage('错误: 价格必须大于0', 'error');
        return;
    }
    
    if (!quantity || quantity <= 0) {
        setStatusMessage('错误: 数量必须大于0', 'error');
        return;
    }
    
    // 转换为股数 (1手 = 100股)
    const shares = quantity * 100;
    
    setStatusMessage('正在执行卖出操作...', 'info');
    
    fetch('/api/sell', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            stock: currentStock,
            price: price,
            quantity: shares
        })
    })
    .then(response => response.json())
    .then(data => {
        setStatusMessage(data.message, data.success ? 'success' : 'error');
        if (data.success) {
            // 手动刷新数据
            updatePortfolio();
            updateOrders();
            updateHistory();
        }
    })
    .catch(error => {
        console.error('卖出操作失败:', error);
        setStatusMessage('卖出操作失败', 'error');
    });
}

// 更新投资组合
function updatePortfolio() {
    const searchTerm = document.getElementById('position-search').value.toLowerCase();
    
    fetch('/api/portfolio')
        .then(response => response.json())
        .then(data => {
            // 更新账户信息
            document.getElementById('total-assets').textContent = 
                formatCurrency(data.total_assets);
            document.getElementById('stock-value').textContent = 
                formatCurrency(data.stock_value);
            
            const totalProfit = data.total_profit;
            const todayProfit = data.today_profit;
            
            document.getElementById('total-profit').textContent = 
                formatCurrency(totalProfit, true);
            document.getElementById('total-profit').className = 
                totalProfit >= 0 ? 'profit-up' : 'profit-down';
            
            document.getElementById('today-profit').textContent = 
                formatCurrency(todayProfit, true);
            document.getElementById('today-profit').className = 
                todayProfit >= 0 ? 'profit-up' : 'profit-down';
            
            // 更新资金曲线图
            updateEquityChart(data.equity_history);
            
            // 更新持仓表格
            const portfolioBody = document.getElementById('portfolio-body');
            portfolioBody.innerHTML = '';

            // 应用搜索过滤
            let positions = [];
            if (data.positions && Object.keys(data.positions).length > 0) {
                for (const [stock, positionInfo] of Object.entries(data.positions)) {
                    // 添加过滤条件：只显示持仓数量大于0的股票
                    if (positionInfo.quantity <= 0) continue;
                    
                    // 检查搜索条件
                    const stockUpper = stock.toUpperCase();
                    const matchSearch = !searchTerm || 
                        stockUpper.includes(searchTerm) || 
                        (positionInfo.buy_date && positionInfo.buy_date.toLowerCase().includes(searchTerm));
                    
                    if (matchSearch) {
                        positions.push({
                            stock: stockUpper,
                            quantity: positionInfo.quantity,
                            avgCost: positionInfo.avg_cost,
                            currentPrice: positionInfo.current_price,
                            marketValue: positionInfo.market_value,
                            profit: positionInfo.profit,
                            buyDate: positionInfo.buy_date
                        });
                    }
                }
            }
            
            // 计算分页
            const totalPages = Math.ceil(positions.length / positionsPerPage);
            if (currentPositionPage > totalPages && totalPages > 0) {
                currentPositionPage = totalPages;
            }
            
            // 更新分页信息
            document.getElementById('position-page-info').textContent = 
                `第${Math.max(1, currentPositionPage)}页/共${Math.max(1, totalPages)}页`;
            
            // 获取当前页数据
            const startIndex = (currentPositionPage - 1) * positionsPerPage;
            const endIndex = Math.min(startIndex + positionsPerPage, positions.length);
            const pagePositions = positions.slice(startIndex, endIndex);
            
            // 渲染持仓表格
            if (pagePositions.length > 0) {
                pagePositions.forEach((position, index) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${position.stock}</td>
                        <td>${position.quantity.toLocaleString()}</td>
                        <td>${position.avgCost.toFixed(2)}</td>
                        <td>${position.currentPrice.toFixed(2)}</td>
                        <td>${formatCurrency(position.marketValue)}</td>
                        <td class="${position.profit >= 0 ? 'profit-up' : 'profit-down'}">
                            ${formatCurrency(position.profit, true)}
                        </td>
                        <td>${position.buyDate}</td>
                    `;
                    
                    if (index % 2 === 0) {
                        row.classList.add('alt-row');
                    }
                    
                    portfolioBody.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="7" class="no-data">无持仓</td>';
                portfolioBody.appendChild(row);
            }
            
            // 更新分页按钮状态
            document.getElementById('position-prev').disabled = currentPositionPage <= 1;
            document.getElementById('position-next').disabled = currentPositionPage >= totalPages;
        })
        .catch(error => {
            console.error('获取投资组合失败:', error);
        });
}

// 更新订单
function updateOrders() {
    const searchTerm = document.getElementById('order-search').value.toLowerCase();
    
    fetch('/api/orders')
        .then(response => response.json())
        .then(data => {
            ordersData = data;
            
            // 应用搜索过滤
            let filteredOrders = ordersData;
            if (searchTerm) {
                filteredOrders = ordersData.filter(order => 
                    order.order_id.toLowerCase().includes(searchTerm) ||
                    order.stock.toLowerCase().includes(searchTerm) ||
                    order.type.includes(searchTerm) ||
                    order.status.toLowerCase().includes(searchTerm)
                );
            }
            
            // 计算分页
            const totalPages = Math.ceil(filteredOrders.length / ordersPerPage);
            if (currentPage > totalPages && totalPages > 0) {
                currentPage = totalPages;
            }
            
            // 更新分页信息
            document.getElementById('page-info').textContent = 
                `第${Math.max(1, currentPage)}页/共${Math.max(1, totalPages)}页`;
            
            // 获取当前页数据
            const startIndex = (currentPage - 1) * ordersPerPage;
            const endIndex = Math.min(startIndex + ordersPerPage, filteredOrders.length);
            const pageOrders = filteredOrders.slice(startIndex, endIndex);
            
            // 渲染订单表格
            const ordersBody = document.getElementById('orders-body');
            ordersBody.innerHTML = '';
            
            if (pageOrders.length > 0) {
                pageOrders.forEach((order, index) => {
                    const row = document.createElement('tr');
                    
                    let statusClass = '';
                    switch (order.status) {
                        case 'pending':
                            statusClass = 'status-pending';
                            break;
                        case 'filled':
                            statusClass = 'status-filled';
                            break;
                        case 'canceled':
                        case 'expired':
                            statusClass = 'status-canceled';
                            break;
                    }
                    
                    row.innerHTML = `
                        <td class="order-id">${order.order_id.substring(0, 8)}...</td>
                        <td class="${order.type === '买入' ? 'type-buy' : 'type-sell'}">${order.type}</td>
                        <td>${order.stock.toUpperCase()}</td>
                        <td>${parseFloat(order.price).toFixed(2)}</td>
                        <td>${parseInt(order.quantity).toLocaleString()}</td>
                        <td class="${statusClass}">${order.status}</td>
                        <td>${order.created_at}</td>
                        <td>
                            ${order.status === 'pending' ? 
                                `<button class="cancel-order" data-id="${order.order_id}"><i class="fas fa-times-circle"></i> 撤单</button>` : 
                                ''}
                        </td>
                    `;
                    
                    if (index % 2 === 0) {
                        row.classList.add('alt-row');
                    }
                    
                    ordersBody.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="8" class="no-data">无订单</td>';
                ordersBody.appendChild(row);
            }
            
            // 更新分页按钮状态
            document.getElementById('prev-page').disabled = currentPage <= 1;
            document.getElementById('next-page').disabled = currentPage >= totalPages;
        })
        .catch(error => {
            console.error('获取订单失败:', error);
        });
}

// 取消订单
function cancelOrder(orderId) {
    setStatusMessage('正在取消订单...', 'info');
    
    fetch('/api/cancel_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            order_id: orderId
        })
    })
    .then(response => response.json())
    .then(data => {
        setStatusMessage(data.message, data.success ? 'success' : 'error');
        if (data.success) {
            updateOrders();
            updatePortfolio(); // 更新持仓以显示解冻的股票
        }
    })
    .catch(error => {
        console.error('取消订单失败:', error);
        setStatusMessage('取消订单失败', 'error');
    });
}

// 更新交易历史
function updateHistory() {
    const searchTerm = document.getElementById('history-search').value.toLowerCase();
    
    fetch('/api/history')
        .then(response => response.json())
        .then(data => {
            historyData = data;
            
            // 应用搜索过滤
            let filteredHistory = historyData;
            if (searchTerm) {
                filteredHistory = historyData.filter(trade => 
                    trade.stock.toLowerCase().includes(searchTerm) ||
                    trade.type.includes(searchTerm) ||
                    trade.datetime.toLowerCase().includes(searchTerm) ||
                    (trade.profit && trade.profit.toString().includes(searchTerm))
                );
            }
            
            // 计算分页
            const totalPages = Math.ceil(filteredHistory.length / historyPerPage);
            if (currentHistoryPage > totalPages && totalPages > 0) {
                currentHistoryPage = totalPages;
            }
            
            // 更新分页信息
            document.getElementById('history-page-info').textContent = 
                `第${Math.max(1, currentHistoryPage)}页/共${Math.max(1, totalPages)}页`;
            
            // 获取当前页数据
            const startIndex = (currentHistoryPage - 1) * historyPerPage;
            const endIndex = Math.min(startIndex + historyPerPage, filteredHistory.length);
            const pageHistory = filteredHistory.slice(startIndex, endIndex);
            
            // 渲染历史表格
            const historyBody = document.getElementById('history-body');
            historyBody.innerHTML = '';
            
            if (pageHistory.length > 0) {
                pageHistory.forEach((trade, index) => {
                    // 修复：确保profit存在且是数字
                    const profit = trade.profit || 0;
                    const profitClass = profit >= 0 ? 'profit-up' : 'profit-down';
                    
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${trade.datetime}</td>
                        <td class="${trade.type === '买入' ? 'type-buy' : 'type-sell'}">${trade.type}</td>
                        <td>${trade.stock.toUpperCase()}</td>
                        <td>${parseFloat(trade.price).toFixed(2)}</td>
                        <td>${parseInt(trade.quantity).toLocaleString()}</td>
                        <td>${formatCurrency(trade.amount)}</td>
                        <td class="${profitClass}">${formatCurrency(profit, true)}</td>
                    `;
                    
                    if (index % 2 === 0) {
                        row.classList.add('alt-row');
                    }
                    
                    historyBody.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="7" class="no-data">无交易记录</td>';
                historyBody.appendChild(row);
            }
            
            // 更新分页按钮状态
            document.getElementById('history-prev').disabled = currentHistoryPage <= 1;
            document.getElementById('history-next').disabled = currentHistoryPage >= totalPages;
        })
        .catch(error => {
            console.error('获取交易历史失败:', error);
        });
}

// 更新资金曲线图
function updateEquityChart(equityData) {
    if (!equityChart || !equityData || equityData.length === 0) return;
    
    // 提取标签和数据
    const labels = equityData.map(item => {
        const date = new Date(item.timestamp);
        return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
    });
    
    const data = equityData.map(item => item.total_assets);
    
    // 更新图表
    equityChart.data.labels = labels;
    equityChart.data.datasets[0].data = data;
    equityChart.update();
}

// 设置状态消息
function setStatusMessage(message, type = 'info') {
    const statusElement = document.getElementById('status-message');
    
    switch (type) {
        case 'success':
            statusElement.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
            statusElement.className = 'status-success';
            break;
        case 'error':
            statusElement.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
            statusElement.className = 'status-error';
            break;
        case 'warning':
            statusElement.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
            statusElement.className = 'status-warning';
            break;
        default:
            statusElement.innerHTML = `<i class="fas fa-info-circle"></i> ${message}`;
            statusElement.className = 'status-info';
    }
}

// 格式化货币
function formatCurrency(amount, showSign = false, skipSymbol = false) {
    if (amount === undefined || amount === null) return '¥0.00';
    
    const sign = showSign && amount > 0 ? '+' : '';
    const symbol = skipSymbol ? '' : '¥';
    
    // 处理负数
    const absAmount = Math.abs(amount);
    
    return sign + symbol + absAmount.toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}