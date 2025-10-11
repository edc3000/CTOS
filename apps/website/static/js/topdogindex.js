// TOPDOGINDEX 指标页面 JavaScript

class TopdogindexManager {
    constructor() {
        this.config = window.topdogindexConfig;
        this.timeframes = this.config.timeframes;
        this.currentTimeframe = 'all';
        this.currentDisplayMode = 'grid'; // 'grid' 或 'single'
        this.autoRefreshInterval = null;
        this.refreshInterval = 10000; // 10秒
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadAllCharts();
        this.startAutoRefresh();
    }

    bindEvents() {
        // 时间框架选择器
        const timeframeSelect = document.getElementById('timeframe-select');
        if (timeframeSelect) {
            timeframeSelect.addEventListener('change', (e) => {
                this.currentTimeframe = e.target.value;
                this.loadAllCharts();
            });
        }

        // 展示模式选择器
        const displayModeSelect = document.getElementById('display-mode-select');
        if (displayModeSelect) {
            displayModeSelect.addEventListener('change', (e) => {
                this.currentDisplayMode = e.target.value;
                this.updateDisplayMode();
            });
        }

        // 手动刷新按钮
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadAllCharts();
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

    async loadAllCharts() {
        this.showLoading();
        
        try {
            const chartsContainer = document.getElementById('charts-container');
            chartsContainer.innerHTML = '';

            if (this.currentTimeframe === 'all') {
                // 显示所有时间框架的图表
                for (let i = 0; i < this.timeframes.length; i++) {
                    const timeframe = this.timeframes[i];
                    await this.loadChart(timeframe, i);
                }
            } else {
                // 只显示选中的时间框架
                const index = this.timeframes.indexOf(this.currentTimeframe);
                await this.loadChart(this.currentTimeframe, index);
            }
            
            this.updateDisplayMode();
            this.hideLoading();
            this.showNotification('图表加载完成', 'success');
        } catch (error) {
            this.hideLoading();
            this.showNotification(`加载失败: ${error.message}`, 'error');
        }
    }

    async loadChart(timeframe, index) {
        try {
            const response = await fetch(`/metrics/${this.config.indicatorId}/api/chart/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    timeframe: timeframe
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.createChartCard(timeframe, data.image_path, index);
            } else {
                this.createErrorCard(timeframe, data.error, index);
            }
        } catch (error) {
            this.createErrorCard(timeframe, error.message, index);
        }
    }

    createChartCard(timeframe, imagePath, index) {
        const chartsContainer = document.getElementById('charts-container');
        
        const chartCard = document.createElement('div');
        chartCard.className = 'chart-card';
        chartCard.innerHTML = `
            <div class="chart-header">
                <h3>TOPDOGINDEX - ${timeframe.toUpperCase()}</h3>
                <span class="chart-index">#${index + 1}</span>
            </div>
            <div class="chart-content">
                <img src="${imagePath}" alt="TOPDOGINDEX ${timeframe}" 
                     class="chart-image" 
                     onload="this.style.opacity=1"
                     onerror="this.parentElement.innerHTML='<div class=\\'error-message\\'>图片加载失败</div>'">
            </div>
            <div class="chart-footer">
                <span class="chart-timeframe">${timeframe.toUpperCase()}</span>
                <span class="chart-timestamp">${new Date().toLocaleTimeString()}</span>
            </div>
        `;
        
        chartsContainer.appendChild(chartCard);
    }

    createErrorCard(timeframe, error, index) {
        const chartsContainer = document.getElementById('charts-container');
        
        const errorCard = document.createElement('div');
        errorCard.className = 'chart-card error-card';
        errorCard.innerHTML = `
            <div class="chart-header">
                <h3>TOPDOGINDEX - ${timeframe.toUpperCase()}</h3>
                <span class="chart-index">#${index + 1}</span>
            </div>
            <div class="chart-content">
                <div class="error-message">
                    <div class="error-icon">⚠️</div>
                    <p>加载失败</p>
                    <small>${error}</small>
                </div>
            </div>
            <div class="chart-footer">
                <span class="chart-timeframe">${timeframe.toUpperCase()}</span>
                <span class="chart-timestamp">${new Date().toLocaleTimeString()}</span>
            </div>
        `;
        
        chartsContainer.appendChild(errorCard);
    }

    updateDisplayMode() {
        const chartsContainer = document.getElementById('charts-container');
        const pageContainer = document.querySelector('.topdogindex-container');
        const chartCards = chartsContainer.querySelectorAll('.chart-card');
        
        // 移除所有现有的样式类
        chartsContainer.classList.remove('charts-grid', 'charts-single');
        chartCards.forEach(card => {
            card.classList.remove('chart-card-grid', 'chart-card-single');
        });
        
        if (this.currentDisplayMode === 'single') {
            // 单页展示模式：6张图在一页
            chartsContainer.classList.add('charts-single');
            chartCards.forEach(card => {
                card.classList.add('chart-card-single');
            });
            // 添加单页模式类到页面容器
            if (pageContainer) {
                pageContainer.classList.add('single-mode');
            }
        } else {
            // 网格布局模式：竖排放置
            chartsContainer.classList.add('charts-grid');
            chartCards.forEach(card => {
                card.classList.add('chart-card-grid');
            });
            // 移除单页模式类
            if (pageContainer) {
                pageContainer.classList.remove('single-mode');
            }
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh(); // 确保没有重复的定时器
        this.autoRefreshInterval = setInterval(() => {
            this.loadAllCharts();
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
    new TopdogindexManager();
});
