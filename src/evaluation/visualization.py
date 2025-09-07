"""
性能对比可视化工具
生成HTML格式的可视化对比报告
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime

class VisualizationGenerator:
    """可视化报告生成器"""
    
    def generate_html_report(self, report_data: Dict[str, Any], output_file: str = "reports/comparison_report.html"):
        """生成HTML可视化报告"""
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent设计模式性能对比报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .metric-card h3 {{
            margin-top: 0;
            color: #495057;
        }}
        .ranking {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .ranking h2 {{
            color: white;
            border-left: 4px solid white;
        }}
        .rank-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin: 10px 0;
            background: rgba(255,255,255,0.1);
            border-radius: 5px;
        }}
        .rank-number {{
            font-size: 1.5em;
            font-weight: bold;
            width: 30px;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}
        .summary-box {{
            background: #e8f5e8;
            border: 1px solid #d4edda;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .recommendation {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        .timestamp {{
            text-align: center;
            color: #6c757d;
            font-style: italic;
            margin-top: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .success-rate {{
            color: #28a745;
            font-weight: bold;
        }}
        .latency {{
            color: #17a2b8;
            font-weight: bold;
        }}
        .score {{
            color: #dc3545;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 AI Agent设计模式性能对比报告</h1>
        
        <div class="summary-box">
            <h2>📊 测试概况</h2>
            <p><strong>测试时间：</strong>{report_data.get('timestamp', 'N/A')}</p>
            <p><strong>总测试数：</strong>{report_data.get('total_tests', 0)} 个</p>
            <p><strong>测试模式：</strong>ReAct、Sequential、State-based</p>
            <p><strong>测试原则：</strong>使用相同的标准化查询确保公平对比</p>
        </div>

        <div class="ranking">
            <h2>🏆 综合排名</h2>
            {self._generate_ranking_html(report_data.get('ranking', []))}
        </div>

        <h2>📈 性能指标对比</h2>
        <div class="chart-container">
            <canvas id="performanceChart"></canvas>
        </div>

        <h2>📊 详细性能数据</h2>
        {self._generate_performance_table(report_data.get('pattern_performance', {}))}

        <h2>🎯 按复杂度分析</h2>
        <div class="chart-container">
            <canvas id="complexityChart"></canvas>
        </div>
        
        <h2>💡 使用建议</h2>
        {self._generate_recommendations(report_data.get('summary', {}).get('recommendations', {}))}
        
        <div class="timestamp">
            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>

    <script>
        // 性能对比图表
        const performanceCtx = document.getElementById('performanceChart').getContext('2d');
        const performanceChart = new Chart(performanceCtx, {{
            type: 'radar',
            data: {{
                labels: ['成功率', '响应速度', '响应质量', '可靠性'],
                datasets: {json.dumps(self._prepare_radar_data(report_data.get('pattern_performance', {})))}
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});

        // 复杂度对比图表
        const complexityCtx = document.getElementById('complexityChart').getContext('2d');
        const complexityChart = new Chart(complexityCtx, {{
            type: 'bar',
            data: {{
                labels: ['Simple', 'Medium', 'Complex'],
                datasets: {json.dumps(self._prepare_complexity_data(report_data.get('complexity_analysis', {})))}
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: '平均延迟 (秒)'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 可视化报告已生成: {output_file}")
        return output_file
    
    def _generate_ranking_html(self, ranking: List[Dict]) -> str:
        """生成排名HTML"""
        html = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, item in enumerate(ranking):
            medal = medals[i] if i < 3 else f"{i+1}."
            html += f"""
            <div class="rank-item">
                <div>
                    <span class="rank-number">{medal}</span>
                    <strong>{item['pattern']}</strong>
                </div>
                <div class="score">{item['score']:.1f}分</div>
            </div>
            """
        return html
    
    def _generate_performance_table(self, performance_data: Dict) -> str:
        """生成性能数据表格"""
        if not performance_data:
            return "<p>无性能数据</p>"
        
        html = """
        <table>
            <thead>
                <tr>
                    <th>模式</th>
                    <th>成功率</th>
                    <th>平均延迟</th>
                    <th>最小延迟</th>
                    <th>最大延迟</th>
                    <th>平均响应长度</th>
                    <th>工具调用次数</th>
                    <th>综合评分</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for pattern, data in performance_data.items():
            success_rate = data['success_rate'] * 100
            html += f"""
                <tr>
                    <td><strong>{pattern}</strong></td>
                    <td class="success-rate">{success_rate:.1f}%</td>
                    <td class="latency">{data['avg_latency']:.2f}s</td>
                    <td>{data['min_latency']:.2f}s</td>
                    <td>{data['max_latency']:.2f}s</td>
                    <td>{data['avg_response_length']:.0f} 字符</td>
                    <td>{data['total_tool_calls']} 次</td>
                    <td class="score">{self._calculate_score(data):.1f}分</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        return html
    
    def _generate_recommendations(self, recommendations: Dict) -> str:
        """生成使用建议"""
        if not recommendations:
            return "<p>无使用建议</p>"
        
        html = ""
        for task_type, recommendation in recommendations.items():
            html += f"""
            <div class="recommendation">
                <strong>{task_type.replace('_', ' ').title()}:</strong> {recommendation}
            </div>
            """
        return html
    
    def _prepare_radar_data(self, performance_data: Dict) -> List[Dict]:
        """准备雷达图数据"""
        datasets = []
        colors = {
            'ReAct': {'border': 'rgb(255, 99, 132)', 'background': 'rgba(255, 99, 132, 0.2)'},
            'Sequential': {'border': 'rgb(54, 162, 235)', 'background': 'rgba(54, 162, 235, 0.2)'},
            'State-based': {'border': 'rgb(75, 192, 192)', 'background': 'rgba(75, 192, 192, 0.2)'}
        }
        
        for pattern, data in performance_data.items():
            # 转换为0-100的分数
            success_score = data['success_rate'] * 100
            speed_score = max(0, 100 - (data['avg_latency'] * 20))  # 延迟越低分数越高
            quality_score = min(100, data['avg_response_length'] / 10)  # 响应长度适中为好
            reliability_score = min(100, (1 - data['avg_latency'] / 10) * 100)  # 基于延迟的可靠性
            
            color_set = colors.get(pattern, {'border': 'rgb(201, 203, 207)', 'background': 'rgba(201, 203, 207, 0.2)'})
            
            datasets.append({
                'label': pattern,
                'data': [success_score, speed_score, quality_score, reliability_score],
                'borderColor': color_set['border'],
                'backgroundColor': color_set['background']
            })
        
        return datasets
    
    def _prepare_complexity_data(self, complexity_data: Dict) -> List[Dict]:
        """准备复杂度对比数据"""
        datasets = []
        patterns = set()
        
        # 收集所有模式
        for complexity, analysis in complexity_data.items():
            patterns.update(analysis.get('avg_latency_by_pattern', {}).keys())
        
        colors = ['rgba(255, 99, 132, 0.8)', 'rgba(54, 162, 235, 0.8)', 'rgba(75, 192, 192, 0.8)']
        
        for i, pattern in enumerate(patterns):
            data = []
            for complexity in ['simple', 'medium', 'complex']:
                latency = complexity_data.get(complexity, {}).get('avg_latency_by_pattern', {}).get(pattern, 0)
                data.append(latency)
            
            datasets.append({
                'label': pattern,
                'data': data,
                'backgroundColor': colors[i % len(colors)]
            })
        
        return datasets
    
    def _calculate_score(self, data: Dict) -> float:
        """计算综合评分"""
        success_score = data['success_rate'] * 40
        latency_score = max(0, (5 - data['avg_latency']) / 5 * 30)
        efficiency_score = max(0, (10 - data['total_tool_calls'] / max(data['total_tests'], 1)) / 10 * 20)
        quality_score = min(10, data['avg_response_length'] / 100)
        return success_score + latency_score + efficiency_score + quality_score

def generate_report_from_file(json_file: str, output_html: str = None):
    """从JSON文件生成可视化报告"""
    if output_html is None:
        output_html = json_file.replace('.json', '.html')
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        generator = VisualizationGenerator()
        return generator.generate_html_report(report_data, output_html)
    
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        return None

if __name__ == "__main__":
    print("可视化报告生成器")
    print("使用方法:")
    print("  python -c \"from src.evaluation.visualization import generate_report_from_file; generate_report_from_file('reports/standardized_comparison.json')\"")