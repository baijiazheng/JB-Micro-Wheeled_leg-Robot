#!/usr/bin/env python3
"""
主控板 F407 网表定义 + 校验
用法: python3 netlist.py
"""

COMPONENTS = [
    ("U1",  "STM32F407VET6",  "",      "LQFP-100",  "主控 MCU"),
    ("U2",  "TJA1050",        "",      "SOIC-8",    "CAN 收发器"),
    ("U3",  "CH340C",         "",      "SOP-16",    "USB 转串口"),
    ("U4",  "AMS1117-3.3",    "",      "SOT-223",   "LDO 5V->3.3V"),
    ("U5",  "MP2225GJ-Z",     "",      "TSOT-23-8", "降压 7.4V->5V"),
    ("L1",  "电感",           "4.7uH", "SMD",       "降压电感"),
    ("R1",  "电阻",           "100k",  "0805",      "MP2225 EN 上拉"),
    ("R2",  "电阻",           "40.2k", "0805",      "MP2225 反馈"),
    ("R3",  "电阻",           "5.49k", "0805",      "MP2225 反馈"),
    ("R4",  "电阻",           "120Ω",  "0805",      "CAN 终端"),
    ("R5",  "电阻",           "10k",   "0603",      "NRST 上拉"),
    ("C1",  "电容",           "22uF",  "0805",      "MP2225 输入"),
    ("C2",  "电容",           "0.1uF", "0805",      "MP2225 输入"),
    ("C3",  "电容",           "22uF",  "0805",      "MP2225 输出"),
    ("C4",  "电容",           "0.1uF", "0805",      "MP2225 输出"),
    ("C5",  "电容",           "100nF", "0805",      "MCU 去耦"),
    ("C6",  "电容",           "100nF", "0805",      "MCU 去耦"),
    ("C7",  "电容",           "100nF", "0805",      "MCU 去耦"),
    ("D1",  "肖特基",         "SS34",  "SMA",       "防反接"),
    ("D2",  "LED",            "红",    "0805",      "电源指示"),
    ("J1",  "连接器",         "XH2.54", "TH",       "电池输入"),
    ("J2",  "连接器",         "3P",    "TH",        "舵机总线 (DATA/VIN/GND)"),
    ("J3",  "连接器",         "2P",    "TH",        "CAN 总线 (CANH/CANL)"),
    ("J4",  "连接器",         "4P",    "TH",        "SWD 调试"),
    ("J5",  "连接器",         "MicroUSB", "SMD",    "USB 调试"),
    ("SW1", "开关",           "SS-12D02", "TH",     "总电源开关"),
]

NETS = {
    # ---- 电源 ----
    "VIN":     [("J1","1"), ("SW1","1"), ("D1","K"), ("U5","IN"), ("J2","2")],
    "SW_OUT":  [("SW1","2"), ("D1","A")],
    "SW_NODE": [("U5","SW"), ("L1","1")],
    "+5V":     [("L1","2"), ("U4","IN"), ("U3","VCC")],
    "+3V3":    [("U4","OUT"), ("U1","VDD"), ("U2","VCC")],
    "GND":     [("J1","2"), ("U1","VSS"), ("U2","GND"), ("U3","GND"),
                ("U4","GND"), ("U5","GND"), ("J2","3")],

    # ---- CAN (PB8/PB9) ----
    "CAN_RX":  [("U1","PB8"), ("U2","RXD")],
    "CAN_TX":  [("U1","PB9"), ("U2","TXD")],
    "CAN_H":   [("U2","CANH"), ("R4","1"), ("J3","1")],
    "CAN_L":   [("U2","CANL"), ("R4","2"), ("J3","2")],

    # ---- 舵机总线 (USART6 半双工, PC6) ----
    "SERVO_DATA": [("U1","PC6"), ("J2","1")],

    # ---- USB 调试串口 (USART1 PA9/PA10) ----
    "UART1_TX": [("U1","PA9"), ("U3","RXD")],
    "UART1_RX": [("U1","PA10"), ("U3","TXD")],

    # ---- SWD ----
    "SWDIO":   [("U1","PA13"), ("J4","1")],
    "SWCLK":   [("U1","PA14"), ("J4","2")],

    # ---- 电源树 ----
    "FB":      [("U5","FB"), ("R2","1"), ("R3","1")],
}

def validate():
    errors = []
    pins = {}
    for net, conns in NETS.items():
        for c, p in conns:
            key = (c, p)
            if key in pins:
                errors.append(f"引脚重复: {c}.{p} -> {pins[key]} 和 {net}")
            pins[key] = net
    for req in ["VIN", "+5V", "+3V3", "GND", "CAN_H", "CAN_L", "SERVO_DATA"]:
        if req not in NETS:
            errors.append(f"缺少关键网络: {req}")
    return errors, pins

if __name__ == "__main__":
    errors, pins = validate()
    print("========== 主控板 F407 网表校验 ==========")
    print(f"元件: {len(COMPONENTS)} 个 | 网络: {len(NETS)} 个 | 连线: {sum(len(v) for v in NETS.values())} 条")
    if errors:
        print(f"[FAIL] {len(errors)} 个错误:")
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)
    print("[ OK ] 网表校验通过 ✅")
