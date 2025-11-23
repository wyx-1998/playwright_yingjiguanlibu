#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证书查询脚本使用示例
演示如何使用改进版证书查询器进行单个和批量查询
"""

import asyncio
import os
from improved_certificate_checker import ImprovedCertificateChecker

async def example_single_query():
    """
    单个证书查询示例
    """
    print("=== 单个证书查询示例 ===")
    
    # 创建查询器实例
    checker = ImprovedCertificateChecker()
    
    try:
        # 初始化浏览器
        await checker.initialize()
        
        # 示例证书信息（请替换为真实信息）
        cert_id = "110101199001011234"  # 证件号码
        name = "张三"                   # 姓名
        cert_type = "身份证"            # 证件类型
        query_type = "特种作业操作证"    # 查询类型
        
        print(f"正在查询: {name} ({cert_id})")
        
        # 执行查询
        result = await checker.query_single_certificate(
            cert_id=cert_id,
            name=name,
            cert_type=cert_type,
            query_type=query_type
        )
        
        # 显示结果
        if result['success']:
            print("✓ 查询成功！")
            print(f"查询结果: {result['result']}")
        else:
            print("✗ 查询失败")
            print(f"错误信息: {result['error']}")
            
    except Exception as e:
        print(f"查询过程中出现错误: {e}")
    finally:
        # 关闭浏览器
        await checker.close()

async def example_batch_query():
    """
    批量证书查询示例
    """
    print("\n=== 批量证书查询示例 ===")
    
    # 创建查询器实例
    checker = ImprovedCertificateChecker()
    
    try:
        # 初始化浏览器
        await checker.initialize()
        
        # 示例批量数据（请替换为真实信息）
        batch_data = [
            {
                "证件号码": "110101199001011234",
                "姓名": "张三"
            },
            {
                "证件号码": "310101199201022345", 
                "姓名": "李四"
            },
            {
                "证件号码": "440101199301033456",
                "姓名": "王五"
            }
        ]
        
        print(f"准备批量查询 {len(batch_data)} 条记录")
        
        # 执行批量查询
        results = await checker.batch_query(
            data=batch_data,
            cert_type="身份证",
            query_type="特种作业操作证",
            delay_range=(3, 6)  # 查询间隔3-6秒
        )
        
        # 显示统计结果
        stats = checker.get_statistics()
        print("\n=== 查询统计 ===")
        print(f"总查询数: {stats['total_queries']}")
        print(f"成功数: {stats['successful_queries']}")
        print(f"失败数: {stats['failed_queries']}")
        print(f"成功率: {stats['success_rate']:.1f}%")
        print(f"验证码识别率: {stats['captcha_success_rate']:.1f}%")
        
        # 保存结果
        json_file, csv_file = checker.save_results()
        print(f"\n结果已保存:")
        print(f"JSON文件: {json_file}")
        print(f"CSV文件: {csv_file}")
        
    except Exception as e:
        print(f"批量查询过程中出现错误: {e}")
    finally:
        # 关闭浏览器
        await checker.close()

async def example_csv_batch_query():
    """
    从CSV文件批量查询示例
    """
    print("\n=== CSV文件批量查询示例 ===")
    
    # 检查示例CSV文件是否存在
    csv_file = "证书查询样例.csv"
    if not os.path.exists(csv_file):
        print(f"示例CSV文件 {csv_file} 不存在")
        print("请先创建CSV文件，格式如下:")
        print("证件号码,姓名,查询类型")
        print("110101199001011234,张三,1")
        print("310101199201022345,李四,2")
        print("查询类型: 1=特种作业操作证查询, 2=安全生产知识和管理能力考核合格信息查询")
        return
    
    # 创建查询器实例
    checker = ImprovedCertificateChecker()
    
    try:
        # 初始化浏览器
        await checker.initialize()
        
        print(f"正在从 {csv_file} 读取查询数据...")
        
        # 从CSV文件批量查询
        results = await checker.batch_query_from_csv(
            csv_file=csv_file,
            cert_type="身份证",
            default_query_type=1,  # 当CSV中没有查询类型列时的默认值 (1=特种作业操作证查询)
            delay=3
        )
        
        # 显示结果
        stats = checker.get_statistics()
        print("\n=== 查询完成 ===")
        print(f"处理文件: {csv_file}")
        print(f"总记录数: {stats['total_queries']}")
        print(f"查询成功: {stats['successful_queries']}")
        print(f"查询失败: {stats['failed_queries']}")
        print(f"成功率: {stats['success_rate']:.1f}%")
        
        # 保存结果
        json_file, csv_file = checker.save_results()
        print(f"\n结果文件:")
        print(f"详细结果: {json_file}")
        print(f"汇总表格: {csv_file}")
        
    except Exception as e:
        print(f"CSV批量查询过程中出现错误: {e}")
    finally:
        # 关闭浏览器
        await checker.close()

def main():
    """
    主函数 - 演示各种使用方式
    """
    print("证书查询脚本使用示例")
    print("=" * 50)
    
    while True:
        print("\n请选择示例:")
        print("1. 单个证书查询")
        print("2. 批量证书查询（代码数据）")
        print("3. CSV文件批量查询")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-3): ").strip()
        
        if choice == "1":
            asyncio.run(example_single_query())
        elif choice == "2":
            asyncio.run(example_batch_query())
        elif choice == "3":
            asyncio.run(example_csv_batch_query())
        elif choice == "0":
            print("退出示例程序")
            break
        else:
            print("无效选择，请重新输入")

if __name__ == "__main__":
    main()