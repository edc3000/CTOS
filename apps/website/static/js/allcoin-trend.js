// 全币种趋势页面 JavaScript

class AllcoinTrendManager {
    constructor() {
        this.config = window.allcoinTrendConfig;
        this.timeframes = this.config.timeframes;
        this.currentTimeframe = '5m';
        this.autoRefreshInterval = null;
        this.refreshInterval = 10000; // 10秒
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadChart();
        this.startAutoRefresh();
    }

    bindEvents() {
        // 时间框架选择器
        const timeframeSelect = document.getElementById('timeframe-select');
        if (timeframeSelect) {
            timeframeSelect.addEventListener('change', (e) => {
                this.currentTimeframe = e.target.value;
                this.loadChart();
            });
        }

        // 手动刷新按钮
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadChart();
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
    }

    async loadChart() {
        this.showLoading();
        
        try {
            const response = await fetch(`/metrics/${this.config.indicatorId}/api/chart/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    timeframe: this.currentTimeframe
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateChart(data.image_path);
                this.hideLoading();
                this.showNotification('图表加载完成', 'success');
            } else {
                this.showError(data.error);
                this.hideLoading();
                this.showNotification(`加载失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.showError(error.message);
            this.hideLoading();
            this.showNotification(`加载失败: ${error.message}`, 'error');
        }
    }

    updateChart(imagePath) {
        const chartImage = document.getElementById('chart-image');
        const chartTitle = document.getElementById('chart-title');
        const lastUpdate = document.getElementById('last-update');
        
        chartImage.src = imagePath;
        chartTitle.textContent = `全币种趋势 - ${this.currentTimeframe.toUpperCase()}`;
        lastUpdate.textContent = new Date().toLocaleTimeString();
        
        // 图片加载完成后的处理
        chartImage.onload = () => {
            chartImage.style.opacity = '1';
        };
        
        chartImage.onerror = () => {
            this.showError('图片加载失败');
        };
    }

    showError(error) {
        const chartImage = document.getElementById('chart-image');
        chartImage.style.display = 'none';
        
        const chartContent = chartImage.parentElement;
        chartContent.innerHTML = `
            <div class="error-message">
                <div class="error-icon">⚠️</div>
                <p>加载失败</p>
                <small>${error}</small>
            </div>
        `;
    }

    startAutoRefresh() {
        this.stopAutoRefresh(); // 确保没有重复的定时器
        this.autoRefreshInterval = setInterval(() => {
            this.loadChart();
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

    showLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
    }

    hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
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
    new AllcoinTrendManager();
});
