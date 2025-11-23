import asyncio
import os
import csv
import time
import json
from datetime import datetime
from playwright.async_api import async_playwright
from enhanced_captcha_recognizer import EnhancedCaptchaRecognizer

# 添加Pillow兼容性代码
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    print("警告: 未安装Pillow库或导入失败")

try:
    from bs4 import BeautifulSoup
    ENABLE_BS4 = True
except ImportError:
    ENABLE_BS4 = False
    print("警告: 未安装BeautifulSoup库，无法使用HTML解析功能")

class ImprovedCertificateChecker:
    """
    改进版证书查询器
    集成增强型验证码识别功能
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.captcha_recognizer = EnhancedCaptchaRecognizer()
        
        # 创建保存文件的目录
        self.img_dir = "img"
        self.output_dir = "output"
        self.results_dir = "查询结果"
        
        for directory in [self.img_dir, self.output_dir, self.results_dir]:
            os.makedirs(directory, exist_ok=True)
            
        print(f"已创建目录: {self.img_dir}, {self.output_dir}, {self.results_dir}")
        
        # 查询统计
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'captcha_success_rate': 0,
            'captcha_attempts': 0,
            'captcha_successes': 0,
            'total_time': 0.0,  # 总用时（秒）
            'start_time': None,  # 开始时间
            'found_results': 0,        # 查询成功且找到信息
            'not_found_results': 0,    # 查询成功但未找到信息
            'input_error_results': 0,  # 输入信息有误
            'unknown_results': 0       # 无法确定结果类型
        }
        
        # 存储查询结果
        self.query_results = []
    
    async def initialize(self, headless: bool = False):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        browser_type = os.getenv("BROWSER", "chromium").lower()
        ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        if browser_type == "firefox":
            self.browser = await playwright.firefox.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0'
        elif browser_type == "webkit":
            self.browser = await playwright.webkit.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        else:
            self.browser = await playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
        
        self.context = await self.browser.new_context(
            user_agent=ua,
            viewport={'width': 1366, 'height': 768},
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )
        
        self.page = await self.context.new_page()
        
        # 设置页面超时
        self.page.set_default_timeout(30000)
        
        await self.page.goto("https://cx.mem.gov.cn/")
        print("浏览器已初始化并打开网站首页")
        
    async def navigate_to_search_page(self, query_type: int):
        """
        导航到查询页面
        query_type: 1 - 特种作业操作证查询
                  2 - 安全生产知识和管理能力考核合格信息查询
        """
        await self.page.wait_for_load_state("networkidle")
        
        # 检查是否已经在正确的查询页面
        current_url = self.page.url
        if query_type == 1 and "special" in current_url:
            print("已在特种作业操作证查询页面，无需重新导航")
            return
        elif query_type == 2 and "safety" in current_url:
            print("已在安全生产知识和管理能力考核查询页面，无需重新导航")
            return
        
        # 如果在错误的查询页面或其他页面，需要导航到正确页面
        # 但不要直接返回首页，而是直接导航到目标页面
            
        if query_type == 1:
            text_to_click = "特种作业操作证查询 进入查询"
            print("正在导航到特种作业操作证查询页面")
        else:
            text_to_click = "安全生产知识和管理能力 考核合格信息查询 进入查询"
            print("正在导航到安全生产知识和管理能力考核合格信息查询页面")
            
        # 优先尝试直接URL导航，避免点击按钮的不稳定性
        try:
            if query_type == 1:
                await self.page.goto("https://cx.mem.gov.cn/special?index=0")
            else:
                await self.page.goto("https://cx.mem.gov.cn/safety?index=1")
            print("通过直接URL导航成功")
        except Exception as e:
            print(f"直接URL导航失败，尝试点击按钮: {e}")
            try:
                await self.page.click(f"text={text_to_click}")
            except Exception:
                try:
                    await self.page.click("text=进入查询", timeout=5000)
                except Exception as e:
                    print(f"无法找到并点击查询按钮: {str(e)}")
                    # 最后的兜底方案
                    if query_type == 1:
                        await self.page.goto("https://cx.mem.gov.cn/special?index=0")
                    else:
                        await self.page.goto("https://cx.mem.gov.cn/safety?index=1")
                    
        await self.page.wait_for_load_state("networkidle")
        print("已成功导航到查询页面")
        
    async def select_certificate_type(self, cert_type: str):
        """选择证件类型"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                print(f"第 {attempt + 1} 次尝试选择证件类型: {cert_type}")
                
                # 等待页面加载完成，设置5秒超时
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                except Exception as e:
                    print(f"页面加载超时，继续尝试: {e}")
                
                # 多种选择器尝试点击证件类型下拉框
                dropdown_selectors = [
                    "input[placeholder='请选择证件类型']",
                    "input[placeholder*='证件类型']",
                    ".ant-select-selector",
                    ".ant-select",
                    "[class*='select']"
                ]
                
                dropdown_clicked = False
                for selector in dropdown_selectors:
                    try:
                        # 设置5秒超时查找元素
                        dropdown = await self.page.query_selector(selector)
                        if dropdown:
                            # 设置5秒超时点击
                            await dropdown.click(timeout=5000)
                            dropdown_clicked = True
                            print(f"成功点击下拉框: {selector}")
                            break
                    except Exception as e:
                        print(f"选择器 {selector} 失败: {e}")
                        continue
                
                if not dropdown_clicked:
                    raise Exception("无法找到证件类型下拉框")
                
                # 减少等待时间，等待下拉选项出现
                await self.page.wait_for_timeout(500)
                
                # 多种方式尝试选择证件类型
                option_selectors = [
                    f"text='{cert_type}'",
                    f"[title='{cert_type}']",
                    f"div:has-text('{cert_type}')",
                    f".ant-select-item:has-text('{cert_type}')",
                    f"li:has-text('{cert_type}')"
                ]
                
                option_selected = False
                for selector in option_selectors:
                    try:
                        # 设置5秒超时查找选项
                        option = await self.page.query_selector(selector)
                        if option:
                            # 设置5秒超时点击选项
                            await option.click(timeout=5000)
                            option_selected = True
                            print(f"成功选择证件类型: {cert_type}")
                            break
                    except Exception as e:
                        print(f"选项选择器 {selector} 失败: {e}")
                        continue
                
                if option_selected:
                    # 验证选择是否成功，减少等待时间
                    await self.page.wait_for_timeout(300)
                    return
                else:
                    raise Exception(f"无法找到证件类型选项: {cert_type}")
                    
            except Exception as e:
                print(f"第 {attempt + 1} 次选择证件类型失败: {str(e)}")
                if attempt < max_attempts - 1:
                    print("等待1秒后重试...")
                    await self.page.wait_for_timeout(1000)
                    # 尝试刷新页面或重新导航，设置超时
                    try:
                        await self.page.reload(timeout=5000)
                        await self.page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception as reload_e:
                        print(f"页面刷新失败: {reload_e}")
                else:
                    print(f"选择证件类型最终失败: {str(e)}")
                    raise
            
    async def input_certificate_info(self, cert_number: str, name: str):
        """输入证件号码和姓名"""
        try:
            # 清空之前的输入
            await self.page.fill("input[placeholder='请输入证件号码']", "")
            await self.page.fill("input[placeholder='请输入姓名']", "")
            
            # 输入新的信息
            await self.page.fill("input[placeholder='请输入证件号码']", cert_number)
            await self.page.fill("input[placeholder='请输入姓名']", name)
            print(f"已输入证件号码和姓名")
        except Exception as e:
            print(f"输入证件信息时出错: {str(e)}")
            raise
            
    async def solve_captcha_with_retry(self, max_attempts: int = 5) -> bool:
        """
        使用增强识别器解决验证码，支持重试
        
        Args:
            max_attempts: 最大尝试次数
            
        Returns:
            是否成功解决验证码
        """
        for attempt in range(max_attempts):
            try:
                print(f"第 {attempt + 1} 次尝试识别验证码")
                self.stats['captcha_attempts'] += 1
                
                # 使用增强识别器获取验证码
                timestamp = int(time.time())
                filename = f"captcha_{timestamp}_{attempt}.png"
                
                captcha_result = await self.captcha_recognizer.get_captcha_from_page(
                    self.page, filename
                )
                
                if not captcha_result[0]:  # 识别失败
                    if attempt < max_attempts - 1:
                        # 刷新验证码
                        try:
                            await self.page.click('.yzm-style-img')
                            await self.page.wait_for_timeout(1500)
                            print("已刷新验证码")
                        except Exception as e:
                            print(f"刷新验证码失败: {e}")
                        continue
                    else:
                        print("验证码识别失败，跳过当前证件")
                        return False
                
                captcha_text = captcha_result[0]
                
                # 输入验证码
                await self._input_captcha(captcha_text)
                
                # 提交查询并检查结果
                if await self._submit_and_check():
                    print(f"验证码识别成功: {captcha_text}")
                    self.stats['captcha_successes'] += 1
                    return True
                else:
                    print(f"验证码 {captcha_text} 可能错误，尝试重新识别")
                    if attempt < max_attempts - 1:
                        # 刷新验证码
                        try:
                            await self.page.click('.yzm-style-img')
                            await self.page.wait_for_timeout(1500)
                        except Exception:
                            pass
                    
            except Exception as e:
                print(f"第 {attempt + 1} 次验证码处理失败: {e}")
                
        print(f"经过 {max_attempts} 次尝试，验证码识别失败")
        return False
        
    async def _input_captcha(self, captcha_text: str):
        """输入验证码"""
        selectors = [
            "input[placeholder='请输入验证码']",
            "input.ant-input[placeholder*='验证码']",
            "input[placeholder*='验证码']"
        ]
        
        captcha_input = None
        for selector in selectors:
            try:
                captcha_input = await self.page.query_selector(selector)
                if captcha_input:
                    break
            except Exception:
                continue
                
        if not captcha_input:
            raise Exception("无法找到验证码输入框")
            
        await captcha_input.fill("")
        await self.page.wait_for_timeout(300)
        await captcha_input.fill(captcha_text)
        await self.page.wait_for_timeout(500)
        
    async def _submit_and_check(self) -> bool:
        """提交查询并检查是否成功（区分验证码错误和查询结果）"""
        try:
            # 记录当前URL，用于检测页面跳转
            current_url = self.page.url
            
            # 点击查询按钮
            await self.page.click("button:has-text('查询')")
            
            # 等待页面响应
            await self.page.wait_for_timeout(2000)
            
            # 首先检查是否有验证码相关的错误提示
            captcha_error_indicators = [
                "验证码错误", "验证码不正确", "验证码输入错误", "验证码有误",
                "请输入正确的验证码", "验证码不匹配", "验证码失效"
            ]
            
            page_content = await self.page.content()
            for error_text in captcha_error_indicators:
                if error_text in page_content:
                    print(f"检测到验证码错误提示: {error_text}")
                    return False
            
            # 检查特定的验证码错误元素
            error_selectors = [
                ".ant-message-error",
                ".ant-notification-notice-message",
                "[class*='error']",
                "[class*='message']"
            ]
            
            for selector in error_selectors:
                try:
                    error_element = await self.page.query_selector(selector)
                    if error_element:
                        error_text = await error_element.inner_text()
                        if "验证码" in error_text:
                            print(f"检测到验证码错误元素: {error_text}")
                            return False
                except Exception:
                    continue
            
            # 检查页面是否发生跳转（URL变化）
            new_url = self.page.url
            if new_url != current_url:
                print(f"页面已跳转: {current_url} -> {new_url}")
                return True
            
            # 检查是否出现了结果相关的元素（即使是"未找到"的结果）
            result_indicators = [
                "table",
                ".ant-table",
                ".ant-result",
                "[class*='result']",
                "[class*='content']"
            ]
            
            for indicator in result_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element:
                        print(f"检测到结果元素: {indicator}")
                        return True
                except Exception:
                    continue
            
            # 检查页面内容是否包含查询结果相关的文本
            result_texts = [
                "暂无数据", "未查询到相关信息", "没有找到", "无相关记录",
                "查询结果", "证书信息", "个人信息"
            ]
            
            for result_text in result_texts:
                if result_text in page_content:
                    print(f"检测到结果文本: {result_text}")
                    return True
            
            # 如果没有明确的验证码错误，也没有结果，可能是页面加载问题
            print("未检测到明确的验证码错误或查询结果")
            return False
            
        except Exception as e:
            print(f"提交查询时出错: {e}")
            return False
            

            
    async def get_query_result(self, cert_number: str, name: str) -> dict:
        """获取查询结果 - 增强版"""
        import re
        
        try:
            # 确保页面完全加载
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(3000)  # 额外等待动态内容
            
            # 检查是否还在加载中
            loading_selectors = [".loading", ".spinner", "[class*='loading']", ".ant-spin"]
            for selector in loading_selectors:
                try:
                    if await self.page.query_selector(selector):
                        await self.page.wait_for_selector(selector, state="detached", timeout=10000)
                except Exception:
                    continue
            
            result = {
                'cert_number': cert_number,
                'name': name,
                'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'unknown',
                'data': None,
                'screenshots': []
            }
            
            # 保存页面截图
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.output_dir, f"{name}_{cert_number[-6:]}_{timestamp}_截图.png")
            await self.page.screenshot(path=screenshot_path, full_page=True)
            result['screenshots'].append(screenshot_path)
            
            # 获取页面内容
            page_content = await self.page.content()
            
            # 第一步：检查是否有错误提示（查询失败情况）
            error_confidence = await self._check_error_indicators(page_content)
            if error_confidence['has_error']:
                result['status'] = 'input_error'
                result['data'] = f'查询失败: {error_confidence["message"]}'
                print(f"检测到输入错误: {error_confidence['message']}")
                return result
            
            # 第二步：检查是否为无结果页面
            no_result_confidence = await self._check_no_result_indicators(page_content)
            if no_result_confidence['is_no_result']:
                result['status'] = 'not_found'
                result['data'] = '查询成功，但未查询到相关信息'
                print(f"查询成功，但未找到相关信息: {no_result_confidence['message']}")
                return result
            
            # 第三步：检查是否有查询结果数据
            result_confidence = await self._check_result_data()
            if result_confidence['has_data']:
                result['status'] = 'found'
                result['data'] = result_confidence['data']
                
                # 保存结果截图
                if result_confidence['element']:
                    try:
                        result_screenshot_path = os.path.join(self.output_dir, f"{name}_{cert_number[-6:]}_{timestamp}_结果截图.png")
                        await result_confidence['element'].screenshot(path=result_screenshot_path)
                        result['screenshots'].append(result_screenshot_path)
                    except Exception:
                        pass
                
                # 转换为结构化数据
                if ENABLE_BS4 and result_confidence['data_type'] == 'table':
                    structured_data = self._parse_table_data(result_confidence['data'])
                    result['structured_data'] = structured_data
                
                print(f"查询成功，找到相关信息: {result_confidence['data_type']}")
                return result
            
            # 第四步：如果都无法确定，提供详细的页面分析
            page_analysis = await self._analyze_page_structure()
            result['status'] = 'unknown'
            result['data'] = f'查询完成，但无法解析结果类型。页面分析: {page_analysis}'
            print(f"查询完成，但无法确定结果类型。页面分析: {page_analysis}")
            return result
            
            # 保存结果为JSON
            json_path = os.path.join(self.results_dir, f"{name}_{cert_number[-6:]}_{timestamp}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            return result
            
        except Exception as e:
            print(f"获取查询结果时出错: {e}")
            return {
                'cert_number': cert_number,
                'name': name,
                'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'error',
                'data': str(e),
                'screenshots': []
            }
    
    async def _check_error_indicators(self, page_content: str) -> dict:
        """检查错误指示器"""
        import re
        
        # 扩展的错误关键词
        error_indicators = [
            "信息输入有误", "输入信息有误", "证件号码格式错误", "姓名格式错误",
            "请检查输入信息", "输入的信息不正确", "证件信息错误", "查询条件错误",
            "参数错误", "格式不正确", "请核实输入信息", "信息不匹配",
            "验证失败", "校验失败", "数据格式错误", "请重新输入",
            "身份证号码错误", "姓名不匹配", "证件类型错误", "查询参数无效"
        ]
        
        # 使用正则表达式进行更灵活的匹配
        error_patterns = [
            r"(信息|数据|参数|格式).*(错误|有误|不正确|无效)",
            r"(输入|填写).*(错误|有误|不正确)",
            r"(验证|校验|检查).*(失败|错误)",
            r"请.*(检查|核实|重新输入|修正)"
        ]
        
        # 检查文本内容
        for error_text in error_indicators:
            if error_text in page_content:
                return {'has_error': True, 'message': error_text, 'confidence': 0.9}
        
        # 检查正则表达式模式
        for pattern in error_patterns:
            matches = re.findall(pattern, page_content)
            if matches:
                return {'has_error': True, 'message': f'匹配到错误模式: {"".join(matches[0])}', 'confidence': 0.8}
        
        # 检查特定的错误元素
        error_selectors = [
            ".ant-message-error", ".error-message", "[class*='error']",
            ".ant-alert-error", ".warning", "[class*='warning']",
            ".el-message--error", ".van-toast--fail", ".weui-toast_fail"
        ]
        
        for selector in error_selectors:
            try:
                error_element = await self.page.query_selector(selector)
                if error_element:
                    error_text = await error_element.inner_text()
                    if error_text and len(error_text.strip()) > 0:
                        error_keywords = ["错误", "失败", "格式", "输入", "信息", "验证", "校验"]
                        if any(keyword in error_text for keyword in error_keywords):
                            return {'has_error': True, 'message': error_text.strip(), 'confidence': 0.85}
            except Exception:
                continue
        
        return {'has_error': False, 'message': '', 'confidence': 0}
    
    async def _check_no_result_indicators(self, page_content: str) -> dict:
        """检查无结果指示器"""
        import re
        
        # 扩展的无结果关键词
        no_result_indicators = [
            "暂无数据", "未查询到相关信息", "没有找到", "无相关记录",
            "查询结果为空", "暂无相关信息", "未找到匹配记录", "无查询结果",
            "暂时没有数据", "没有相关数据", "查无此人", "无此记录",
            "抱歉，未找到", "很遗憾，没有查到", "暂无匹配信息"
        ]
        
        # 使用正则表达式进行更灵活的匹配
        no_result_patterns = [
            r"(暂无|没有|未找到|无相关).*(数据|信息|记录|结果)",
            r"查询.*(无结果|为空|失败|不到)",
            r"(抱歉|很遗憾).*(未找到|没有查到|无相关)",
            r"(暂时|目前).*(没有|无).*(数据|信息|记录)"
        ]
        
        # 检查文本内容
        for no_result_text in no_result_indicators:
            if no_result_text in page_content:
                return {'is_no_result': True, 'message': no_result_text, 'confidence': 0.9}
        
        # 检查正则表达式模式
        for pattern in no_result_patterns:
            matches = re.findall(pattern, page_content)
            if matches:
                return {'is_no_result': True, 'message': f'匹配到无结果模式: {"".join(matches[0])}', 'confidence': 0.8}
        
        # 检查特定的无结果元素
        no_result_selectors = [
            ".no-data", ".empty-result", ".no-record", "[class*='empty']",
            "[class*='no-data']", ".ant-empty", ".el-empty", ".van-empty",
            ".weui-loadmore_line", ".no-result", "[class*='no-result']"
        ]
        
        for selector in no_result_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    element_text = await element.inner_text()
                    if element_text and len(element_text.strip()) > 0:
                        return {'is_no_result': True, 'message': f'发现无结果元素: {element_text.strip()}', 'confidence': 0.85}
                    else:
                        # 即使没有文本，元素存在也可能表示无结果
                        return {'is_no_result': True, 'message': '发现无结果元素', 'confidence': 0.7}
            except Exception:
                continue
        
        return {'is_no_result': False, 'message': '', 'confidence': 0}
    
    async def _check_result_data(self) -> dict:
        """检查是否有查询结果数据"""
        # 多种可能的结果展示结构
        result_selectors = [
            # 表格结构
            {"selector": "table", "type": "table", "priority": 0.9},
            {"selector": ".table", "type": "table", "priority": 0.85},
            {"selector": "[class*='table']", "type": "table", "priority": 0.8},
            
            # 列表结构
            {"selector": ".result-list", "type": "list", "priority": 0.85},
            {"selector": ".data-list", "type": "list", "priority": 0.85},
            {"selector": ".info-list", "type": "list", "priority": 0.8},
            {"selector": "[class*='result']", "type": "list", "priority": 0.7},
            {"selector": "[class*='data']", "type": "list", "priority": 0.7},
            
            # 卡片结构
            {"selector": ".card-list", "type": "card", "priority": 0.8},
            {"selector": ".info-card", "type": "card", "priority": 0.8},
            {"selector": "[class*='card']", "type": "card", "priority": 0.7},
            
            # 详情结构
            {"selector": ".detail-info", "type": "detail", "priority": 0.8},
            {"selector": ".certificate-info", "type": "detail", "priority": 0.85},
            {"selector": "[class*='detail']", "type": "detail", "priority": 0.7},
            {"selector": "[class*='info']", "type": "detail", "priority": 0.6}
        ]
        
        best_match = None
        highest_confidence = 0
        
        for item in result_selectors:
            try:
                element = await self.page.query_selector(item["selector"])
                if element:
                    # 检查元素是否包含实际数据
                    element_text = await element.inner_text()
                    element_html = await element.inner_html()
                    
                    # 排除空元素或只包含标题的元素
                    if (element_text and len(element_text.strip()) > 10 and 
                        not self._is_empty_result_element(element_text)):
                        
                        confidence = item["priority"]
                        
                        # 根据内容质量调整置信度
                        if len(element_text.strip()) > 50:
                            confidence += 0.1
                        if "证书" in element_text or "证件" in element_text or "姓名" in element_text:
                            confidence += 0.1
                        if element_html and ("<td>" in element_html or "<li>" in element_html):
                            confidence += 0.05
                        
                        if confidence > highest_confidence:
                            highest_confidence = confidence
                            best_match = {
                                'has_data': True,
                                'data': element_html,
                                'data_type': item["type"],
                                'element': element,
                                'confidence': confidence,
                                'text_preview': element_text[:100] + "..." if len(element_text) > 100 else element_text
                            }
            except Exception:
                continue
        
        if best_match:
            return best_match
        
        return {'has_data': False, 'data': None, 'data_type': None, 'element': None, 'confidence': 0}
    
    def _is_empty_result_element(self, text: str) -> bool:
        """判断元素是否为空结果元素"""
        empty_indicators = [
            "暂无数据", "没有数据", "无数据", "空", "无结果",
            "loading", "加载中", "请稍候", "查询中"
        ]
        
        text_lower = text.lower().strip()
        return any(indicator in text_lower for indicator in empty_indicators)
    
    async def _analyze_page_structure(self) -> str:
        """分析页面结构，用于调试"""
        try:
            # 获取页面的主要结构信息
            analysis = []
            
            # 检查页面标题
            title = await self.page.title()
            if title:
                analysis.append(f"页面标题: {title}")
            
            # 检查主要容器元素
            containers = [".container", ".main", ".content", "#main", "#content"]
            for container in containers:
                try:
                    element = await self.page.query_selector(container)
                    if element:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 0:
                            analysis.append(f"发现容器 {container}: {text[:50]}...")
                            break
                except Exception:
                    continue
            
            # 检查是否有表单元素
            forms = await self.page.query_selector_all("form")
            if forms:
                analysis.append(f"发现 {len(forms)} 个表单")
            
            # 检查是否有按钮
            buttons = await self.page.query_selector_all("button")
            if buttons:
                analysis.append(f"发现 {len(buttons)} 个按钮")
            
            # 检查页面URL
            url = self.page.url
            analysis.append(f"当前URL: {url}")
            
            return "; ".join(analysis) if analysis else "无法分析页面结构"
            
        except Exception as e:
            return f"页面结构分析失败: {str(e)}"
            
    def _parse_table_data(self, table_html: str) -> list:
        """解析表格数据为结构化格式"""
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            table = soup.find('table')
            
            if not table:
                return []
                
            rows = []
            for tr in table.find_all('tr'):
                row = []
                for cell in tr.find_all(['td', 'th']):
                    cell_text = cell.get_text(strip=True)
                    row.append(cell_text)
                if row:
                    rows.append(row)
                    
            return rows
            
        except Exception as e:
            print(f"解析表格数据失败: {e}")
            return []
            
    async def query_single_certificate(self, cert_type: str, cert_number: str, name: str, query_type: int = 1) -> dict:
        """查询单个证书"""
        # 开始计时
        start_time = time.time()
        
        # 如果这是第一次查询，记录开始时间
        if self.stats['start_time'] is None:
            self.stats['start_time'] = start_time
        
        try:
            self.stats['total_queries'] += 1
            print(f"\n开始查询: {name} - {cert_number}")
            
            # 导航到查询页面计时
            nav_start = time.time()
            await self.navigate_to_search_page(query_type)
            nav_time = time.time() - nav_start
            print(f"导航到查询页面耗时: {nav_time:.2f}秒")
            
            # 选择证件类型计时
            select_start = time.time()
            await self.select_certificate_type(cert_type)
            select_time = time.time() - select_start
            print(f"选择证件类型耗时: {select_time:.2f}秒")
            
            # 输入证件信息计时
            input_start = time.time()
            await self.input_certificate_info(cert_number, name)
            input_time = time.time() - input_start
            print(f"输入证件信息耗时: {input_time:.2f}秒")
            
            # 解决验证码计时
            captcha_start = time.time()
            if await self.solve_captcha_with_retry():
                captcha_time = time.time() - captcha_start
                print(f"验证码识别耗时: {captcha_time:.2f}秒")
                
                # 获取查询结果计时
                result_start = time.time()
                result = await self.get_query_result(cert_number, name)
                result_time = time.time() - result_start
                print(f"获取查询结果耗时: {result_time:.2f}秒")
                
                # 计算总耗时
                total_time = time.time() - start_time
                result['query_duration'] = {
                    'total_time': round(total_time, 2),
                    'navigation_time': round(nav_time, 2),
                    'selection_time': round(select_time, 2),
                    'input_time': round(input_time, 2),
                    'captcha_time': round(captcha_time, 2),
                    'result_time': round(result_time, 2)
                }
                
                # 更新详细统计
                if result['status'] == 'found':
                    self.stats['successful_queries'] += 1
                    self.stats['found_results'] += 1
                    print(f"查询成功(找到信息): {result['status']}，总耗时: {total_time:.2f}秒")
                elif result['status'] == 'not_found':
                    self.stats['successful_queries'] += 1
                    self.stats['not_found_results'] += 1
                    print(f"查询成功(未找到信息): {result['status']}，总耗时: {total_time:.2f}秒")
                elif result['status'] == 'input_error':
                    self.stats['failed_queries'] += 1
                    self.stats['input_error_results'] += 1
                    print(f"查询失败(输入错误): {result['status']}，总耗时: {total_time:.2f}秒")
                elif result['status'] == 'unknown':
                    self.stats['failed_queries'] += 1
                    self.stats['unknown_results'] += 1
                    print(f"查询完成(结果未知): {result['status']}，总耗时: {total_time:.2f}秒")
                else:
                    self.stats['failed_queries'] += 1
                    print(f"查询失败: {result['status']}，总耗时: {total_time:.2f}秒")
                
                # 更新总用时
                if self.stats['start_time']:
                    self.stats['total_time'] = time.time() - self.stats['start_time']
                
                # 将查询结果添加到结果列表
                self.query_results.append(result)
                
                # 查询完成后返回证照类型选择页面
                await self.return_to_certificate_selection_page(query_type)
                return result
            else:
                captcha_time = time.time() - captcha_start
                total_time = time.time() - start_time
                print(f"验证码识别失败，耗时: {captcha_time:.2f}秒，总耗时: {total_time:.2f}秒")
                
                self.stats['failed_queries'] += 1
                # 更新总用时
                if self.stats['start_time']:
                    self.stats['total_time'] = time.time() - self.stats['start_time']
                # 验证码失败后也返回证照类型选择页面
                await self.return_to_certificate_selection_page(query_type)
                
                captcha_failed_result = {
                    'cert_number': cert_number,
                    'name': name,
                    'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'captcha_failed',
                    'data': '验证码识别失败',
                    'screenshots': [],
                    'query_duration': {
                        'total_time': round(total_time, 2),
                        'navigation_time': round(nav_time, 2),
                        'selection_time': round(select_time, 2),
                        'input_time': round(input_time, 2),
                        'captcha_time': round(captcha_time, 2),
                        'result_time': 0
                    }
                }
                
                # 将验证码失败结果添加到结果列表
                self.query_results.append(captcha_failed_result)
                return captcha_failed_result
                
        except Exception as e:
            total_time = time.time() - start_time
            self.stats['failed_queries'] += 1
            print(f"查询过程出错: {e}，总耗时: {total_time:.2f}秒")
            # 更新总用时
            if self.stats['start_time']:
                self.stats['total_time'] = time.time() - self.stats['start_time']
            # 出错后也尝试返回证照类型选择页面
            try:
                await self.return_to_certificate_selection_page(query_type)
            except Exception:
                pass
            
            error_result = {
                'cert_number': cert_number,
                'name': name,
                'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'error',
                'data': str(e),
                'screenshots': [],
                'query_duration': {
                    'total_time': round(total_time, 2),
                    'navigation_time': 0,
                    'selection_time': 0,
                    'input_time': 0,
                    'captcha_time': 0,
                    'result_time': 0
                }
            }
            
            # 将错误结果添加到结果列表
            self.query_results.append(error_result)
            return error_result
            
    async def batch_query_from_csv(self, csv_file: str, cert_type: str = "身份证", default_query_type: int = 1, delay: int = 3) -> list:
        """从CSV文件批量查询
        
        CSV文件格式:
        证件号码,姓名,查询类型
        110101199001011234,张三,1
        310101199201022345,李四,2
        
        查询类型说明:
        1 - 特种作业操作证查询
        2 - 安全生产知识和管理能力考核合格信息查询
        
        如果CSV中没有查询类型列，则使用default_query_type
        """
        results = []
        
        try:
            # 记录批量查询开始时间
            import time
            batch_start_time = time.time()
            self.stats['start_time'] = batch_start_time
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                certificates = list(reader)
                
            print(f"从 {csv_file} 读取到 {len(certificates)} 条记录")
            
            for i, cert in enumerate(certificates, 1):
                print(f"\n进度: {i}/{len(certificates)}")
                
                cert_number = cert.get('证件号码', '').strip()
                name = cert.get('姓名', '').strip()
                
                # 跳过表头数据（如果证件号码字段就是"证件号码"，说明这是表头）
                if cert_number == '证件号码' or name == '姓名':
                    print(f"跳过表头记录: {cert}")
                    continue
                
                # 从CSV中读取查询类型，如果没有则使用默认值
                query_type_str = cert.get('查询类型', str(default_query_type)).strip()
                try:
                    query_type = int(query_type_str)
                    if query_type not in [1, 2]:
                        print(f"警告: 无效的查询类型 {query_type}，使用默认值 {default_query_type}")
                        query_type = default_query_type
                except ValueError:
                    print(f"警告: 查询类型格式错误 '{query_type_str}'，使用默认值 {default_query_type}")
                    query_type = default_query_type
                
                if not cert_number or not name:
                    print(f"跳过无效记录: {cert}")
                    continue
                
                print(f"查询: {name} ({cert_number}) - 查询类型: {query_type}")
                result = await self.query_single_certificate(cert_type, cert_number, name, query_type)
                results.append(result)
                
                # 延时避免请求过于频繁
                if i < len(certificates):
                    print(f"等待 {delay} 秒后继续下一个查询...")
                    await asyncio.sleep(delay)
                    
            # 计算总用时
            if self.stats['start_time']:
                self.stats['total_time'] = time.time() - self.stats['start_time']
                print(f"\n批量查询总用时: {self.stats['total_time']:.2f}秒")
            
            # 保存批量查询结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_result_path = os.path.join(self.results_dir, f"batch_query_results_{timestamp}.json")
            
            with open(batch_result_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_count': len(results),
                    'statistics': self.get_statistics(),
                    'results': results
                }, f, ensure_ascii=False, indent=2)
                
            print(f"\n批量查询完成，结果已保存到: {batch_result_path}")
            return results
            
        except Exception as e:
            print(f"批量查询失败: {e}")
            return results
            
    def get_statistics(self) -> dict:
        """获取查询统计信息"""
        if self.stats['captcha_attempts'] > 0:
            self.stats['captcha_success_rate'] = self.stats['captcha_successes'] / self.stats['captcha_attempts']
        
        return self.stats.copy()
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            print("浏览器已关闭")
            
        # 打印统计信息
        stats = self.get_statistics()
        print("\n=== 查询统计 ===")
        print(f"总查询数: {stats['total_queries']}")
        print(f"成功查询: {stats['successful_queries']}")
        print(f"  - 找到信息: {stats['found_results']}")
        print(f"  - 未找到信息: {stats['not_found_results']}")
        print(f"失败查询: {stats['failed_queries']}")
        print(f"  - 输入信息错误: {stats['input_error_results']}")
        print(f"  - 结果类型未知: {stats['unknown_results']}")
        print(f"  - 其他失败: {stats['failed_queries'] - stats['input_error_results'] - stats['unknown_results']}")
        print(f"验证码识别成功率: {stats['captcha_success_rate']:.2%}")
        if stats['total_time'] > 0:
            print(f"总用时: {stats['total_time']:.2f}秒")
            if stats['total_queries'] > 0:
                avg_time = stats['total_time'] / stats['total_queries']
                print(f"平均每次查询用时: {avg_time:.2f}秒")

    async def return_to_homepage(self):
        """返回首页"""
        try:
            print("正在返回首页...")
            # 尝试点击返回按钮
            back_selectors = [
                "button:has-text('返回')",
                "a:has-text('返回')",
                "[class*='back']",
                "button:has-text('首页')",
                "a:has-text('首页')"
            ]
            
            for selector in back_selectors:
                try:
                    back_button = await self.page.query_selector(selector)
                    if back_button:
                        await back_button.click()
                        await self.page.wait_for_load_state("networkidle")
                        print("已通过返回按钮回到首页")
                        return
                except Exception:
                    continue
            
            # 如果没有找到返回按钮，直接导航到首页
            await self.page.goto("https://cx.mem.gov.cn/")
            await self.page.wait_for_load_state("networkidle")
            print("已直接导航到首页")
            
        except Exception as e:
            print(f"返回首页时出错: {e}")
            # 最后的兜底方案：强制刷新到首页
            try:
                await self.page.goto("https://cx.mem.gov.cn/")
                await self.page.wait_for_load_state("networkidle")
            except Exception:
                pass
                
    async def return_to_certificate_selection_page(self, query_type: int):
        """返回证照类型选择页面"""
        try:
            print("正在返回证照类型选择页面...")
            
            # 首先尝试点击返回按钮回到证照类型选择页面
            back_selectors = [
                "button:has-text('返回')",
                "a:has-text('返回')",
                "[class*='back']",
                "button:has-text('重新查询')",
                "a:has-text('重新查询')"
            ]
            
            for selector in back_selectors:
                try:
                    back_button = await self.page.query_selector(selector)
                    if back_button:
                        await back_button.click()
                        await self.page.wait_for_load_state("networkidle")
                        
                        # 检查是否已经回到证照类型选择页面
                        if await self._is_certificate_selection_page():
                            print("已通过返回按钮回到证照类型选择页面")
                            return
                        else:
                            # 如果不是证照类型选择页面，继续尝试其他方法
                            break
                except Exception:
                    continue
            
            # 如果返回按钮无效，直接重新导航到查询页面
            print("返回按钮无效，重新导航到查询页面...")
            await self.navigate_to_search_page(query_type)
            
        except Exception as e:
            print(f"返回证照类型选择页面时出错: {e}")
            # 兜底方案：重新导航到查询页面
            try:
                await self.navigate_to_search_page(query_type)
            except Exception:
                pass
                
    async def _is_certificate_selection_page(self) -> bool:
        """检查当前是否在证照类型选择页面"""
        try:
            # 检查页面是否包含证照类型选择的关键元素
            selectors_to_check = [
                "select[name*='证件']",
                "select[name*='cert']",
                "option:has-text('身份证')",
                "option:has-text('护照')",
                "text=证件类型",
                "text=证件号码",
                "input[placeholder*='证件']",
                "input[placeholder*='身份证']"
            ]
            
            for selector in selectors_to_check:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        return True
                except Exception:
                    continue
                    
            return False
            
        except Exception:
            return False
    
    def save_results(self) -> tuple:
        """
        保存查询结果为JSON和CSV格式
        
        Returns:
            tuple: (json_file_path, csv_file_path)
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存为JSON格式
            json_filename = f"query_results_{timestamp}.json"
            json_path = os.path.join(self.results_dir, json_filename)
            
            # 收集所有查询结果
            results_data = {
                'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'statistics': self.get_statistics(),
                'query_results': getattr(self, 'query_results', [])
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            # 保存为CSV格式
            csv_filename = f"query_results_{timestamp}.csv"
            csv_path = os.path.join(self.results_dir, csv_filename)
            
            if hasattr(self, 'query_results') and self.query_results:
                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'cert_number', 'name', 'status', 'query_time', 
                        'response_time', 'captcha_attempts', 'error_message'
                    ])
                    writer.writeheader()
                    
                    for result in self.query_results:
                        # 提取基本信息
                        row = {
                            'cert_number': result.get('cert_number', ''),
                            'name': result.get('name', ''),
                            'status': result.get('status', ''),
                            'query_time': result.get('query_time', ''),
                            'response_time': result.get('response_time', ''),
                            'captcha_attempts': result.get('captcha_attempts', ''),
                            'error_message': result.get('error_message', '')
                        }
                        writer.writerow(row)
            else:
                # 如果没有查询结果，创建空的CSV文件
                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'cert_number', 'name', 'status', 'query_time', 
                        'response_time', 'captcha_attempts', 'error_message'
                    ])
                    writer.writeheader()
            
            print(f"\n查询结果已保存:")
            print(f"JSON文件: {json_path}")
            print(f"CSV文件: {csv_path}")
            
            return json_path, csv_path
            
        except Exception as e:
            print(f"保存查询结果时出错: {e}")
            return None, None

# 使用示例
async def main():
    checker = ImprovedCertificateChecker()
    
    try:
        await checker.initialize(headless=False)
        
        # 单个查询示例
        # result = await checker.query_single_certificate(
        #     cert_type="身份证",
        #     cert_number="110101199001011234",
        #     name="张三",
        #     query_type=1
        # )
        # print(f"查询结果: {result}")
        
        # 批量查询示例
        csv_file = "证书查询样例.csv"
        if os.path.exists(csv_file):
            results = await checker.batch_query_from_csv(
                csv_file=csv_file,
                cert_type="身份证",
                default_query_type=1,  # 当CSV中没有查询类型列时的默认值
                delay=3
            )
            print(f"批量查询完成，共处理 {len(results)} 条记录")
        else:
            print(f"CSV文件不存在: {csv_file}")
            
    finally:
        await checker.close()

if __name__ == "__main__":
    asyncio.run(main())
