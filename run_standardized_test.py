#!/usr/bin/env python3
"""
标准化性能对比测试运行器
使用相同的测试查询对三种设计模式进行公平对比
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加src路径到Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 加载环境变量
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print("✅ Environment variables loaded")
    else:
        load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not available, environment variables may not be loaded")


async def run_full_comparison():
    """运行完整的标准化对比测试"""
    print("🚀 启动标准化AI Agent设计模式对比测试")
    print("=" * 60)

    try:
        # 导入所需模块
        from src.agent.pattern_react import graph_pattern_react
        from src.agent.pattern_sequential import graph_pattern_sequential

        # from src.agent.pattern_stateful import graph_pattern_stateful
        from src.evaluation.standardized_tests import StandardizedTester

        # 准备测试模式
        patterns = {
            "ReAct": graph_pattern_react,
            "Sequential": graph_pattern_sequential,
            # "State-based": graph_pattern_stateful,
        }

        print("✅ 已加载三种设计模式:")
        for name in patterns.keys():
            print(f"   • {name}")

        # 创建测试器并运行测试
        tester = StandardizedTester()

        print(f"\n🧪 开始运行标准化测试...")
        print(f"   • 每个复杂度级别测试 2 个查询")
        print(f"   • 总计: 3个复杂度 × 2个查询 × 3个模式 = 18 个测试")

        # 运行测试
        report = await tester.run_comprehensive_test(patterns, queries_per_complexity=2)

        # 显示详细结果
        tester.print_detailed_report()

        # 保存报告
        filename = tester.save_report("reports/standardized_comparison.json")

        print(f"\n🎉 测试完成！")
        print(f"📄 详细报告已保存至: {filename}")

        return report

    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("请确保:")
        print("  1. 所有依赖已安装: pip install -e .")
        print("  2. 在项目根目录运行此脚本")
        return None

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        return None


async def quick_test():
    """快速测试（每个复杂度只测试1个查询）"""
    print("⚡ 快速标准化测试")
    print("=" * 30)

    try:
        from src.agent.pattern_react import graph_pattern_react
        from src.agent.pattern_sequential import graph_pattern_sequential

        # from src.agent.pattern_stateful import graph_pattern_stateful
        from src.evaluation.standardized_tests import StandardizedTester

        patterns = {
            "ReAct": graph_pattern_react,
            "Sequential": graph_pattern_sequential,
            # "State-based": graph_pattern_stateful
        }

        tester = StandardizedTester()
        print("🧪 运行快速测试 (3个复杂度 × 1个查询 × 3个模式 = 9个测试)")

        await tester.run_comprehensive_test(patterns, queries_per_complexity=1)
        tester.print_detailed_report()

        return tester.save_report("reports/quick_comparison.json")

    except Exception as e:
        print(f"❌ 快速测试失败: {e}")
        return None


def main():
    """主函数"""
    # 确保reports目录存在
    os.makedirs("reports", exist_ok=True)

    print("🎯 AI Agent设计模式标准化对比测试")
    print("选择测试模式:")
    print("  1. 完整测试 (推荐)")
    print("  2. 快速测试")
    print("  3. 退出")

    choice = input("\n请输入选择 (1-3): ").strip()

    if choice == "1":
        result = asyncio.run(run_full_comparison())
    elif choice == "2":
        result = asyncio.run(quick_test())
    elif choice == "3":
        print("👋 再见!")
        return
    else:
        print("❌ 无效选择")
        return

    if result:
        print("\n✨ 测试成功完成!")
        print("\n📋 关键发现:")
        if "summary" in result:
            summary = result["summary"]
            print(f"  🏆 综合最佳: {summary.get('overall_winner', 'N/A')}")
            print(f"  ⚡ 最快响应: {summary.get('fastest_pattern', 'N/A')}")
            print(f"  🛡️ 最可靠: {summary.get('most_reliable', 'N/A')}")
    else:
        print("\n❌ 测试失败，请检查配置")


if __name__ == "__main__":
    main()
