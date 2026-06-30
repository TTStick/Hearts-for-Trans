# -*- coding: utf-8 -*-
"""
PixelPrideHearts —— 任务栏左下角像素爱心悬浮程序
=================================================

功能：
- 在 Windows 11 任务栏左下角常驻两个「我的世界」像素风格爱心：
  1) LGBT 彩虹旗   2) 跨性别旗（粉/蓝/白）
- 每个爱心外圈一圈黑色描边
- 自动根据任务栏高度纵向居中，并按任务栏高度缩放，适配不同分辨率 / DPI
- 始终置顶（盖在任务栏上方）
- 右键爱心 → 打开设置菜单（也有系统托盘图标）
- 左键拖动爱心可移动位置；菜单可「重置位置」
- 可设置开机自启
- 可开关「提示彩蛋」：开启后单击爱心会弹出一句随机彩蛋文字

依赖：PyQt5    （安装：pip install PyQt5）
运行：pythonw pixel_pride_hearts.py
作者备注：仅适用于 Windows。
"""

import sys
import os
import json
import random
import ctypes
from ctypes import wintypes

from PyQt5.QtWidgets import (
    QApplication, QWidget, QMenu, QAction, QSystemTrayIcon,
    QMessageBox, QToolTip
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QIcon, QFont
from PyQt5.QtCore import Qt, QTimer, QPoint


# ============================================================
#  常量 / 配置
# ============================================================

APP_NAME = "PixelPrideHearts"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(APPDATA, APP_NAME)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "offset_x": 0,      # 用户拖动产生的水平偏移
    "offset_y": 0,      # 用户拖动产生的垂直偏移
    "autostart": False, # 开机自启
    "easter_egg": True, # 提示彩蛋
    "scale": 0.82,      # 爱心高度占任务栏高度比例（含描边）
    "margin": 10,       # 距任务栏左边缘的间距（像素）
    "auto_hide_fullscreen": True,  # 全屏游戏/视频时自动隐藏
}

# 像素爱心形状（# = 实心，. = 空）。7 行 8 列，外加描边后为 9x10。
HEART = [
    ".##..##.",
    "########",
    "########",
    "########",
    ".######.",
    "..####..",
    "...##...",
]

# 彩虹旗 6 色（从上到下：红橙黄绿蓝紫）
RAINBOW = [
    (228, 3, 3),
    (255, 140, 0),
    (255, 237, 0),
    (0, 128, 38),
    (0, 77, 255),
    (117, 7, 135),
]

# 跨性别旗 5 条（蓝-粉-白-粉-蓝）
TRANS = [
    (91, 206, 250),
    (245, 169, 184),
    (255, 255, 255),
    (245, 169, 184),
    (91, 206, 250),
]

# 提示彩蛋文字
EGG_MESSAGES = [
    "做自己，就很好 🏳️‍🌈",
    "你值得被爱 💖",
    "爱就是爱 🏳️‍⚧️",
    "今天也要勇敢发光 ✨",
    "你并不孤单 🤍",
    "保持温柔，保持骄傲 🌈",
    "Be proud of who you are 🌈",
    "Trans rights are human rights 🏳️‍⚧️",
    "你本来的样子最好看 💙",
    "勇敢一点，世界很大 🌍",
]


# ============================================================
#  配置读写
# ============================================================

def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("保存配置失败:", e)


# ============================================================
#  开机自启（写注册表 HKCU Run）
# ============================================================

def get_launch_command():
    """返回开机自启要写入的命令行。"""
    if getattr(sys, "frozen", False):
        # 已打包成 exe
        return '"{}"'.format(sys.executable)
    # 以脚本运行：尽量用 pythonw 避免黑色控制台窗口
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    script = os.path.abspath(__file__)
    return '"{}" "{}"'.format(pyw, script)


def set_autostart(enable):
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                             winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                              get_launch_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print("设置开机自启失败:", e)
        return False


# ============================================================
#  Windows API：获取任务栏矩形 / 置顶
# ============================================================

