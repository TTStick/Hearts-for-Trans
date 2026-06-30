# Trans & Pride Hearts 🏳️‍🌈🏳️‍⚧️

![image-20260630112151326](./readme.assets/image-20260630112151326.png)

A tiny desktop app that pins two pixel-art pride hearts to the bottom-left corner of the Windows 11 taskbar — one rainbow, one trans flag, with a black outline. It auto-centers vertically, scales to your resolution / DPI, and stays on top.

一个 Windows 11 桌面小程序，在任务栏左下角常驻两个像素风格的爱心——一个是 **LGBT 彩虹旗**，一个是 **跨性别旗（粉/蓝/白）**，外圈带黑色描边，「我的世界」像素风。它会根据任务栏高度自动纵向居中、按分辨率与 DPI 自动缩放，并始终置顶。

---

### Config

```
%APPDATA%\PixelPrideHearts\config.json
```

| 字段                    | 含义                         | 默认值  |
| ----------------------- | ---------------------------- | ------- |
| `scale`                 | 爱心高度占任务栏高度的比例   | `0.82`  |
| `margin`                | 距任务栏左边缘的间距（像素） | `10`    |
| `offset_x` / `offset_y` | 拖动产生的位置偏移           | `0`     |
| `autostart`             | 开机自启                     | `false` |
| `easter_egg`            | 提示彩蛋                     | `true`  |

---

## 直接运行

#### 📦 安装与运行 / Install & Run

##### 1. 安装 Python

从 [python.org](https://www.python.org/) 下载安装 Python 3.8+，安装时记得勾选 **Add Python to PATH**。

##### 2. 安装依赖

bash

```bash
pip install PyQt5
```

##### 3. 运行

用 `pythonw` 启动（不会弹出黑色控制台窗口）：

bash

```bash
pythonw pixel_pride_hearts.py
```

## 打包EXE运行

打包后即可直接双击运行，无需安装 Python：

bash

```bash
pip install pyinstaller
pyinstaller -F -w pixel_pride_hearts.py
```

完成后在 `dist/` 文件夹里得到 `pixel_pride_hearts.exe`。开机自启会自动指向这个 exe。

