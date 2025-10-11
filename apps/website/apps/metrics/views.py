from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
from pathlib import Path

def metrics_home(request):
    """指标可视化主页 - 显示所有可用指标"""
    # 定义可用指标
    indicators = [
        {
            "id": "topdogindex",
            "name": "TOPDOGINDEX 指标",
            "description": "多时间框架对比分析，包含6张comparison图片",
            "type": "multi_chart",
            "charts": 6,
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
        },
        {
            "id": "allcoin_trend",
            "name": "全币种趋势",
            "description": "所有币种的价格变化趋势图",
            "type": "single_chart",
            "charts": 1,
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
        },
        {
            "id": "kline",
            "name": "K线图",
            "description": "单个币种的K线图展示",
            "type": "kline",
            "charts": 1,
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
        }
    ]
    
    return render(request, "metrics/home.html", {
        "indicators": indicators
    })

def indicator_detail(request, indicator_id):
    """指标详情页面"""
    if indicator_id == "topdogindex":
        return render(request, "metrics/topdogindex.html", {
            "indicator_id": indicator_id,
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
        })
    elif indicator_id == "allcoin_trend":
        return render(request, "metrics/allcoin_trend.html", {
            "indicator_id": indicator_id,
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
        })
    elif indicator_id == "kline":
        return render(request, "metrics/kline.html", {
            "indicator_id": indicator_id,
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],
            "coins": ["btc", "eth", "xrp", "bnb", "sol", "ada", "doge", "trx", "ltc", "shib"]
        })
    else:
        return render(request, "metrics/error.html", {
            "error": f"未知指标: {indicator_id}"
        })

@csrf_exempt
def get_chart_image(request, indicator_id):
    """获取图表图片的AJAX接口"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        data = json.loads(request.body)
        timeframe = data.get('timeframe', '1m')
        coin = data.get('coin', 'btc')
        
        # 构建图片路径
        chart_dir = Path("/home/zzb/Quantify/ctos/apps/indicatorVisualization/chart_for_group")
        
        if indicator_id == "topdogindex":
            # TOPDOGINDEX的comparison图片
            chart_name = f"all_coin-{['1m', '5m', '15m', '1h', '4h', '1d'].index(timeframe)}"
            image_path = chart_dir / f"comparison_chart_{chart_name}_{timeframe}.png"
        elif indicator_id == "allcoin_trend":
            # 全币种趋势图
            image_path = chart_dir / f"allcoin_trend_{timeframe}.png"
        elif indicator_id == "kline":
            # K线图（这里需要根据实际实现调整）
            image_path = chart_dir / f"kline_{coin}_{timeframe}.png"
        else:
            return JsonResponse({
                "success": False,
                "error": f"未知指标: {indicator_id}"
            }, status=404)
        
        # 检查图片是否存在
        if not image_path.exists():
            return JsonResponse({
                "success": False,
                "error": f"图片不存在: {image_path.name}"
            }, status=404)
        
        # 返回图片的相对路径
        relative_path = f"/static/images/{image_path.name}"
        
        return JsonResponse({
            "success": True,
            "image_path": relative_path,
            "indicator_id": indicator_id,
            "timeframe": timeframe,
            "coin": coin
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
