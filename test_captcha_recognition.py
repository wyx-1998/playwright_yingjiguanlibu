#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码识别测试脚本
用于测试和评估验证码识别功能的准确率
"""

import asyncio
import os
import time
from datetime import datetime
from enhanced_captcha_recognizer import EnhancedCaptchaRecognizer
from playwright.async_api import async_playwright

class CaptchaRecognitionTester:
    """
    验证码识别测试器
    """
    
    def __init__(self):
        self.recognizer = EnhancedCaptchaRecognizer()
        self.browser = None
        self.page = None
        self.test_results = []
        
    async def initialize(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        browser_type = os.getenv("BROWSER", "chromium").lower()
        if browser_type == "firefox":
            self.browser = await playwright.firefox.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
        elif browser_type == "webkit":
            self.browser = await playwright.webkit.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
        else:
            self.browser = await playwright.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
        
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.page = await context.new_page()
        
        # 导航到查询页面
        await self.page.goto("https://cx.mem.gov.cn/wxcx/pages/certificateQuery/inputQuery")
        await self.page.wait_for_load_state('networkidle')
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            
    async def test_single_captcha(self, save_image=True):
        """
        测试单个验证码识别
        
        Args:
            save_image: 是否保存验证码图片
            
        Returns:
            dict: 测试结果
        """
        try:
            # 获取验证码
            captcha_result = await self.recognizer.get_captcha_from_page(self.page)
            
            if not captcha_result['success']:
                return {
                    'success': False,
                    'error': captcha_result['error'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # 保存验证码图片（可选）
            image_path = None
            if save_image:
                os.makedirs('test_captcha', exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                image_path = f'test_captcha/captcha_{timestamp}.png'
                
                with open(image_path, 'wb') as f:
                    f.write(captcha_result['image_data'])
            
            # 识别验证码
            recognition_result = await self.recognizer.recognize_with_retry(
                captcha_result['image_data'],
                max_retries=1  # 单次测试不重试
            )
            
            result = {
                'success': recognition_result['success'],
                'recognized_text': recognition_result.get('text', ''),
                'confidence': recognition_result.get('confidence', 0),
                'method_used': recognition_result.get('method', ''),
                'processing_time': recognition_result.get('processing_time', 0),
                'image_path': image_path,
                'timestamp': datetime.now().isoformat()
            }
            
            if not recognition_result['success']:
                result['error'] = recognition_result.get('error', 'Unknown error')
                
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def test_multiple_captchas(self, count=10, delay=2):
        """
        测试多个验证码识别
        
        Args:
            count: 测试次数
            delay: 每次测试间隔（秒）
            
        Returns:
            dict: 测试统计结果
        """
        print(f"开始测试 {count} 个验证码识别...")
        
        results = []
        successful_recognitions = 0
        total_confidence = 0
        total_processing_time = 0
        
        for i in range(count):
            print(f"\n测试 {i+1}/{count}")
            
            # 刷新验证码
            if i > 0:
                try:
                    await self.page.click('.yzm-style-img')
                    await asyncio.sleep(1)
                except:
                    pass
            
            # 测试识别
            result = await self.test_single_captcha(save_image=True)
            results.append(result)
            
            if result['success']:
                successful_recognitions += 1
                total_confidence += result.get('confidence', 0)
                total_processing_time += result.get('processing_time', 0)
                
                print(f"✓ 识别成功: {result['recognized_text']} (置信度: {result.get('confidence', 0):.2f})")
            else:
                print(f"✗ 识别失败: {result.get('error', 'Unknown error')}")
            
            # 延时
            if i < count - 1:
                await asyncio.sleep(delay)
        
        # 计算统计信息
        success_rate = (successful_recognitions / count) * 100
        avg_confidence = total_confidence / successful_recognitions if successful_recognitions > 0 else 0
        avg_processing_time = total_processing_time / successful_recognitions if successful_recognitions > 0 else 0
        
        stats = {
            'total_tests': count,
            'successful_recognitions': successful_recognitions,
            'failed_recognitions': count - successful_recognitions,
            'success_rate': success_rate,
            'average_confidence': avg_confidence,
            'average_processing_time': avg_processing_time,
            'detailed_results': results,
            'test_timestamp': datetime.now().isoformat()
        }
        
        return stats
    
    def save_test_results(self, stats):
        """
        保存测试结果到文件
        
        Args:
            stats: 测试统计结果
            
        Returns:
            str: 保存的文件路径
        """
        import json
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'captcha_test_results_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def print_test_summary(self, stats):
        """
        打印测试摘要
        
        Args:
            stats: 测试统计结果
        """
        print("\n" + "=" * 50)
        print("验证码识别测试结果摘要")
        print("=" * 50)
        print(f"测试总数: {stats['total_tests']}")
        print(f"识别成功: {stats['successful_recognitions']}")
        print(f"识别失败: {stats['failed_recognitions']}")
        print(f"成功率: {stats['success_rate']:.1f}%")
        print(f"平均置信度: {stats['average_confidence']:.2f}")
        print(f"平均处理时间: {stats['average_processing_time']:.2f}秒")
        
        # 分析失败原因
        failed_results = [r for r in stats['detailed_results'] if not r['success']]
        if failed_results:
            print("\n失败原因分析:")
            error_counts = {}
            for result in failed_results:
                error = result.get('error', 'Unknown')
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in error_counts.items():
                print(f"  - {error}: {count}次")
        
        print("=" * 50)

async def main():
    """
    主测试函数
    """
    tester = CaptchaRecognitionTester()
    
    try:
        print("初始化测试环境...")
        await tester.initialize()
        
        while True:
            print("\n验证码识别测试菜单:")
            print("1. 单次识别测试")
            print("2. 批量识别测试 (10次)")
            print("3. 批量识别测试 (50次)")
            print("4. 自定义批量测试")
            print("0. 退出")
            
            choice = input("\n请选择测试类型 (0-4): ").strip()
            
            if choice == "1":
                print("\n执行单次识别测试...")
                result = await tester.test_single_captcha()
                
                if result['success']:
                    print(f"✓ 识别成功: {result['recognized_text']}")
                    print(f"置信度: {result.get('confidence', 0):.2f}")
                    print(f"处理时间: {result.get('processing_time', 0):.2f}秒")
                    if result.get('image_path'):
                        print(f"图片保存: {result['image_path']}")
                else:
                    print(f"✗ 识别失败: {result.get('error', 'Unknown error')}")
            
            elif choice == "2":
                stats = await tester.test_multiple_captchas(count=10)
                tester.print_test_summary(stats)
                
                # 保存结果
                filename = tester.save_test_results(stats)
                print(f"\n详细结果已保存到: {filename}")
            
            elif choice == "3":
                stats = await tester.test_multiple_captchas(count=50)
                tester.print_test_summary(stats)
                
                # 保存结果
                filename = tester.save_test_results(stats)
                print(f"\n详细结果已保存到: {filename}")
            
            elif choice == "4":
                try:
                    count = int(input("请输入测试次数: "))
                    delay = float(input("请输入测试间隔(秒): "))
                    
                    if count <= 0 or delay < 0:
                        print("无效输入，请输入正数")
                        continue
                    
                    stats = await tester.test_multiple_captchas(count=count, delay=delay)
                    tester.print_test_summary(stats)
                    
                    # 保存结果
                    filename = tester.save_test_results(stats)
                    print(f"\n详细结果已保存到: {filename}")
                    
                except ValueError:
                    print("输入格式错误，请输入数字")
            
            elif choice == "0":
                print("退出测试程序")
                break
            
            else:
                print("无效选择，请重新输入")
    
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
