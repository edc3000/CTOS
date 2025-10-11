// 账户详情页面 JavaScript

class AccountDetailManager {
    constructor() {
        this.accountInfo = window.accountInfo;
        this.positionsRefreshInterval = null;
        this.ordersRefreshInterval = null;
        this.refreshInterval = 30000; // 30秒
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
    }

    bindEvents() {
        // 标签页切换
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // 仓位刷新按钮
        const refreshPositionsBtn = document.getElementById('refresh-positions');
        if (refreshPositionsBtn) {
            refreshPositionsBtn.addEventListener('click', () => {
                this.refreshPositions();
            });
        }

        // 订单刷新按钮
        const refreshOrdersBtn = document.getElementById('refresh-orders');
        if (refreshOrdersBtn) {
            refreshOrdersBtn.addEventListener('click', () => {
                this.refreshOrders();
            });
        }

        // 仓位自动刷新
        const autoRefreshPositionsCheckbox = document.getElementById('auto-refresh-positions');
        if (autoRefreshPositionsCheckbox) {
            autoRefreshPositionsCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefreshPositions();
                } else {
                    this.stopAutoRefreshPositions();
                }
            });
        }

        // 订单自动刷新
        const autoRefreshOrdersCheckbox = document.getElementById('auto-refresh-orders');
        if (autoRefreshOrdersCheckbox) {
            autoRefreshOrdersCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefreshOrders();
                } else {
                    this.stopAutoRefreshOrders();
                }
            });
        }
    }

    switchTab(tabName) {
        // 更新标签按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 更新标签面板状态
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        document.getElementById(`${tabName}-panel`).classList.add('active');

        // 如果切换到仓位标签页且还没有数据，则加载数据
        if (tabName === 'positions' && !this.positionsLoaded) {
            this.refreshPositions();
        }

        // 如果切换到订单标签页且还没有数据，则加载数据
        if (tabName === 'orders' && !this.ordersLoaded) {
            this.refreshOrders();
        }
    }

    loadInitialData() {
        // 默认加载仓位数据
        this.refreshPositions();
    }

    async refreshPositions() {
        const refreshBtn = document.getElementById('refresh-positions');
        const refreshIcon = refreshBtn.querySelector('.refresh-icon');
        
        // 显示加载状态
        refreshBtn.disabled = true;
        refreshIcon.style.animation = 'spin 1s linear infinite';
        
        try {
            const response = await fetch(`/accounts/${this.accountInfo.exchange}/${this.accountInfo.accountId}/api/positions/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.updatePositionsTable(data.positions);
                this.showNotification('仓位信息刷新成功', 'success');
                this.positionsLoaded = true;
            } else {
                this.showNotification(`刷新失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`网络错误: ${error.message}`, 'error');
        } finally {
            // 恢复按钮状态
            refreshBtn.disabled = false;
            refreshIcon.style.animation = '';
        }
    }

    async refreshOrders() {
        const refreshBtn = document.getElementById('refresh-orders');
        const refreshIcon = refreshBtn.querySelector('.refresh-icon');
        
        // 显示加载状态
        refreshBtn.disabled = true;
        refreshIcon.style.animation = 'spin 1s linear infinite';
        
        try {
            const response = await fetch(`/accounts/${this.accountInfo.exchange}/${this.accountInfo.accountId}/api/orders/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateOrdersTable(data.orders);
                this.showNotification('订单信息刷新成功', 'success');
                this.ordersLoaded = true;
            } else {
                this.showNotification(`刷新失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`网络错误: ${error.message}`, 'error');
        } finally {
            // 恢复按钮状态
            refreshBtn.disabled = false;
            refreshIcon.style.animation = '';
        }
    }

    updatePositionsTable(positions) {
        const tbody = document.getElementById('positions-tbody');
        if (!tbody) return;

        // 清空现有内容
        tbody.innerHTML = '';

        if (!positions || positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="no-data">暂无仓位数据</td></tr>';
            return;
        }

        // 重新生成表格行
        positions.forEach(position => {
            const row = this.createPositionRow(position);
            tbody.appendChild(row);
        });
    }

    updateOrdersTable(orders) {
        const tbody = document.getElementById('orders-tbody');
        if (!tbody) return;

        // 清空现有内容
        tbody.innerHTML = '';

        if (!orders || orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="no-data">暂无订单数据</td></tr>';
            return;
        }

        // 重新生成表格行
        orders.forEach(order => {
            const row = this.createOrderRow(order);
            tbody.appendChild(row);
        });
    }

    createPositionRow(position) {
        const row = document.createElement('tr');
        
        // 根据Driver统一格式处理仓位数据
        const symbol = position.symbol || 'N/A';
        const side = position.side || 'flat';
        const quantity = position.quantity || 0;
        const entryPrice = position.entryPrice || 0;
        const markPrice = position.markPrice || 0;
        const unrealizedPnl = position.pnlUnrealized || 0;
        const realizedPnl = position.pnlRealized || 0;
        const leverage = position.leverage || 1;
        const liquidationPrice = position.liquidationPrice || null;

        // 格式化数值
        const formatNumber = (value, decimals = 4) => {
            if (value === null || value === undefined || isNaN(value)) return 'N/A';
            return parseFloat(value).toFixed(decimals);
        };

        // 格式化方向显示
        const formatSide = (side) => {
            if (side === 'long') return '多头';
            if (side === 'short') return '空头';
            if (side === 'flat') return '平仓';
            return side.toUpperCase();
        };

        // 检查是否为有效仓位（数量不为0）
        const isValidPosition = Math.abs(parseFloat(quantity)) > 0.0001;

        row.innerHTML = `
            <td class="symbol-cell">${symbol}</td>
            <td class="side-cell">
                <span class="side-badge side-${side}">${formatSide(side)}</span>
            </td>
            <td class="quantity-cell">${formatNumber(quantity)}</td>
            <td class="entry-price-cell">${isValidPosition ? formatNumber(entryPrice) : 'N/A'}</td>
            <td class="mark-price-cell">${formatNumber(markPrice)}</td>
            <td class="unrealized-pnl-cell ${parseFloat(unrealizedPnl) >= 0 ? 'profit' : 'loss'}">
                ${formatNumber(unrealizedPnl)}
            </td>
            <td class="realized-pnl-cell ${parseFloat(realizedPnl) >= 0 ? 'profit' : 'loss'}">
                ${formatNumber(realizedPnl)}
            </td>
            <td class="leverage-cell">${leverage}x</td>
            <td class="liquidation-price-cell">${isValidPosition ? formatNumber(liquidationPrice) : 'N/A'}</td>
        `;

        return row;
    }

    createOrderRow(order) {
        const row = document.createElement('tr');
        
        // 根据Driver统一格式处理订单数据
        const orderId = order.orderId || 'N/A';
        const symbol = order.symbol || 'N/A';
        const orderType = order.orderType || 'N/A';
        const side = order.side || 'N/A';
        const quantity = order.quantity || 0;
        const price = order.price || 0;
        const status = order.status || 'N/A';
        const createTime = order.createdAt || order.created_at || 'N/A';

        // 格式化数值
        const formatNumber = (value, decimals = 4) => {
            if (value === null || value === undefined || isNaN(value)) return 'N/A';
            return parseFloat(value).toFixed(decimals);
        };

        // 格式化方向显示
        const formatSide = (side) => {
            if (side === 'buy') return '买入';
            if (side === 'sell') return '卖出';
            return side.toUpperCase();
        };

        // 格式化订单类型
        const formatOrderType = (type) => {
            if (type === 'limit') return '限价';
            if (type === 'market') return '市价';
            if (type === 'stop') return '止损';
            if (type === 'stop_limit') return '止损限价';
            return type.toUpperCase();
        };

        // 格式化状态
        const formatStatus = (status) => {
            if (status === 'open' || status === 'active' || status === 'live') return '活跃';
            if (status === 'filled' || status === 'completed') return '已成交';
            if (status === 'cancelled' || status === 'canceled') return '已取消';
            if (status === 'pending') return '待处理';
            return status.toUpperCase();
        };

        row.innerHTML = `
            <td class="order-id-cell">${orderId}</td>
            <td class="symbol-cell">${symbol}</td>
            <td class="order-type-cell">${formatOrderType(orderType)}</td>
            <td class="side-cell">
                <span class="side-badge side-${side}">${formatSide(side)}</span>
            </td>
            <td class="quantity-cell">${formatNumber(quantity)}</td>
            <td class="price-cell">${formatNumber(price)}</td>
            <td class="status-cell">
                <span class="status-badge status-${status.toLowerCase()}">${formatStatus(status)}</span>
            </td>
            <td class="create-time-cell">${this.formatTime(createTime)}</td>
            <td class="actions-cell">
                <button class="btn btn-small btn-danger cancel-order" data-order-id="${orderId}">
                    取消
                </button>
            </td>
        `;

        return row;
    }

    formatTime(timestamp) {
        if (timestamp === 'N/A') return 'N/A';
        
        try {
            const date = new Date(parseInt(timestamp));
            return date.toLocaleString('zh-CN');
        } catch (e) {
            return timestamp;
        }
    }

    startAutoRefreshPositions() {
        this.stopAutoRefreshPositions(); // 确保没有重复的定时器
        this.positionsRefreshInterval = setInterval(() => {
            this.refreshPositions();
        }, this.refreshInterval);
        
        this.showNotification(`仓位自动刷新已启动 (${this.refreshInterval/1000}秒间隔)`, 'info');
    }

    stopAutoRefreshPositions() {
        if (this.positionsRefreshInterval) {
            clearInterval(this.positionsRefreshInterval);
            this.positionsRefreshInterval = null;
            this.showNotification('仓位自动刷新已停止', 'info');
        }
    }

    startAutoRefreshOrders() {
        this.stopAutoRefreshOrders(); // 确保没有重复的定时器
        this.ordersRefreshInterval = setInterval(() => {
            this.refreshOrders();
        }, this.refreshInterval);
        
        this.showNotification(`订单自动刷新已启动 (${this.refreshInterval/1000}秒间隔)`, 'info');
    }

    stopAutoRefreshOrders() {
        if (this.ordersRefreshInterval) {
            clearInterval(this.ordersRefreshInterval);
            this.ordersRefreshInterval = null;
            this.showNotification('订单自动刷新已停止', 'info');
        }
    }

    showNotification(message, type = 'info') {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // 添加样式
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '1rem 1.5rem',
            borderRadius: '5px',
            color: 'white',
            fontWeight: '500',
            zIndex: '1000',
            maxWidth: '300px',
            wordWrap: 'break-word',
            opacity: '0',
            transform: 'translateX(100%)',
            transition: 'all 0.3s ease'
        });

        // 根据类型设置背景色
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            info: '#17a2b8',
            warning: '#ffc107'
        };
        notification.style.backgroundColor = colors[type] || colors.info;

        // 添加到页面
        document.body.appendChild(notification);

        // 显示动画
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);

        // 自动移除
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    getCSRFToken() {
        // 尝试从cookie中获取CSRF token
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        // 如果cookie中没有，尝试从meta标签获取
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        return '';
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new AccountDetailManager();
});
