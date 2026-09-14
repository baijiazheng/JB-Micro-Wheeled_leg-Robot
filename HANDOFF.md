# 项目交接 / 状态文档

> **用途**：上下文用尽、换新会话、或过一段时间回来时，读这一份就能接上。
> 最后更新：**2026-09-14**

---

## 一、这是什么项目

把开源项目 [Micro-Wheeled_leg-Robot](https://gitee.com/lavine/Micro-Wheeled_leg-Robot)（桌面级双轮腿机器人，ESP32 单板）
**复刻成 STM32 双板 + CAN 版本**。

- **驱动板 F103**：STM32F103C8T6 + 2×L6234（FOC）+ CAN 从机
- **主控板 F407**：STM32F407VET6 + 2×STS3032（腿舵机）+ CAN 主机
- **编码器板 ×2**：AS5600 磁编码器（卫星板，贴电机轴）
- **IMU 板 ×1**：MPU6050（卫星板，放整车重心）
- 电池 2S（7.4V）

**学习主线**：STM32 HAL → FOC 从零写 → LQR 平衡 → CAN 双板架构

---

## 二、已完成（全部有验证）

| 项目 | 状态 | 证据 |
|---|---|---|
| 固件算法 | ✅ | 6 套主机测试全绿 |
| F103 驱动板固件 | ✅ 编译通过 | `driver_f103.bin` (text 27988 / bss 788) |
| F407 主控板固件 | ✅ 编译通过 | `main_f407.bin` (text 12440) |
| **四板网表** | ✅ 自动校验通过 | `python3 hardware/check_netlists.py` |
| **立创EDA 原生原理图 ×4** | ✅ 可导入专业版 | `*_立创EDA.json` |
| **架构改造：编码器/IMU 改卫星板** | ✅ | 见下方"四" |
| 小白接线示意图 | ✅ | `docs/wiring/接线示意图.html` |
| 设计文档 | ✅ | `docs/`（含 board_spec / bom） |

**固件算法测试**（可随时重跑）：
```bash
cd ~/JB-Micro-Wheeled_leg-Robot/firmware
(cd driver_f103/foc && ./test_foc_math)      # FOC 数学
(cd common/pid && ./test_pid)                # PID
(cd driver_f103/foc && ./test_foc_control)   # FOC 控制环
(cd driver_f103/balance && ./test_balance)   # LQR 平衡
(cd common/can_protocol && ./test_can)       # CAN 协议
(cd main_f407/hal && ./test_sts3032)         # STS3032 舵机
```

**网表校验**（改任何网表后必跑）：
```bash
cd ~/JB-Micro-Wheeled_leg-Robot/hardware
python3 check_netlists.py       # 四板自洽 + 板间逐脚 + GH1.25 线序 + 电源链
```

---

## 三、文件导航

```
JB-Micro-Wheeled_leg-Robot/
├── HANDOFF.md                    ← 本文件
├── docs/
│   ├── architecture.md           架构（双板分工、CAN 协议、引脚分配）
│   ├── bom.md                    ★ 采购清单（渠道分工、避坑、下单顺序）
│   ├── schematic_design.md       原理图设计蓝图
│   ├── board_spec.md             ★ 板级规格书（四板尺寸、分区、堆叠、布线、打样）
│   ├── pcb_layout.md             PCB 布局方案
│   ├── bringup_plan.md           上电联调 + 故障速查表
│   └── wiring/接线示意图.html     ★ 小白接线图（分享给别人的那份）
├── hardware/
│   ├── check_netlists.py         ★ 四板网表 + 板间连接自动校验（单一真相校验器）
│   ├── driver_board_f103/
│   │   ├── driver_f103_立创EDA.json   ★ 立创EDA 原生原理图（45 元件）
│   │   ├── driver_f103.kicad_sch      KiCad 版（备用）
│   │   └── netlist.py                 薄封装，转调 check_netlists.py
│   ├── main_board_f407/               同上（30 元件）
│   ├── encoder_board/                 ★ 编码器板（6 元件，做 2 块）
│   ├── imu_board/                     ★ IMU 板（6 元件，做 1 块）
│   ├── easyeda_gen/gen_boards.py      立创EDA 生成器（当前主线路）
│   └── kicad_gen/{gen_driver,gen_main}.py  ★ 网表的唯一真相在这里
└── firmware/
    ├── common/{pid,can_protocol}/     共享模块
    ├── driver_f103/                   驱动板固件
    └── main_f407/                     主控板固件
```

> ⚠️ **网表只在一处定义**：`kicad_gen/gen_driver.py` 与 `gen_main.py` 的 `GROUPS`/`NETS`。
> 其它文件（`netlist.py`、`gen_boards.py`）都从它取，不再手抄。

---

## 四、【最新】架构改造：编码器/IMU 改成卫星板 ✅

**触发原因**：扒了参考项目的原始资料（`~/Micro-Wheeled_leg-Robot/2.Hardware/`），发现它是 **4 块 PCB**：

```
1.ControllerPCB  ESP32 + 2×L6234 + 电源      ← 主板
2.EncoderPCB     AS5600 + GH1.25座           ← 卫星板 ×2
3.IMUPCB         MPU6050 + 2×GH1.25座        ← 卫星板 ×1
4.ServoDebugPCB  舵机总线调试板
```

**物理依据**（实测 `BodyBase-Steel.stp`）：

| 项 | 数值 |
|---|---|
| 参考底盘宽度 | **60 mm** |
| 两轮轴线间距 | ≈ 60 mm |
| 我们板宽 | 50 mm |
| AS5600 感应距离 | 0.5 ~ 3 mm |

磁铁是 502 粘在**电机转轴端面**上的，板宽 50mm 而两轮轴线在 ±30mm —— **差 5mm，够不到**。
硬塞在板上就没法做机械了。所以照参考项目做卫星板。

### 本次改动清单

| 改动 | 说明 |
|---|---|
| 驱动板移除 U4/U5/U6 + R4~R7 + C11/C12/C20/C21 | 共 11 个元件移出 |
| 驱动板新增 J6/J7 | GH1.25 4P，分别接编码器①、IMU 板 |
| 新增 3 块卫星板生成 | 编码器板 ×2、IMU 板 ×1 |
| **补板间连接器 J8 / J3** | 2×4 排针：VIN×2 + GND×4 + CAN_H + CAN_L |
| 主控板 J3 从 2P 改 2×4 | 原来只有 CAN_H/L，没有地 |

### ★ 顺带揪出并修掉的 5 个隐藏 bug

| # | Bug | 后果 | 修法 |
|---|---|---|---|
| 1 | **总开关被旁路** | `J1.1` 和 `SW1.1` 都挂在 `VIN` 上 → **开关按了没用** | 拆出 `BAT_RAW` 网：`J1 → SW1 → D1 → VIN` |
| 2 | **防反接二极管没串进回路** | `D1.A` 接在 `SW_OUT` 上，`SW_OUT` 是死网 → 保护失效 | 同上，`D1` 串在 `SW1` 之后 |
| 3 | **MP2225 反馈上拉到 3V3** | `R2.2` 挂在 `+3V3` 而不是 `+5V` → 实际输出会冲到 8.3V | `R2.2` 改到 `+5V` |
| 4 | **电池分压超量程** | 100k/100k 分压 → 8.4V 变 4.2V，超过 3.3V ADC 上限 | `R13` 改 **47k**，8.4V→2.69V |
| 5 | **MPU6050 的 CPOUT 电容值是错的** | 写成 2.2uF，手册要求 **2.2nF** | 改 2.2nF（移到 IMU 板） |

> Bug 3 和 4 是"能跑但不对"的类型 —— 不会冒烟，但电源电压和电池读数都是错的。
> 这类问题在**出板前**发现，比焊完调不出来强太多。

### 当前状态

- ✅ 四块板原理图生成完毕，`check_netlists.py` **全绿**
  （驱动板 45 元件/50 网、主控板 30 元件/26 网、编码器板 6/4、IMU 板 6/6，无悬空网）
- ✅ 板间 J8↔J3 逐脚一致、GH1.25 线序全车统一
- ⏳ **下一步：PCB 布局**（见第五节）

---

## 五、下一步（按顺序）

### 阶段 A：PCB 布局（当前）

1. **把 4 个 `.json` 重新导入立创EDA专业版**（先删掉旧工程，避免符号混在一起）
   - `hardware/driver_board_f103/driver_f103_立创EDA.json`
   - `hardware/main_board_f407/main_f407_立创EDA.json`
   - `hardware/encoder_board/encoder_立创EDA.json`
   - `hardware/imu_board/imu_立创EDA.json`
2. **关联封装**（封装管理器切**在线模式**）→ 把能搜到的封装名回填进 `gen_boards.py` 的 `PKG`
3. **转 PCB**：板框改 50×50、圆角 R2，放 4× M2.5 孔 @ (3,3)(47,3)(3,47)(47,47)
4. **按分区摆放**：见 `docs/board_spec.md` 第二节 + 第七节摆放优先级
5. **Auto Route** → DRC → 导出 Gerber

### 阶段 B：打样与采购

6. 嘉立创下单：2 层 / 1.6mm / 沉金 / 5 片 / **SMT 部分贴片**（只贴 5 个难焊件）/ **钢网**
7. 淘宝先下机电件（货期长）：电机、STS3032、电池、磁铁、**GH1.25 4PIN 15cm 线 ×3**
8. 立创商城按 `docs/bom.md` 一键配单
9. 先用**卫星板**练加热台回流焊手感，再焊两块大板

### 阶段 C：联调

10. 照 `docs/wiring/接线示意图.html` 接线，按 `docs/bringup_plan.md` 逐步上电
11. FOC 标定 → LQR 调参 → CAN 双板联调
12. 最后做 ESP32 网页控制版本

---

## 六、关键坑（踩过的，别再踩）

### 工具链 / 立创EDA

| 坑 | 说明 |
|---|---|
| **立创EDA 只认 .eprj"打开"** | 导入标准版文件要用**"导入"**菜单，不是"打开" |
| **立创EDA 引脚必须 30 字段** ★ | 最初用 `[^#]*` 正则提取模板，在颜色字段 `#000000` 处被截断，生成的引脚只有 10 字段 → 符号无引脚 → **无网络、无飞线**。正确格式 = 头+连接点+线+**引脚名文本**+**引脚号文本**+**端部装饰** |
| **验证连接的唯一标准** ★ | 导入后**看有没有飞线**（按 N）。"能导入" ≠ "连接建立了" |
| **别给引脚额外加 T 文本** ★ | 引脚名写在 `P` 元素内部即可；额外加 `T~…~comment~{引脚名}~` 会**污染器件备注/值**（把 `5.49k` 覆盖成引脚名 `2`） |
| **封装管理器要切"在线模式"** | 否则只能看到工程自带封装，搜不到系统库 |
| **符号引脚数必须等于封装焊盘数** ★ | SW1（5 焊盘 vs 2 脚）、AMS1117（4 焊盘 vs 3 脚）、STM32（脚号凭感觉编）都报过 DRC "引脚与焊盘未对应"。**改用 KiCad 官方库的权威管脚定义**（`sexp.py` 提取）后解决 |
| **不要用 KiCad 生成 PCB** | 立创EDA 的封装来自立创商城真实料号，换 KiCad 封装可能尺寸不符废板 |

### 硬件设计

| 坑 | 说明 |
|---|---|
| **AS5600 固定地址 0x36** | 两个必须占两条 I2C 总线（F103 正好 2 个）；两块编码器板必须分接 J6/J7 |
| **I²C 上拉只放一处** | 编码器板放 4.7k，IMU 板不放 —— 否则并联后阻值减半 |
| **F103 的 PA9/PA10 冲突** | TIM1 PWM 和 USART1 共用 → 调试口用 USART2(PA2/PA3) |
| **F103 CAN1_RX0 中断名** | 必须叫 `USB_LP_CAN1_RX0_IRQHandler`（和 USB 共用向量） |
| **L6234 假芯片多** | 参考项目 README 原文警告；走立创商城自营 |
| **MPU6050 已停产** | 市面多为翻新，买 3 个 |
| **两块板的 GND 必须相通** | 靠板间排针的地脚。不共地 CAN 和 I²C 都不工作 |

### 算法

| 坑 | 说明 |
|---|---|
| **平衡环是正反馈** | 轮式倒立摆 LQR 四路反馈**全是正反馈**，位移靠"先造后仰再拉回" |
| **运动时位移零点要重置** | 否则位移环和速度环打架，机器人走不动 |
| **GH1.25 线序统一** | 全车 `1=+3V3 2=SCL 3=SDA 4=GND`，插反直接烧传感器 |

---

## 七、想继续时怎么开口

新会话里直接说：

> "读 `~/JB-Micro-Wheeled_leg-Robot/HANDOFF.md`，我们继续做 XX"

我就知道全部上下文了。

---

## 八、环境信息（重装/换机用）

| 项 | 值 |
|---|---|
| OS | Ubuntu 22.04 |
| 交叉编译 | arm-none-eabi-gcc 10.3.1 |
| KiCad | 9.0.9（只用来提取权威管脚定义，不用来出 PCB） |
| STM32 HAL | `~/STM32Cube/Repository/STM32CubeF1-1.8.6`、`...F4_V1.28.3` |
| 烧录 | st-flash 1.7.0（udev 已配 `/etc/udev/rules.d/49-stlinkv2.rules`） |
| 立创EDA专业版 | `/opt/lceda-pro` |
| 参考项目源码 | `~/Micro-Wheeled_leg-Robot/`（含 4 块板的原始 BOM.csv，**UTF-16 编码**） |
| apt 源 | 已修（阿里云 HTTPS） |
| python3 | 用 `/usr/bin/python3`（PATH 被 PlatformIO penv 遮蔽过） |
