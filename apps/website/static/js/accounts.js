// CTOS 账户管理 JavaScript

class AccountsManager {
    constructor() {
        this.autoRefreshInterval = null;
        this.refreshInterval = 30000; // 30秒
        this.init();
    }

    init() {
        this.bindEvents();
        this.calculateSummary();
    }

    bindEvents() {
        // 交易所选择器
        const exchangeSelect = document.getElementById('exchange-select');
        if (exchangeSelect) {
            exchangeSelect.addEventListener('change', (e) => {
                this.filterByExchange(e.target.value);
            });
        }

        // 刷新按钮
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshAllAccounts();
            });
        }

        // 自动刷新复选框
        const autoRefreshCheckbox = document.getElementById('auto-refresh-checkbox');
        if (autoRefreshCheckbox) {
            autoRefreshCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // 单个账户刷新按钮
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('refresh-single')) {
                const exchange = e.target.dataset.exchange;
                const accountId = e.target.dataset.accountId;
                this.refreshSingleAccount(exchange, accountId, e.target);
            }
        });
    }

    filterByExchange(exchange) {
        const rows = document.querySelectorAll('.account-row');
        rows.forEach(row => {
            if (!exchange || row.dataset.exchange === exchange) {
                row.classList.remove('hidden');
            } else {
                row.classList.add('hidden');
            }
        });
        this.calculateSummary();
    }

    async refreshAllAccounts() {
        const refreshBtn = document.getElementById('refresh-btn');
        const refreshIcon = refreshBtn.querySelector('.refresh-icon');
        
        // 显示加载状态
        refreshBtn.disabled = true;
        refreshIcon.style.animation = 'spin 1s linear infinite';
        
        try {
            const response = await fetch('/accounts/api/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateAccountsTable(data.accounts);
                this.showNotification('账户信息刷新成功', 'success');
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

    async refreshSingleAccount(exchange, accountId, button) {
        const originalText = button.textContent;
        button.textContent = '刷新中...';
        button.disabled = true;

        try {
            const response = await fetch('/accounts/api/balance/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    exchange: exchange,
                    account_id: accountId
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateSingleAccountBalance(exchange, accountId, data.balance);
                this.showNotification(`${exchange.toUpperCase()} 账户 ${accountId} 余额刷新成功`, 'success');
            } else {
                this.showNotification(`刷新失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`网络错误: ${error.message}`, 'error');
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    updateAccountsTable(accounts) {
        const tbody = document.getElementById('accounts-tbody');
        if (!tbody) return;

        // 清空现有内容
        tbody.innerHTML = '';

        // 重新生成表格行
        accounts.forEach(acc => {
            const row = this.createAccountRow(acc);
            tbody.appendChild(row);
        });

        this.calculateSummary();
    }

    createAccountRow(acc) {
        const row = document.createElement('tr');
        row.className = 'account-row';
        row.dataset.exchange = acc.exchange;
        row.dataset.accountId = acc.account_id;

        const statusClass = acc.status === '正常' ? '正常' : 
                           acc.status.includes('错误') ? '错误' : '未知';

        row.innerHTML = `
            <td class="exchange-cell">
                <span class="exchange-badge exchange-${acc.exchange}">${acc.exchange.toUpperCase()}</span>
            </td>
            <td class="account-name">${acc.account_name}</td>
            <td class="account-id">${acc.account_id}</td>
            <td class="balance-cell">
                <span class="balance-value" data-balance="${acc.balance}">
                    ${parseFloat(acc.balance).toFixed(2)}
                </span>
            </td>
            <td class="status-cell">
                <span class="status-badge status-${statusClass}">
                    ${acc.status}
                </span>
            </td>
            <td class="config-cell">
                <span class="config-badge config-${acc.credentials_configured ? 'ok' : 'error'}">
                    ${acc.credentials_configured ? '✓ 已配置' : '✗ 未配置'}
                </span>
            </td>
            <td class="actions-cell">
                <button class="btn btn-small refresh-single" 
                        data-exchange="${acc.exchange}" 
                        data-account-id="${acc.account_id}">
                    刷新
                </button>
            </td>
        `;

        return row;
    }

    updateSingleAccountBalance(exchange, accountId, balance) {
        const row = document.querySelector(`tr[data-exchange="${exchange}"][data-account-id="${accountId}"]`);
        if (row) {
            const balanceElement = row.querySelector('.balance-value');
            if (balanceElement) {
                // 添加更新动画
                balanceElement.classList.add('updating');
                
                setTimeout(() => {
                    balanceElement.textContent = parseFloat(balance).toFixed(2);
                    balanceElement.dataset.balance = balance;
                    balanceElement.classList.remove('updating');
                }, 500);
            }
        }
        this.calculateSummary();
    }

    calculateSummary() {
        const visibleRows = document.querySelectorAll('.account-row:not(.hidden)');
        const totalAccounts = visibleRows.length;
        
        let totalBalance = 0;
        let healthyAccounts = 0;

        visibleRows.forEach(row => {
            const balanceElement = row.querySelector('.balance-value');
            const statusElement = row.querySelector('.status-badge');
            
            if (balanceElement) {
                const balance = parseFloat(balanceElement.dataset.balance) || 0;
                totalBalance += balance;
            }
            
            if (statusElement && statusElement.textContent.trim() === '正常') {
                healthyAccounts++;
            }
        });

        // 更新摘要
        const totalAccountsElement = document.getElementById('total-accounts');
        const totalBalanceElement = document.getElementById('total-balance');
        const healthyAccountsElement = document.getElementById('healthy-accounts');

        if (totalAccountsElement) {
            totalAccountsElement.textContent = totalAccounts;
        }
        if (totalBalanceElement) {
            totalBalanceElement.textContent = `${totalBalance.toFixed(2)} USDT`;
        }
        if (healthyAccountsElement) {
            healthyAccountsElement.textContent = healthyAccounts;
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh(); // 确保没有重复的定时器
        this.autoRefreshInterval = setInterval(() => {
            this.refreshAllAccounts();
        }, this.refreshInterval);
        
        this.showNotification(`自动刷新已启动 (${this.refreshInterval/1000}秒间隔)`, 'info');
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            this.showNotification('自动刷新已停止', 'info');
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
    new AccountsManager();
});
