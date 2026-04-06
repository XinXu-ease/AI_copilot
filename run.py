#!/usr/bin/env python
"""
启动脚本：同时启动 API 后端和打开前端
"""
import os
import sys
import subprocess
import webbrowser
import time
import socket

def check_port_available(port):
    """检查端口是否可用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result != 0

def find_available_port(start_port, end_port=start_port + 10):
    """找到可用端口"""
    for port in range(start_port, end_port):
        if check_port_available(port):
            return port
    return None

def main():
    print("=" * 70)
    print("🚀 AI Product Team Copilot - HTML Version")
    print("=" * 70)
    print()
    
    # 检查依赖
    print("📦 检查依赖...")
    try:
        import flask
        import flask_cors
        import pydantic
        from langgraph.graph import StateGraph
        print("✅ 所有依赖已安装")
    except ImportError as e:
        print(f"❌ 缺少依赖：{e}")
        print("   请运行：pip install -r requirements.txt")
        return
    
    print()
    
    # 检查后端端口
    print("🔍 检查后端端口 5000...")
    if not check_port_available(5000):
        print("⚠️  端口 5000 已被占用，尝试寻找其他端口...")
        backend_port = find_available_port(5000, 5010)
        if backend_port is None:
            print("❌ 无法找到可用端口（5000-5009）")
            print("   请关闭占用端口的其他程序")
            return
        print(f"✅ 使用端口 {backend_port}")
    else:
        backend_port = 5000
        print(f"✅ 端口 {backend_port} 可用")
    
    print()
    
    # 启动 Flask API 后端
    print(f"📡 启动 API 后端...")
    print(f"   → 监听地址: http://0.0.0.0:{backend_port}")
    print(f"   → 前端访问: http://localhost:{backend_port}/api")
    print()
    
    # 如果不是 5000，需要修改启动配置
    env = os.environ.copy()
    env['FLASK_PORT'] = str(backend_port)
    
    try:
        backend_process = subprocess.Popen(
            [sys.executable, "app_api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )
        print("✅ 后端启动中...")
    except Exception as e:
        print(f"❌ 启动后端失败：{e}")
        return
    
    # 等待后端启动
    print("   等待后端初始化...")
    time.sleep(3)
    
    # 验证后端是否成功启动
    if backend_process.poll() is not None:
        print("❌ 后端启动失败！")
        print("详细错误信息，请参考终端输出")
        return
    
    print()
    
    # 检查前端端口
    print("🔍 检查前端端口 8000...")
    if not check_port_available(8000):
        print("⚠️  端口 8000 已被占用，尝试寻找其他端口...")
        frontend_port = find_available_port(8000, 8010)
        if frontend_port is None:
            print("❌ 无法找到可用端口（8000-8009）")
            return
        print(f"✅ 使用端口 {frontend_port}")
    else:
        frontend_port = 8000
        print(f"✅ 端口 {frontend_port} 可用")
    
    print()
    
    # 启动前端 HTTP 服务器
    print("🌐 启动前端服务器...")
    print(f"   → 地址: http://localhost:{frontend_port}")
    print()
    
    try:
        frontend_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(frontend_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print("✅ 前端启动中...")
    except Exception as e:
        print(f"❌ 启动前端失败：{e}")
        backend_process.terminate()
        return
    
    # 等待前端启动
    time.sleep(1)
    
    print()
    print("=" * 70)
    print("✅ 系统已启动成功！")
    print("=" * 70)
    print()
    print("📌 访问地址:")
    print(f"   🌐 前端: http://localhost:{frontend_port}/index.html")
    print(f"   📡 后端: http://localhost:{backend_port}/api")
    print(f"   💚 健康检查: http://localhost:{backend_port}/health")
    print()
    print("📝 提示:")
    print("   - 按 Ctrl+C 停止所有服务")
    print("   - 查看 api.log 获取详细日志")
    print("   - 浏览器按 F12 打开开发者工具查看错误")
    print()
    print("=" * 70)
    
    # 打开浏览器
    try:
        webbrowser.open(f"http://localhost:{frontend_port}/index.html")
        print("🎯 已在浏览器中打开...")
    except Exception as e:
        print(f"⚠️  无法自动打开浏览器，请手动访问上述地址：{e}")
    
    print()
    
    try:
        # 保持进程运行，并处理后端输出
        while True:
            time.sleep(0.1)
            
            # 检查后端是否还在运行
            if backend_process.poll() is not None:
                print("\n❌ 后端服务已停止，正在关闭...")
                frontend_process.terminate()
                break
            
            # 检查前端是否还在运行
            if frontend_process.poll() is not None:
                print("\n❌ 前端服务已停止")
                # 前端停止不需要关闭后端
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号，正在关闭所有服务...")
        backend_process.terminate()
        frontend_process.terminate()
        
        # 等待进程终止
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        
        try:
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_process.kill()
        
        print("✅ 所有服务已关闭")
        print()

if __name__ == "__main__":
    main()
