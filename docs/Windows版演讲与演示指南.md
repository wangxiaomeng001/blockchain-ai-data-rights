# Windows 答辩完整指南

王孝萌 · 学号 22480010119 · 后天 8:30 线上答辩

---

## 你的两条路（先读这段决定走哪条）

### 🟢 路 A · 推荐：Mac 录好视频，Windows 只播

**条件**：你在 Mac 上录好 7 分钟 mp4 演讲视频，然后 Windows 当天只播放。

**优点**：
- 完全不用在 Windows 配 Python / py-evm 环境
- 视频和台词完全可控，零翻车
- Windows 自带"电影和电视"或装个 VLC 就能播

**当天要做的事**：
1. 把 `王孝萌-答辩录屏-7分钟.mp4` 拷到 Windows（U 盘 / 微信 / 网盘）
2. 把 `王孝萌-答辩PPT-7分钟版.pptx` 也拷过去（备用）
3. 双击 mp4 直接全屏播放
4. 屏幕共享给评委的就是这个视频
5. 视频播完进入 Q&A

**风险**：万一评委说"现场再演示一下"，没法满足——但概率很低，因为视频里已经有 90 秒清晰演示。

---

### 🟡 路 B · 备用：Windows 上跑完整环境

**条件**：你想保留"现场再 demo"的能力。

**优点**：
- 真出问题能现场操作 Streamlit

**缺点**：
- 配 Python + py-solc-x + py-evm 在 Windows 上**容易翻车**，可能要折腾 1-2 小时
- 答辩前一晚才装很冒险

**建议**：今天或明天提前装一次试通，不要答辩当天才装。

---

## 路 A · Mac 录视频 + Windows 播放（详细步骤）

### Mac 上要做的（今天/明天）

