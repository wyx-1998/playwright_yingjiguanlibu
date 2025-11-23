import asyncio
import os
import base64
import io
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import ddddocr
import time
from typing import Tuple, Optional

class EnhancedCaptchaRecognizer:
    """
    增强型验证码识别器
    解决当前验证码识别率低的问题
    """
    
    def __init__(self):
        self.ocr_models = self._initialize_ocr_models()
        self.img_dir = "img"
        os.makedirs(self.img_dir, exist_ok=True)
        
    def _initialize_ocr_models(self):
        """初始化多个OCR模型"""
        models = {}
        try:
            # 标准模型
            models['standard'] = ddddocr.DdddOcr(show_ad=False)
            
            # 数字+字母模型
            models['alpha_numeric'] = ddddocr.DdddOcr(show_ad=False, beta=True)
            
            # 自定义模型（如果有训练好的模型）
            # models['custom'] = ddddocr.DdddOcr(show_ad=False, det=False, ocr=False)
            # models['custom'].set_ranges(0)  # 设置为数字+字母
            
            print(f"已初始化 {len(models)} 个OCR模型")
        except Exception as e:
            print(f"初始化OCR模型失败: {e}")
            
        return models
    
    def preprocess_image(self, image_data: bytes, method: str = 'standard') -> bytes:
        """
        图像预处理，提高识别率
        
        Args:
            image_data: 原始图像数据
            method: 预处理方法 ('standard', 'denoise', 'enhance', 'threshold')
            
        Returns:
            处理后的图像数据
        """
        try:
            # 将bytes转换为PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            if method == 'standard':
                # 标准处理：调整大小和对比度
                if image.size[0] < 100 or image.size[1] < 40:
                    # 放大小图片
                    image = image.resize((image.size[0] * 2, image.size[1] * 2), Image.LANCZOS)
                
                # 增强对比度
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)
                
            elif method == 'denoise':
                # 降噪处理
                image = image.filter(ImageFilter.MedianFilter(size=3))
                
                # 转换为灰度图
                if image.mode != 'L':
                    image = image.convert('L')
                    
                # 增强锐度
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(2.0)
                
            elif method == 'enhance':
                # 增强处理
                # 转换为RGB
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                    
                # 调整亮度
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(1.2)
                
                # 调整对比度
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.8)
                
                # 转换为灰度
                image = image.convert('L')
                
            elif method == 'threshold':
                # 二值化处理
                # 转换为numpy数组
                img_array = np.array(image)
                if len(img_array.shape) == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    
                # 高斯模糊
                img_array = cv2.GaussianBlur(img_array, (3, 3), 0)
                
                # 自适应阈值
                img_array = cv2.adaptiveThreshold(
                    img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
                
                # 形态学操作去噪
                kernel = np.ones((2, 2), np.uint8)
                img_array = cv2.morphologyEx(img_array, cv2.MORPH_CLOSE, kernel)
                
                # 转换回PIL Image
                image = Image.fromarray(img_array)
            
            # 将处理后的图像转换为bytes
            output = io.BytesIO()
            image.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            print(f"图像预处理失败 ({method}): {e}")
            return image_data  # 返回原始数据
    
    def recognize_with_multiple_methods(self, image_data: bytes, save_path: str = None) -> Tuple[str, float]:
        """
        使用多种方法识别验证码
        
        Args:
            image_data: 图像数据
            save_path: 保存路径（可选）
            
        Returns:
            (识别结果, 置信度)
        """
        results = []
        
        # 预处理方法列表
        preprocess_methods = ['standard', 'denoise', 'enhance', 'threshold']
        
        for method in preprocess_methods:
            try:
                # 预处理图像
                processed_data = self.preprocess_image(image_data, method)
                
                # 保存预处理后的图像（用于调试）
                if save_path:
                    debug_path = save_path.replace('.png', f'_{method}.png')
                    with open(debug_path, 'wb') as f:
                        f.write(processed_data)
                
                # 使用不同的OCR模型识别
                for model_name, ocr_model in self.ocr_models.items():
                    try:
                        result = ocr_model.classification(processed_data)
                        # 过滤结果：只保留数字，且长度为4位
                        if result:
                            # 提取数字字符
                            digit_result = ''.join(c for c in result if c.isdigit())
                            if len(digit_result) == 4:  # 验证码必须是4位数字
                                confidence = self._calculate_confidence(digit_result)
                                results.append((digit_result, confidence, f"{method}_{model_name}"))
                                print(f"方法 {method}_{model_name} 识别结果: {digit_result} (置信度: {confidence:.2f})")
                    except Exception as e:
                        print(f"模型 {model_name} 识别失败: {e}")
                        
            except Exception as e:
                print(f"预处理方法 {method} 失败: {e}")
        
        if not results:
            return None, 0.0
        
        # 分析结果一致性，提高置信度
        final_result, final_confidence = self._analyze_consistency_and_boost_confidence(results)
        
        return final_result, final_confidence
        
    def _analyze_consistency_and_boost_confidence(self, results: list) -> Tuple[str, float]:
        """
        分析多种方法识别结果的一致性，如果一致且置信度>0.5则提高置信度
        
        Args:
            results: [(result, confidence, method), ...]
            
        Returns:
            (最终结果, 最终置信度)
        """
        if not results:
            return None, 0.0
            
        # 统计每个识别结果的出现次数和平均置信度
        result_stats = {}
        for result, confidence, method in results:
            if result not in result_stats:
                result_stats[result] = {'count': 0, 'confidences': [], 'methods': []}
            result_stats[result]['count'] += 1
            result_stats[result]['confidences'].append(confidence)
            result_stats[result]['methods'].append(method)
        
        # 找到出现次数最多的结果
        most_common_result = max(result_stats.keys(), key=lambda x: result_stats[x]['count'])
        stats = result_stats[most_common_result]
        
        # 计算平均置信度
        avg_confidence = sum(stats['confidences']) / len(stats['confidences'])
        
        # 如果多种方法识别结果一致且平均置信度>0.5，则提高置信度
        if stats['count'] >= 2 and avg_confidence > 0.5:
            # 一致性加成：根据一致的方法数量提高置信度
            consistency_boost = min(0.3, stats['count'] * 0.1)  # 最多提高0.3
            final_confidence = min(0.95, avg_confidence + consistency_boost)  # 最高不超过0.95
            
            print(f"识别结果一致性分析:")
            print(f"  结果: {most_common_result}")
            print(f"  一致方法数: {stats['count']}/{len(results)}")
            print(f"  平均置信度: {avg_confidence:.2f}")
            print(f"  一致性加成: +{consistency_boost:.2f}")
            print(f"  最终置信度: {final_confidence:.2f}")
            print(f"  使用方法: {', '.join(stats['methods'])}")
            
            return most_common_result, final_confidence
        else:
            # 没有足够的一致性，返回置信度最高的单个结果
            best_result = max(results, key=lambda x: x[1])
            print(f"识别结果一致性不足，使用最佳单个结果: {best_result[0]} (方法: {best_result[2]}, 置信度: {best_result[1]:.2f})")
            return best_result[0], best_result[1]
    
    def _calculate_confidence(self, result: str) -> float:
        """
        计算识别结果的置信度（针对纯数字验证码优化）
        
        Args:
            result: 识别结果
            
        Returns:
            置信度 (0.0-1.0)
        """
        if not result:
            return 0.0
        
        # 针对纯数字验证码的基础置信度
        base_confidence = 0.8  # 提高基础置信度，因为数字识别相对容易
        
        # 检查是否为4位纯数字
        if len(result) == 4 and result.isdigit():
            base_confidence += 0.1  # 长度正确的纯数字加分
        
        # 检查容易混淆的数字字符（在数字识别中）
        confusing_pairs = {
            '0': ['O'],  # 0和O容易混淆
            '1': ['I', 'l', '|'],  # 1和I、l、|容易混淆
            '5': ['S'],  # 5和S容易混淆
            '6': ['G'],  # 6和G容易混淆
            '8': ['B'],  # 8和B容易混淆
        }
        
        # 对于纯数字，不需要过多惩罚，因为我们已经过滤了非数字字符
        # 只对特别容易出错的数字组合稍微降低置信度
        error_penalty = 0.0
        consecutive_same = 0
        for i in range(len(result) - 1):
            if result[i] == result[i + 1]:
                consecutive_same += 1
        
        # 连续相同数字可能是识别错误，稍微降低置信度
        if consecutive_same >= 2:
            error_penalty += 0.05
        
        final_confidence = max(0.3, base_confidence - error_penalty)
        
        return min(1.0, final_confidence)
    
    async def get_captcha_from_page(self, page, save_filename: str = None) -> Tuple[Optional[str], Optional[bytes]]:
        """
        从页面获取验证码并识别
        
        Args:
            page: Playwright页面对象
            save_filename: 保存文件名
            
        Returns:
            (识别结果, 图像数据)
        """
        try:
            # 尝试多种选择器获取验证码
            selectors = [
                '.yzm-style-img',
                'img[src*="captcha"]',
                'img[src*="verify"]',
                'img[alt*="验证码"]',
                '.captcha-img',
                '.verify-img'
            ]
            
            captcha_element = None
            for selector in selectors:
                try:
                    captcha_element = await page.query_selector(selector)
                    if captcha_element:
                        print(f"使用选择器 {selector} 找到验证码元素")
                        break
                except Exception:
                    continue
            
            if not captcha_element:
                print("无法找到验证码元素")
                return None, None
            
            # 获取验证码图片数据
            image_data = None
            
            # 方法1: 直接截图
            try:
                if save_filename:
                    screenshot_path = os.path.join(self.img_dir, save_filename)
                    await captcha_element.screenshot(path=screenshot_path)
                    with open(screenshot_path, 'rb') as f:
                        image_data = f.read()
                    print(f"验证码截图已保存: {screenshot_path}")
            except Exception as e:
                print(f"截图方法失败: {e}")
            
            # 方法2: 获取base64数据
            if not image_data:
                try:
                    src = await captcha_element.get_attribute('src')
                    if src and src.startswith('data:image'):
                        base64_data = src.split(',')[1]
                        image_data = base64.b64decode(base64_data)
                        print("从base64获取验证码数据")
                except Exception as e:
                    print(f"base64方法失败: {e}")
            
            if not image_data:
                print("无法获取验证码图片数据")
                return None, None
            
            # 使用增强识别方法
            save_path = os.path.join(self.img_dir, save_filename) if save_filename else None
            result, confidence = self.recognize_with_multiple_methods(image_data, save_path)
            
            if result and confidence > 0.5:  # 降低置信度阈值，配合新的置信度提升机制
                print(f"验证码识别成功: {result} (置信度: {confidence:.2f})")
                return result, image_data
            else:
                print(f"验证码识别置信度较低: {result} (置信度: {confidence:.2f})")
                return None, image_data
                
        except Exception as e:
            print(f"获取验证码失败: {e}")
            return None, None
    
    async def refresh_and_recognize(self, page, max_attempts: int = 5) -> Optional[str]:
        """
        刷新验证码并尝试识别
        
        Args:
            page: Playwright页面对象
            max_attempts: 最大尝试次数
            
        Returns:
            识别结果
        """
        for attempt in range(max_attempts):
            try:
                print(f"第 {attempt + 1} 次尝试识别验证码")
                
                # 刷新验证码
                if attempt > 0:
                    try:
                        await page.click('.yzm-style-img')
                        await page.wait_for_timeout(1000)
                        print("已刷新验证码")
                    except Exception as e:
                        print(f"刷新验证码失败: {e}")
                
                # 识别验证码
                timestamp = int(time.time())
                filename = f"captcha_{timestamp}_{attempt}.png"
                result, _ = await self.get_captcha_from_page(page, filename)
                
                if result:
                    return result
                    
                # 等待一段时间再尝试
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                print(f"第 {attempt + 1} 次尝试失败: {e}")
        
        print(f"经过 {max_attempts} 次尝试，仍无法识别验证码")
        return None

# 使用示例
if __name__ == "__main__":
    # 测试代码
    recognizer = EnhancedCaptchaRecognizer()
    
    # 测试图片文件
    test_image_path = "img/captcha_1.png"
    if os.path.exists(test_image_path):
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
        
        result, confidence = recognizer.recognize_with_multiple_methods(image_data, "test_output.png")
        print(f"测试结果: {result}, 置信度: {confidence}")
    else:
        print(f"测试图片不存在: {test_image_path}")