user32 = ctypes.windll.user32
user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_uint]

HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

# ---- 全屏检测相关 ----
shell32 = ctypes.windll.shell32
MONITOR_DEFAULTTONEAREST = 0x00000002


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]


def is_fullscreen_app_active(self_hwnd=0):
    """检测前台是否有全屏游戏 / 全屏视频 / 演示模式。

    两种判据满足其一即认为处于全屏：
    1) Shell 通知状态为 D3D 独占全屏(3) 或 演示模式(4)
    2) 前台窗口铺满了它所在的整块显示器（独占/无边框全屏）
    （普通最大化窗口不会触发，因为它不会盖住任务栏）
    """
    # 判据 1：Shell 通知状态
    try:
        state = ctypes.c_int(0)
        if shell32.SHQueryUserNotificationState(ctypes.byref(state)) == 0:
            if state.value in (3, 4):  # 3=D3D全屏游戏, 4=演示模式
                return True
    except Exception:
        pass

    # 判据 2：前台窗口铺满整个显示器
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd or int(hwnd) == int(self_hwnd):
            return False
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        if buf.value in ("Progman", "WorkerW",
                         "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
            return False
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return False
        mr = mi.rcMonitor
        if (rect.left <= mr.left and rect.top <= mr.top
                and rect.right >= mr.right and rect.bottom >= mr.bottom):
            return True
    except Exception:
        pass
    return False


def get_taskbar_rect():
    """返回主任务栏 (left, top, right, bottom)，物理像素；失败返回 None。"""
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    if not hwnd:
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return (rect.left, rect.top, rect.right, rect.bottom)


# ============================================================
#  绘制像素爱心 → QPixmap
# ============================================================

def make_heart_pixmap(grid, colors, cell):
    """根据形状 grid 与配色 colors 生成一个带黑色描边的像素爱心 QPixmap。
    cell 为单个像素块的边长（屏幕像素）。"""
    rows = len(grid)
    cols = len(grid[0])
    W = cols + 2   # 左右各留一圈给描边
    H = rows + 2

    fill = [[False] * W for _ in range(H)]
    for r, line in enumerate(grid):
        for c, ch in enumerate(line):
            if ch == "#":
                fill[r + 1][c + 1] = True

    # 描边 = 与实心块八邻接的空块
    outline = [[False] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if fill[r][c]:
                continue
            adj = False
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and fill[rr][cc]:
                        adj = True
            outline[r][c] = adj

    pm = QPixmap(W * cell, H * cell)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setPen(Qt.NoPen)
    black = QColor(0, 0, 0)
    for r in range(H):
        orig_r = r - 1  # 对应原始 grid 的行（用于按行映射颜色条纹）
        for c in range(W):
            if fill[r][c]:
                idx = int(orig_r / rows * len(colors))
                idx = max(0, min(len(colors) - 1, idx))
                p.fillRect(c * cell, r * cell, cell, cell, QColor(*colors[idx]))
            elif outline[r][c]:
                p.fillRect(c * cell, r * cell, cell, cell, black)
    p.end()
    return pm


# ============================================================
#  悬浮窗口
# ============================================================

class HeartOverlay(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self._cell = -1
        self.gap = 4
        self.h1 = None  # 彩虹
        self.h2 = None  # 跨性别
        self._dragging = False
        self._moved = False
        self._drag_origin = QPoint()
        self._win_origin = QPoint()
        self._base = (0, 0)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setToolTip("像素骄傲爱心 · 右键设置")

        # 定时器：保持位置 + 置顶
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(500)

        self.update_position()
        self.show()
        self._apply_ex_style()

    # ---------- 窗口扩展样式：不抢焦点 + 不进任务栏 ----------
    def _apply_ex_style(self):
        try:
            hwnd = int(self.winId())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except Exception as e:
            print("设置窗口样式失败:", e)

    # ---------- 重建像素图 ----------
    def rebuild(self, cell):
        self.gap = cell
        self.h1 = make_heart_pixmap(HEART, RAINBOW, cell)
        self.h2 = make_heart_pixmap(HEART, TRANS, cell)

    # ---------- 置顶 ----------
    def reassert_topmost(self):
        try:
            hwnd = int(self.winId())
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        except Exception:
            pass

    # ---------- 定位 / 缩放 ----------
    def update_position(self):
        if self._dragging:
            return

        # 全屏游戏 / 视频 / 演示模式 → 隐藏，避免遮挡画面
        if self.cfg.get("auto_hide_fullscreen", True):
            if is_fullscreen_app_active(int(self.winId())):
                if self.isVisible():
                    self.hide()
                return
            else:
                if not self.isVisible():
                    self.show()
                    self._apply_ex_style()

        rect = get_taskbar_rect()
        if rect:
            l, t, r, b = rect
            tb_l, tb_t, tb_h = l, t, (b - t)
        else:
            # 兜底：用主屏可用区域估算任务栏
            scr = QApplication.primaryScreen()
            g = scr.geometry()
            ag = scr.availableGeometry()
            tb_h = (g.bottom() - ag.bottom()) if g.bottom() > ag.bottom() else 48
            tb_l = g.left()
            tb_t = ag.bottom() + 1

        # 按任务栏高度计算每个像素块大小（含描边共 len(HEART)+2 行）
        cell = max(3, int(tb_h * self.cfg["scale"] / (len(HEART) + 2)))
        if cell != self._cell:
            self._cell = cell
            self.rebuild(cell)

        total_w = self.h1.width() + self.gap + self.h2.width()
        total_h = max(self.h1.height(), self.h2.height())

        base_x = tb_l + self.cfg["margin"]
        base_y = tb_t + (tb_h - total_h) // 2
        self._base = (base_x, base_y)

        x = base_x + self.cfg["offset_x"]
        y = base_y + self.cfg["offset_y"]

        self.setFixedSize(total_w, total_h)
        self.move(int(x), int(y))
        self.reassert_topmost()

    # ---------- 绘制 ----------
    def paintEvent(self, e):
        if not self.h1 or not self.h2:
            return
        p = QPainter(self)
        p.drawPixmap(0, 0, self.h1)
        p.drawPixmap(self.h1.width() + self.gap, 0, self.h2)
        p.end()

    # ---------- 鼠标：拖动 / 右键菜单 / 彩蛋 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._moved = False
            self._drag_origin = e.globalPos()
            self._win_origin = self.pos()
        elif e.button() == Qt.RightButton:
            self.show_menu(e.globalPos())

    def mouseMoveEvent(self, e):
        if self._dragging and (e.buttons() & Qt.LeftButton):
            delta = e.globalPos() - self._drag_origin
            if delta.manhattanLength() > 2:
                self._moved = True
            self.move(self._win_origin + delta)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self._moved:
            # 保存新的偏移量
            bx, by = self._base
            self.cfg["offset_x"] = self.x() - bx
            self.cfg["offset_y"] = self.y() - by
            save_config(self.cfg)
        else:
            # 单击（未移动）：触发彩蛋
            if self.cfg.get("easter_egg", True):
                msg = random.choice(EGG_MESSAGES)
                QToolTip.showText(e.globalPos() + QPoint(0, -10), msg, self)
        self._dragging = False

    # ---------- 设置菜单 ----------
    def show_menu(self, global_pos):
        menu = QMenu()
        f = QFont()
        f.setPointSize(10)
        menu.setFont(f)

        info = QAction("🏳️‍🌈 像素骄傲爱心", self)
        info.setEnabled(False)
        menu.addAction(info)
        menu.addSeparator()

        tip = QAction("（左键拖动爱心可移动位置）", self)
        tip.setEnabled(False)
        menu.addAction(tip)

        act_reset = QAction("重置位置", self)
        act_reset.triggered.connect(self.reset_position)
        menu.addAction(act_reset)

        menu.addSeparator()

        act_auto = QAction("开机自启", self)
        act_auto.setCheckable(True)
        act_auto.setChecked(self.cfg.get("autostart", False))
        act_auto.triggered.connect(self.toggle_autostart)
        menu.addAction(act_auto)

        act_egg = QAction("提示彩蛋", self)
        act_egg.setCheckable(True)
        act_egg.setChecked(self.cfg.get("easter_egg", True))
        act_egg.triggered.connect(self.toggle_egg)
        menu.addAction(act_egg)

        act_fs = QAction("全屏时自动隐藏", self)
        act_fs.setCheckable(True)
        act_fs.setChecked(self.cfg.get("auto_hide_fullscreen", True))
        act_fs.triggered.connect(self.toggle_auto_hide)
        menu.addAction(act_fs)

        menu.addSeparator()

        act_about = QAction("关于", self)
        act_about.triggered.connect(self.show_about)
        menu.addAction(act_about)

        act_quit = QAction("退出", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_quit)

        menu.exec_(global_pos)

    def reset_position(self):
        self.cfg["offset_x"] = 0
        self.cfg["offset_y"] = 0
        save_config(self.cfg)
        self.update_position()

    def toggle_autostart(self, checked):
        ok = set_autostart(checked)
        self.cfg["autostart"] = checked if ok else self.cfg.get("autostart", False)
        save_config(self.cfg)

    def toggle_egg(self, checked):
        self.cfg["easter_egg"] = checked
        save_config(self.cfg)

    def toggle_auto_hide(self, checked):
        self.cfg["auto_hide_fullscreen"] = checked
        save_config(self.cfg)
        # 关闭该功能时，若当前被隐藏则立即恢复显示
        if not checked and not self.isVisible():
            self.show()
            self._apply_ex_style()
        self.update_position()

    def show_about(self):
        QMessageBox.information(
            self, "关于 " + APP_NAME,
            "像素骄傲爱心 🏳️‍🌈🏳️‍⚧️\n\n"
            "常驻任务栏左下角的两个我的世界像素风格爱心。\n"
            "· 左键拖动可移动位置\n"
            "· 右键打开设置菜单\n"
            "· 单击爱心有提示彩蛋\n"
            "· 支持开机自启、自动适配分辨率\n"
        )


# ============================================================
#  系统托盘（设置入口的备份）
# ============================================================

def build_tray(overlay, cfg, app):
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    icon_pm = make_heart_pixmap(HEART, RAINBOW, 4)
    tray = QSystemTrayIcon(QIcon(icon_pm))
    tray.setToolTip("像素骄傲爱心")

    menu = QMenu()

    act_reset = QAction("重置位置", menu)
    act_reset.triggered.connect(overlay.reset_position)
    menu.addAction(act_reset)

    act_auto = QAction("开机自启", menu)
    act_auto.setCheckable(True)
    act_auto.setChecked(cfg.get("autostart", False))
    act_auto.triggered.connect(lambda c: overlay.toggle_autostart(c))
    menu.addAction(act_auto)

    act_egg = QAction("提示彩蛋", menu)
    act_egg.setCheckable(True)
    act_egg.setChecked(cfg.get("easter_egg", True))
    act_egg.triggered.connect(lambda c: overlay.toggle_egg(c))
    menu.addAction(act_egg)

    menu.addSeparator()
    act_about = QAction("关于", menu)
    act_about.triggered.connect(overlay.show_about)
    menu.addAction(act_about)

    act_quit = QAction("退出", menu)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_quit)

    tray.setContextMenu(menu)
    tray.show()
    return tray


# ============================================================
#  主入口
# ============================================================

def main():
    # 让进程 DPI 感知，使 Qt 坐标 == 物理像素，与任务栏坐标一致，像素更清晰
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭悬浮窗不退出（由菜单退出）

    cfg = load_config()

    # 启动时按配置同步一次开机自启状态
    if cfg.get("autostart", False):
        set_autostart(True)

    overlay = HeartOverlay(cfg)
    tray = build_tray(overlay, cfg, app)  # 保存引用，避免被回收
    overlay._tray = tray

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
