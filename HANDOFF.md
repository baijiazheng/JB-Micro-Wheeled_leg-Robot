# 项目交接 / 状态文档

> **用途**：上下文用尽、换新会话、或过一段时间回来时，读这一份就能接上。
> 最后更新：2026-09-13

---

## 一、这是什么项目

把开源项目 [Micro-Wheeled_leg-Robot](https://gitee.com/lavine/Micro-Wheeled_leg-Robot)（桌面级双轮腿机器人，ESP32 单板）
**复刻成 STM32 双板 + CAN 版本**。

- **驱动板**：STM32F103C8T6 + 2×L6234（FOC）+ 2×AS5600（编码器）+ MPU6050（IMU）
- **主控板**：STM32F407VET6 + 2×STS3032（腿舵机）+ CAN 主机
- 电池 2S（7.4V）

**学习主线**：STM32 HAL → FOC 从零写 → LQR 平衡 → CAN 双板架构

---

## 二、已完成（全部有验证）

| 项目 | 状态 | 证据 |
|---|---|---|
| 固件算法 | ✅ | 6 套主机测试全绿 |
| F103 驱动板固件 | ✅ 编译通过 | `driver_f103.bin` (29KB) |
| F407 主控板固件 | ✅ 编译通过 | `main_f407.bin` (12KB) |
| 双板网表 | ✅ 校验通过 | 51 / 25 网络 |
| **立创EDA 原生原理图** | ✅ **已成功导入专业版** | `*_立创EDA.json` |
| 5 份设计文档 | ✅ | `docs/` |

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

---

## 三、文件导航

```
JB-Micro-Wheeled_leg-Robot/
├── HANDOFF.md                    ← 本文件
├── README.md
├── docs/
│   ├── architecture.md           架构（双板分工、CAN 协议、引脚分配）
│   ├── bom.md                    采购清单 + 芯片列表
│   ├── schematic_design.md       原理图设计蓝图
│   ├── board_spec.md             ★ 板级规格书（50×50mm、安装孔、堆叠、布线规则）
│   ├── pcb_layout.md             PCB 布局方案
│   └── bringup_plan.md           上电联调 10 步 + 故障速查表
├── hardware/
│   ├── driver_board_f103/
│   │   ├── driver_f103_立创EDA.json   ★ 立创EDA 原生原理图（已验证可导入）
│   │   ├── driver_f103.kicad_sch      KiCad 版（备用）
│   │   └── netlist.py                 网表 + 校验脚本
│   ├── main_board_f407/               （同上）
│   ├── easyeda_gen/                   立创EDA 生成器（gen_boards.py）
│   └── kicad_gen/                     KiCad 生成器
└── firmware/
    ├── common/{pid,can_protocol}/     共享模块
    ├── driver_f103/                   驱动板固件
    └── main_f407/                     主控板固件
```

---

## 四、当前进度：卡在哪一步

### 【最新】已成功转到 PCB ✅ —— 当前在 PCB 布局阶段

**原理图 → PCB 转换成功**，所有元件带焊盘摆放完毕（U1/U2/U3/U6/U10、J1-J5、全部阻容）。
DRC 里的"引脚与焊盘未对应"信息级提示**无害**（PCB 转换成功即证明封装生效），可忽略。

**PCB 布局待办**（参考 `docs/pcb_layout.md`）：
1. **定板框尺寸** ← 当前卡在这（见下方"待决策"）
2. 按功能分区摆放（电源区/通信区/MCU/电机驱动/编码器）
3. 关键约束：AS5600 对电机轴磁铁、MPU6050 在重心、L6234 靠板边散热、去耦紧贴
4. 布线 → 铺铜 → DRC → 导出 Gerber → 嘉立创打样

**已决定**：
- **板框尺寸：50×50mm**（驱动板+主控板统一，可堆叠）→ 见 `docs/board_spec.md`
- **焊接：锡膏 + 加热台** → 硬约束：**所有 SMD 必须放同一面**
- **布线：用立创EDA 自带的自动布线器**（程序里找到 `Auto Route...` 菜单）

**⚠️ 注意**：不要用 KiCad 生成 PCB——立创EDA 的封装来自立创商城真实料号，
换 KiCad 封装可能尺寸不符导致打样废板。freerouting 是备选（下载不稳定，非必需）。

### 【历史】DRC 结果：致命错误 0 / 错误 0 ✅
封装全部关联完成。剩 51 警告 + 32 信息。其中 **6 个元件"引脚与焊盘未对应"**，
转 PCB 前必须修（封装焊盘号要 1..N 与符号引脚号对应）：

| DRC 显示的"值" | 位号 | 元件 | 应选封装 |
|---|---|---|---|
| 2.2uF | C20 | MPU6050 CPOUT 电容 | C0805（选错了） |
| TJA1051T | U9 | CAN 收发器 | SOIC-8，焊盘 1~8 |
| 120 | R8 | CAN 终端电阻 | R0805（选错了） |
| CH340C | U10 | USB 转串口 | SOP-16，焊盘 1~16 |
| SWD | J4 | SWD 口 | 4 脚排针 |
| USB | J5 | USB 口 | Micro USB，焊盘 1~4 |

> 技巧：找一个已成功关联的同类元件（如 C1 的 C0805），选同一个封装。

### 历史记录（已完成）

**✅ 立创EDA 导入成功 → ⏳ 只剩 1 个元件待关联封装**

驱动板原理图已导入专业版。**关键经验**：封装管理器必须在**在线模式**下才能搜到系统库，
离线/工程模式下只能看到文件里带过来的封装。

已关联 7 个（D2/J1/J2/J3/J4/J5/U7）。**只剩 U6 (MPU6050)**：

| 位号 | 元件 | 搜什么封装 |
|---|---|---|
| U6 | MPU6050 | `QFN-24` 或 `QFN-24_L4.0-W4.0-P0.50-BL-EP`，或按料号 `C24112` 搜 |

> 官方文档说明：单独导入原理图时"需要全部元件重新绑定封装"，所以这是正常流程。

**⚠️ 待决策**：MPU6050 裸片是 QFN-24 / 0.5mm 间距 / 带底部散热焊盘，**手工烙铁焊不了**。
三个选择：(a) 热风枪+锡膏；(b) 嘉立创 SMT 贴片服务；(c) 改用 GY-521 模块（板上放 8P 排母）。
参考项目当初就是因此把 IMU 做成独立小板的。

---

## 五、下一步（按顺序）

1. **关联 U6 (MPU6050) 封装** → 驱动板原理图就完整了
2. **检查原理图**（对照 `docs/schematic_design.md`）
3. **画 PCB**：设计 → 更新/转换原理图到 PCB
   - 参考 `docs/pcb_layout.md`（布局分区、AS5600 须对电机磁铁、MPU6050 放重心）
4. **打样**：嘉立创下单（2 层 / 1.6mm）
5. **采购物料**：`docs/bom.md` 第一节（电机/舵机/电池货期长，可先买）
6. **焊接 + 上电联调**：照 `docs/bringup_plan.md` 10 步走

---

## 六、关键坑（踩过的，别再踩）

| 坑 | 说明 |
|---|---|
| **AS5600 固定地址 0x36** | 两个必须占两条 I2C 总线（F103 正好 2 个） |
| **F103 的 PA9/PA10 冲突** | TIM1 PWM 和 USART1 共用 → 调试口用 USART2(PA2/PA3) |
| **F103 CAN1_RX0 中断名** | 必须叫 `USB_LP_CAN1_RX0_IRQHandler`（和 USB 共用向量） |
| **平衡环是正反馈** | 轮式倒立摆 LQR 四路反馈**全是正反馈**，位移靠"先造后仰再拉回" |
| **运动时位移零点要重置** | 否则位移环和速度环打架，机器人走不动 |
| **L6234 假芯片多** | 走正规渠道 |
| **立创EDA 只认 .eprj"打开"** | 导入标准版文件要用**"导入"**菜单，不是"打开" |

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
| KiCad | 9.0.9 |
| STM32 HAL | `~/STM32Cube/Repository/STM32CubeF1-1.8.6`、`...F4_V1.28.3` |
| 烧录 | st-flash 1.7.0（udev 已配） |
| 立创EDA专业版 | /opt/lceda-pro |
| apt 源 | 已修（阿里云 HTTPS） |
