"""
DNA-Strand 自动窗口启动器
支持最小化、关闭、系统托盘
"""
import sys
import os
import webbrowser
import threading
import time
from pathlib import Path

# 尝试导入pywebview（原生窗口）
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

# 尝试导入pystray（系统托盘）
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


class DNAWindow:
    """DNA-Strand 窗口管理器"""

    def __init__(self, system, port=8080):
        self.system = system
        self.port = port
        self.url = f"http://127.0.0.1:{port}"
        self.window = None
        self.tray_icon = None
        self.server_thread = None

    def start_server(self):
        """启动Web服务器"""
        from .server import DNAWebServer
        self.server = DNAWebServer(self.system, port=self.port)
        self.server.start(background=True)
        print(f"[Window] 服务器已启动: {self.url}")

    def create_tray_icon(self):
        """创建系统托盘图标"""
        if not HAS_TRAY:
            return None

        # 创建图标
        icon_size = 64
        image = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 绘制DNA图标（简化）
        # 背景圆
        draw.ellipse([4, 4, icon_size-4, icon_size-4], fill=(0, 200, 255, 200))

        # DNA双螺旋（简化）
        for i in range(5):
            y = 12 + i * 10
            # 左螺旋
            draw.ellipse([20, y, 28, y+6], fill=(255, 255, 255, 200))
            # 右螺旋
            draw.ellipse([36, y, 44, y+6], fill=(255, 255, 255, 200))
            # 连接线
            draw.line([(24, y+3), (40, y+3)], fill=(255, 255, 255, 150), width=2)

        return image

    def setup_tray(self):
        """设置系统托盘"""
        if not HAS_TRAY:
            return

        image = self.create_tray_icon()
        if not image:
            return

        menu = pystray.Menu(
            pystray.MenuItem("打开仪表盘", self._show_window),
            pystray.MenuItem("最小化", self._minimize_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._quit)
        )

        self.tray_icon = pystray.Icon(
            "DNA-Strand",
            image,
            "DNA-Strand 神经网络",
            menu
        )

        # 在单独线程中运行托盘
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _show_window(self, icon=None, item=None):
        """显示窗口"""
        if self.window:
            self.window.show()
            self.window.restore()

    def _minimize_window(self, icon=None, item=None):
        """最小化窗口"""
        if self.window:
            self.window.minimize()

    def _quit(self, icon=None, item=None):
        """退出程序"""
        if self.tray_icon:
            self.tray_icon.stop()
        if self.window:
            self.window.destroy()
        os._exit(0)

    def open_browser(self):
        """在浏览器中打开"""
        webbrowser.open(self.url)

    def run_with_webview(self):
        """使用pywebview运行原生窗口"""
        if not HAS_WEBVIEW:
            print("[Window] pywebview 未安装，使用浏览器打开")
            self.open_browser()
            return

        # 创建窗口
        self.window = webview.create_window(
            "DNA-Strand 神经网络仪表盘",
            self.url,
            width=1400,
            height=900,
            resizable=True,
            min_size=(800, 600),
            background_color='#0a0a1a'
        )

        # 窗口事件
        self.window.events.closed += self._on_window_closed

        # 启动pywebview
        webview.start(debug=False)

    def _on_window_closed(self):
        """窗口关闭事件"""
        print("[Window] 窗口已关闭")
        if self.tray_icon:
            self.tray_icon.stop()

    def run(self):
        """运行窗口"""
        # 启动服务器
        self.start_server()

        # 等待服务器启动
        time.sleep(1)

        # 设置系统托盘
        self.setup_tray()

        # 运行窗口
        if HAS_WEBVIEW:
            self.run_with_webview()
        else:
            self.open_browser()
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[Window] 程序已退出")


def open_dashboard_window(system, port=8080):
    """
    打开仪表盘窗口

    Args:
        system: DNASystem 实例
        port: 端口号
    """
    window = DNAWindow(system, port)
    window.run()


def open_dashboard_background(system, port=8080):
    """
    后台打开仪表盘（不阻塞）

    Args:
        system: DNASystem 实例
        port: 端口号

    Returns:
        窗口URL
    """
    window = DNAWindow(system, port)
    window.start_server()
    time.sleep(0.5)
    window.open_browser()
    return window.url