按 [王孝萌-录屏全脚本-7分钟.md](computer:///Users/mac/Documents/毕业设计-王孝萌-2026/v2/王孝萌-录屏全脚本-7分钟.md) 录一段 7 分钟 mp4。

录完导出为 mp4 格式（QuickTime 默认存 .mov，要"文件 → 导出为 → 1080p" 选 mp4，或者用 HandBrake 转）。

如果 QuickTime 只能存 .mov，**也没关系**——VLC 在 Windows 上能放 .mov。

### 拷到 Windows 的三种方式

**1. U 盘（最稳）**：

直接复制粘贴。**优点是无网络依赖**。

**2. 微信文件传输助手**：

Mac 微信传文件 → Windows 微信收 → 注意：微信对超过 200 MB 的视频会压缩。7 分钟 1080p 视频通常 100-300 MB，可能被压。**建议改成"传文件"而不是"传视频"**。

**3. 网盘（百度网盘 / 阿里云盘 / QQ 邮箱附件）**：

上传到云端 → Windows 下载。慢但稳。

### Windows 上播放的两种方式

**方式 1 · 自带"电影和电视"**：

直接双击 mp4 文件 → 默认用"电影和电视"打开 → 按 F11 全屏。

兼容性：mp4 ✅，mov ❌

**方式 2 · 装 VLC**（推荐）：

从 https://www.videolan.org/ 下载安装 VLC。

兼容性：mp4 ✅，mov ✅，所有格式都行。

### 答辩当天的关键操作

#### 答辩前 15 分钟

- [ ] 笔记本插电、电量 > 80%
- [ ] 视频文件已经在桌面，命名 `王孝萌-答辩-7分钟.mp4`
- [ ] PPT 也在桌面备用
- [ ] 用 VLC 把视频**预播放前 5 秒确认能正常播**（**别播全程**，避免被 OS 缓存）
- [ ] 摄像头测试，背景干净
- [ ] 麦克风测试

#### 进腾讯会议 / 钉钉

- [ ] 开摄像头，**等评委到齐**
- [ ] 评委说"开始答辩"后：
  1. 点击"共享屏幕"
  2. 选 **"窗口共享"** → 选 VLC / 电影和电视的窗口（不是整屏）
  3. **关键**：选完后立刻把 VLC 窗口全屏（F11 或双击）
  4. 点击播放
  5. 你坐着等 7 分钟，**保持端正姿势对着摄像头**——评委能看到你

#### 视频播完

- [ ] 立刻停止共享屏幕，切回摄像头
- [ ] 说一句："我的汇报到这里，请各位老师批评指正"（再强调一次存在感）
- [ ] 进入 Q&A，照 [答辩问答卡-25题.md](computer:///Users/mac/Documents/毕业设计-王孝萌-2026/v2/王孝萌-答辩问答卡-25题.md) 应对

---

## 路 B · Windows 上跑完整环境（备用方案）

### 0. 检查 Python

按 **Win + R** → 输入 `cmd` → 回车

```
python --version
```

如果输出 `Python 3.x.x`（≥ 3.10 即可），继续下一步。

如果提示找不到 python，去 https://www.python.org/downloads/windows/ 下载 Python 3.12 安装。

**安装时一定要勾选 "Add Python to PATH"**。

### 1. 解压代码包

把 `王孝萌答辩完整包-Windows.zip` 解压到 `C:\bishe\` 或者桌面任意位置。

解压后目录结构：

```
王孝萌答辩完整包-Windows\
  wang-yan-project-code\       <-- 代码
    setup-windows.bat          <-- 一键装依赖
    run-demo.bat               <-- 一键启动
    app.py
    ...
  王孝萌-答辩PPT.pptx           <-- PPT
  王孝萌-答辩-7分钟.mp4          <-- 录屏
  各种文档.md
```

### 2. 装依赖

双击 `setup-windows.bat`。

会自动装：streamlit、py-solc-x、web3、eth-tester、py-evm，以及预下载 Solidity 0.8.20 编译器。

整个过程 5-10 分钟，看到 `✅ 安装完成` 才算成功。

### 3. 跑测试

双击 `run-demo.bat`。

会依次：
- 跑 test_registry.py（应看到 PASSED: 18）
- 跑 test_evm.py（应看到 PASSED: 11）
- 启动 Streamlit，浏览器自动打开 http://localhost:8501

### 4. 录屏（Windows 版）

Mac 上用 QuickTime，**Windows 上推荐用 OBS Studio**（免费、专业）。

**OBS 下载**：https://obsproject.com/

**OBS 配置**：

1. 装好 OBS 打开
2. 来源 → 添加 "显示捕获" → 选你的主屏幕
3. 来源 → 添加 "音频输入捕获" → 选麦克风
4. 设置 → 输出 → 录制路径选桌面、格式 mp4
5. 主界面点 "开始录制"

**Win 自带的替代品**（最简单）：按 **Win + G** 打开 Xbox Game Bar，里面有"屏幕录制"按钮，但只能录单个窗口不能录整屏。

### 5. Windows 上录屏的注意事项

- 关闭 Windows 通知：右下角控制中心 → 专注辅助 → 仅限闹钟（Win 11 是"专注"模式）
- 关掉微信、QQ、邮箱
- 把桌面壁纸换干净
- 隐藏任务栏：右键任务栏 → 任务栏设置 → 自动隐藏任务栏

---

## 路 B 演讲操作差异（vs Mac）

录屏期间 Mac 用 **Cmd+Tab** 切窗口，**Windows 是 Alt+Tab**。

PPT 翻页两个平台都是 → 方向键 / 空格 / 鼠标点击。

退出 PPT 放映模式都是 Esc。

| 动作 | Mac | Windows |
|---|---|---|
| 切窗口 | Cmd+Tab | **Alt+Tab** |
| 复制 | Cmd+C | **Ctrl+C** |
| 粘贴 | Cmd+V | **Ctrl+V** |
| 全屏 PPT 放映 | Cmd+Shift+Return | **F5** |
| 退出放映 | Esc | **Esc** |
| 截图 | Cmd+Shift+3 | **Win+Shift+S** |
| 关闭窗口 | Cmd+W | **Ctrl+W** |

---

## 跨平台都能用的（不用变）

✅ **PPT 文件 .pptx**：跨平台，Windows 上用 PowerPoint 或 WPS 直接打开

✅ **Markdown 文档 .md**：手机看不需要任何 app

✅ **PDF 文档**：跨平台

✅ **mp4 视频**：跨平台（Windows 用 VLC 最稳）

---

## 万一翻车的兜底（Windows 版）

### `python --version` 显示"找不到"
→ Python 没装好或 PATH 没配。重新装一次，**勾上 Add Python to PATH**。

### setup-windows.bat 报错 "pip install failed"
→ 八成是网络问题。换镜像源：

```
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### run-demo.bat 弹错 "ModuleNotFoundError"
→ 依赖没装齐。重新跑 setup-windows.bat。

### Streamlit 启动但浏览器没自动打开
→ 手动打开 Chrome / Edge，地址栏输入 `http://localhost:8501`。

### py-evm 跑失败 "VMError"
→ Python 版本不对，要求 3.10+。`python --version` 检查。

### 录屏视频里没有声音
→ OBS 里"音频输入捕获"没选对麦克风。检查 OBS → 设置 → 音频 → 麦克风/辅助音频。

### 屏幕共享时评委看不到 PPT
→ 选错了"窗口共享"。腾讯会议建议选 **"共享屏幕 → 选你的主屏幕"**（不是窗口），这样确保所有内容都共享。

### 摄像头没图像
→ Windows 设置 → 隐私 → 摄像头 → 允许应用访问摄像头。

---

## 我的最终建议

**走路 A**：

1. 今天在 Mac 上把 7 分钟视频录好
2. 拷一份到 U 盘
3. 拷一份到 Windows 电脑桌面
4. 答辩当天 Windows 上**只播视频不跑代码**
5. 万一评委追问技术细节，用 [答辩问答卡-25题.md](computer:///Users/mac/Documents/毕业设计-王孝萌-2026/v2/王孝萌-答辩问答卡-25题.md) 应对

**Windows 上跑代码这条路只在以下情况走**：
- 评委明确要求现场 demo（少见）
- Mac 当天坏了备用

---

## 答辩当天文件清单（带到 Windows 上）

打包成一个文件夹放桌面：

```
答辩-王孝萌-20260514\
  王孝萌-答辩-7分钟.mp4           <- 录屏（最重要）
  王孝萌-答辩PPT.pptx              <- PPT 备用
  王孝萌-答辩问答卡-25题.md        <- 问答手机看
  王孝萌-定稿.pdf                  <- 论文 PDF
  代码包 wang-yan-project-code\   <- 万一现场要 demo
```

U 盘里也复制一份。手机里也存一份这个目录的压缩包（微信传输助手）。

---

生成时间：2026-05-12 · 后天 8:30 答辩前 36 小时
