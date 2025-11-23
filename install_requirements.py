#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖安装脚本
自动安装证书查询脚本所需的所有依赖包
"""

import subprocess
import sys
import os

def run_command(command):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def install_package(package_name, pip_name=None):
    """安装Python包"""
    if pip_name is None:
        pip_name = package_name
    
    print(f"正在安装 {package_name}...")
    success, stdout, stderr = run_command(f"{sys.executable} -m pip install {pip_name}")
    
    if success:
        print(f"✓ {package_name} 安装成功")
        return True
    else:
        print(f"✗ {package_name} 安装失败: {stderr}")
        return False

def check_package(package_name):
    """检查包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def main():
    print("=== 证书查询脚本依赖安装程序 ===")
    print("正在检查和安装所需依赖...\n")
    
    # 基础依赖包列表
    basic_packages = [
        ("playwright", "playwright"),
        ("PIL", "Pillow"),
        ("bs4", "beautifulsoup4"),
        ("cv2", "opencv-python"),
        ("numpy", "numpy")
    ]
    
    # 验证码识别相关包
    ocr_packages = [
        ("ddddocr", "ddddocr")
    ]
    
    failed_packages = []
    
    # 安装基础包
    print("1. 安装基础依赖包:")
    for package_name, pip_name in basic_packages:
        if check_package(package_name):
            print(f"✓ {package_name} 已安装")
        else:
            if not install_package(package_name, pip_name):
                failed_packages.append((package_name, pip_name))
    
    print("\n2. 安装验证码识别依赖:")
    for package_name, pip_name in ocr_packages:
        if check_package(package_name):
            print(f"✓ {package_name} 已安装")
        else:
            if not install_package(package_name, pip_name):
                failed_packages.append((package_name, pip_name))
    
    # 安装Playwright浏览器
    print("\n3. 安装Playwright浏览器:")
    if check_package("playwright"):
        print("正在安装Firefox浏览器...")
        success, stdout, stderr = run_command(f"{sys.executable} -m playwright install firefox")
        if success:
            print("✓ Firefox浏览器安装成功")
        else:
            print(f"✗ Firefox浏览器安装失败: {stderr}")
            failed_packages.append(("firefox", "playwright install firefox"))
    
    # 检查OpenCV是否需要额外配置
    print("\n4. 检查OpenCV配置:")
    try:
        import cv2
        print(f"✓ OpenCV版本: {cv2.__version__}")
    except Exception as e:
        print(f"✗ OpenCV导入失败: {e}")
        print("提示: 如果OpenCV导入失败，可能需要安装额外的系统依赖")
        if sys.platform == "darwin":  # macOS
            print("macOS用户可以尝试: brew install opencv")
        elif sys.platform.startswith("linux"):  # Linux
            print("Linux用户可以尝试: sudo apt-get install python3-opencv")
    
    # 总结安装结果
    print("\n=== 安装总结 ===")
    if failed_packages:
        print("以下包安装失败:")
        for package_name, pip_name in failed_packages:
            print(f"  - {package_name} (pip install {pip_name})")
        print("\n请手动安装失败的包，或检查网络连接后重试。")
    else:
        print("✓ 所有依赖包安装成功！")
    
    # 创建requirements.txt文件
    print("\n5. 创建requirements.txt文件:")
    requirements_content = """# 证书查询脚本依赖包
playwright>=1.40.0
Pillow>=9.0.0
beautifulsoup4>=4.11.0
opencv-python>=4.8.0
numpy>=1.21.0
ddddocr>=1.4.0

# 可选依赖
# requests>=2.28.0
# pandas>=1.5.0
"""
    
    try:
        with open("requirements.txt", "w", encoding="utf-8") as f:
            f.write(requirements_content)
        print("✓ requirements.txt 文件已创建")
        print("  后续可以使用 'pip install -r requirements.txt' 安装依赖")
    except Exception as e:
        print(f"✗ 创建requirements.txt失败: {e}")
    
    # 测试导入
    print("\n6. 测试依赖包导入:")
    test_imports = [
        "playwright",
        "PIL",
        "bs4",
        "cv2",
        "numpy",
        "ddddocr"
    ]
    
    import_success = True
    for package in test_imports:
        try:
            __import__(package)
            print(f"✓ {package} 导入成功")
        except ImportError as e:
            print(f"✗ {package} 导入失败: {e}")
            import_success = False
    
    if import_success:
        print("\n🎉 所有依赖包测试通过！可以开始使用证书查询脚本了。")
        print("\n使用方法:")
        print("  python improved_certificate_checker.py")
    else:
        print("\n⚠️  部分依赖包导入失败，请检查安装情况。")
    
    print("\n=== 使用提示 ===")
    print("1. 确保网络连接正常")
    print("2. 首次使用时，验证码识别可能需要一些时间来优化")
    print("3. 建议在查询间隔设置3-5秒，避免请求过于频繁")
    print("4. 如遇到问题，请查看生成的日志文件")

if __name__ == "__main__":
    main()