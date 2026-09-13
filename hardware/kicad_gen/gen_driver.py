#!/usr/bin/env python3
"""
生成驱动板 F103 完整原理图 (.kicad_sch)

元件连接取自 hardware/driver_board_f103/netlist.py
符号来自 KiCad 官方库 (缺失的 L6234/AS5600/MP2225 用自定义符号)
连接方式: 每个引脚贴同名网络标签
"""

import os, copy, uuid as _uuid
import sexp

SYMDIR = '/usr/share/kicad/symbols'
OUT = os.path.join(os.path.dirname(__file__), '..', 'driver_board_f103', 'driver_f103.kicad_sch')

# ---- 元件 -> (KiCad库, 符号名) ----
SYMMAP = {
    'STM32F103C8T6': ('MCU_ST_STM32F1', 'STM32F103C8Tx'),
    'MPU6050':       ('Sensor_Motion', 'MPU-6050'),
    'AMS1117-3.3':   ('Regulator_Linear', 'AMS1117-3.3'),
    'TJA1050':       ('Interface_CAN_LIN', 'TJA1051T'),
    'CH340C':        ('Interface_USB', 'CH340C'),
    'R':             ('Device', 'R'),
    'C':             ('Device', 'C'),
    'L':             ('Device', 'L'),
    'D_Schottky':    ('Device', 'D_Schottky'),
    'LED':           ('Device', 'LED'),
    'SW_SPST':       ('Switch', 'SW_SPST'),
    'Conn_01x02':    ('Connector_Generic', 'Conn_01x02'),
    'Conn_01x03':    ('Connector_Generic', 'Conn_01x03'),
    'Conn_01x04':    ('Connector_Generic', 'Conn_01x04'),
}

# ---- 自定义符号 (KiCad 库里没有的) ----
def rect_symbol(name, left, right, pin_len=3.81, width=15.24):
    n = max(len(left), len(right))
    hh = max(n * 2.54 / 2 + 2.54, 5.08); hw = width / 2
    o = [f'    (symbol "{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
         f'      (property "Reference" "U" (id 0) (at 0 {hh+1.27:.2f} 0) (effects (font (size 1.27 1.27))))',
         f'      (property "Value" "{name}" (id 1) (at 0 {-hh-1.27:.2f} 0) (effects (font (size 1.27 1.27))))',
         f'      (property "Footprint" "" (id 2) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         f'      (property "Datasheet" "" (id 3) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         f'      (symbol "{name}_0_1"',
         f'        (rectangle (start {-hw:.2f} {hh:.2f}) (end {hw:.2f} {-hh:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))',
         f'      (symbol "{name}_1_1"']
    for i, it in enumerate(left):
        num, pn = it.split(':', 1) if ':' in it else (it, it)
        y = (len(left)-1)*2.54/2 - i*2.54
        o.append(f'        (pin passive line (at {-hw-pin_len:.2f} {y:.2f} 0) (length {pin_len}) (name "{pn}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
    for i, it in enumerate(right):
        num, pn = it.split(':', 1) if ':' in it else (it, it)
        y = (len(right)-1)*2.54/2 - i*2.54
        o.append(f'        (pin passive line (at {hw+pin_len:.2f} {y:.2f} 180) (length {pin_len}) (name "{pn}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
    o.append('      ))')
    return '\n'.join(o)

CUSTOM = {
 'L6234': rect_symbol('L6234',
    ['1:GND','2:SENSE1','3:EN2','4:IN2','5:OUT2','6:OUT1','7:IN1','8:EN1','9:Vs','10:GND'],
    ['11:GND','12:Vs','13:EN3','14:IN3','15:OUT3','16:Vref','17:Vcp','18:Vboot','19:SENSE2','20:GND']),
 'AS5600': rect_symbol('AS5600',
    ['1:VDD5V','2:VDD3V3','3:OUT','4:GND'],
    ['8:DIR','7:SCL','6:SDA','5:PGO']),
 'MP2225': rect_symbol('MP2225',
    ['2:IN','6:EN','7:VCC','1:AGND'],
    ['5:BST','3:SW','8:FB','4:GND']),
}

# ---- 引脚名别名 (网表名 -> KiCad 符号引脚名) ----
ALIAS = {
    ('U8','IN'):  'VI',    # AMS1117
    ('U8','OUT'): 'VO',
    ('U1','VDD'): 'VDD',   # STM32 可能有 VDD_1..n, 用前缀匹配
    ('U1','VSS'): 'VSS',
}

# ---- 元件清单: (位号, 器件类型/符号, 值, x, y) ----
# 分区摆放: 左=电源, 中=MCU, 右=驱动/外设
# 功能分组 (自动布局用, 避免导线重叠短路)
GROUPS = [
  # 电源输入
  [('J1','Conn_01x02','BAT'), ('SW1','SW_SPST','SW'), ('D1','D_Schottky','SS34'),
   ('U7','MP2225','MP2225'), ('L1','L','4.7uH'), ('U8','AMS1117-3.3','AMS1117-3.3')],
  # 电源支撑元件
  [('R1','R','100k'), ('C1','C','22uF'), ('C2','C','0.1uF'), ('C23','C','1uF'),
   ('C24','C','0.1uF'), ('C3','C','22uF'), ('C4','C','0.1uF'),
   ('R2','R','40.2k'), ('R3','R','5.49k'), ('R11','R','1k'), ('D2','LED','RED')],
  # MCU + 支撑
  [('U1','STM32F103C8T6','STM32F103C8T6'), ('R10','R','10k'), ('C19','C','100nF'),
   ('R9','R','10k'), ('C25','C','100nF'), ('R12','R','100k'), ('R13','R','100k')],
  # 电机驱动 + 支撑
  [('U2','L6234','L6234'), ('U3','L6234','L6234'), ('J2','Conn_01x03','M1'),
   ('J3','Conn_01x03','M2'), ('C5','C','100uF'), ('C6','C','100nF'),
   ('C13','C','220nF'), ('C14','C','1uF'), ('C15','C','10nF'),
   ('C16','C','220nF'), ('C17','C','1uF'), ('C18','C','10nF')],
  # 编码器 / IMU + 支撑
  [('U4','AS5600','AS5600'), ('U5','AS5600','AS5600'), ('U6','MPU6050','MPU6050'),
   ('R4','R','4.7k'), ('R5','R','4.7k'), ('R6','R','4.7k'), ('R7','R','4.7k'),
   ('C11','C','100nF'), ('C12','C','100nF'), ('C20','C','2.2uF'), ('C21','C','0.1uF')],
  # CAN / USB / SWD
  [('U9','TJA1050','TJA1051T'), ('R8','R','120'), ('U10','CH340C','CH340C'),
   ('C22','C','10nF'), ('J4','Conn_01x04','SWD'), ('J5','Conn_01x04','USB')],
]

# 自动布局: x/y 间距足够大, 保证引脚外伸导线互不重叠
LAYOUT_X0, LAYOUT_Y0 = 40.0, 40.0
LAYOUT_DX, LAYOUT_DY = 55.0, 45.0
LAYOUT_PER_ROW = 6
LAYOUT_GROUP_GAP = 20.0

def _autolayout():
    out, y = [], LAYOUT_Y0
    for grp in GROUPS:
        rows = (len(grp) + LAYOUT_PER_ROW - 1) // LAYOUT_PER_ROW
        for i, (d, t, v) in enumerate(grp):
            r, c = divmod(i, LAYOUT_PER_ROW)
            out.append((d, t, v, LAYOUT_X0 + c * LAYOUT_DX, y + r * LAYOUT_DY))
        y += rows * LAYOUT_DY + LAYOUT_GROUP_GAP
    return out

COMPS = _autolayout()

_OLD_COMPS_UNUSED = [
    # ---- 电源区 ----
    ('J1','Conn_01x02','BAT',  25, 40),
    ('SW1','SW_SPST','SW',     50, 40),
    ('D1','D_Schottky','SS34', 75, 40),
    ('U7','MP2225','MP2225',   110, 40),
    ('L1','L','4.7uH',         140, 40),
    ('U8','AMS1117-3.3','AMS1117-3.3', 175, 40),
    ('C1','C','22uF',  100, 70),      # 输入
    ('C2','C','0.1uF', 115, 70),
    ('C3','C','22uF',  150, 70),      # 输出
    ('C4','C','0.1uF', 165, 70),
    ('R1','R','100k',  90, 55),       # EN 上拉
    ('R2','R','40.2k', 200, 40),      # 反馈
    ('R3','R','5.49k', 200, 60),
    ('C23','C','1uF',  125, 55),      # MP2225 VCC
    ('C24','C','0.1uF', 148, 55),     # MP2225 BST
    ('R11','R','1k',   205, 15),      # LED 限流
    ('D2','LED','RED', 218, 15),
    # ---- MCU ----
    ('U1','STM32F103C8T6','STM32F103C8T6', 130, 150),
    ('R10','R','10k',  60, 130),      # NRST 上拉
    ('C19','C','100nF', 75, 130),     # NRST 电容
    ('R9','R','10k',   90, 130),      # BOOT0 下拉
    ('C25','C','100nF', 105, 130),    # 去耦
    ('R12','R','100k', 120, 130),    # 电池分压上
    ('R13','R','100k', 135, 130),    # 电池分压下
    # ---- 电机驱动 ----
    ('U2','L6234','L6234', 35, 230),
    ('U3','L6234','L6234', 130, 230),
    ('J2','Conn_01x03','M1', 35, 295),
    ('J3','Conn_01x03','M2', 130, 295),
    ('C5','C','100uF', 35, 190),      # 电机轨大电解
    ('C6','C','100nF', 50, 190),
    ('C13','C','220nF', 90, 210),     # U2 Vcp
    ('C14','C','1uF',  105, 210),     # U2 Vboot
    ('C15','C','10nF', 185, 210),     # U2 Vref
    ('C16','C','220nF', 200, 210),    # U3 Vcp
    ('C17','C','1uF',  215, 210),     # U3 Vboot
    ('C18','C','10nF', 230, 210),     # U3 Vref
    # ---- 编码器 / IMU ----
    ('U4','AS5600','AS5600', 315, 150),
    ('U5','AS5600','AS5600', 315, 185),
    ('U6','MPU6050','MPU6050', 315, 230),
    ('R4','R','4.7k', 350, 130),
    ('R5','R','4.7k', 350, 145),
    ('R6','R','4.7k', 350, 160),
    ('R7','R','4.7k', 350, 175),
    ('C11','C','100nF', 355, 150),
    ('C12','C','100nF', 355, 230),
    ('C20','C','2.2uF', 355, 245),    # MPU CPOUT
    ('C21','C','0.1uF', 355, 260),    # MPU REGOUT
    # ---- CAN / USB / SWD ----
    ('U9','TJA1050','TJA1051T', 35, 350),
    ('R8','R','120', 70, 350),
    ('U10','CH340C','CH340C', 130, 350),
    ('C22','C','10nF', 175, 375),     # CH340C V3
    ('J4','Conn_01x04','SWD', 250, 350),
    ('J5','Conn_01x04','USB', 300, 350),
]

# ---- 网络 (取自 netlist.py) ----
NETS = {
 # ---- 电源树 ----
 "VIN":     [("J1","1"),("SW1","1"),("D1","K"),("U2","Vs"),("U3","Vs"),("U7","IN"),
             ("C1","1"),("C2","1"),("C5","1"),("C6","1"),("R1","1"),("R12","2")],
 "SW_OUT":  [("SW1","2"),("D1","A")],
 "SW_NODE": [("U7","SW"),("L1","1")],
 "BST":     [("U7","BST"),("C24","1")],
 "MP_VCC":  [("U7","VCC"),("C23","1")],
 "MP_EN":   [("U7","EN"),("R1","2")],
 "+5V":     [("L1","2"),("U8","VI"),("U9","VCC"),("U10","VCC"),("C3","1"),("C4","1"),("J5","1")],
 "+3V3":    [("U8","VO"),("U1","VDD"),("U1","VBAT"),("U1","VDDA"),
             ("U4","VDD3V3"),("U4","VDD5V"),("U5","VDD3V3"),("U5","VDD5V"),
             ("U6","VDD"),("U6","VLOGIC"),("C11","1"),("C12","1"),("C25","1"),
             ("R4","2"),("R5","2"),("R6","2"),("R7","2"),("R10","2"),("R11","1"),("J4","4"),("R2","2")],
 "GND":     [("J1","2"),("U1","VSS"),("U1","VSSA"),("J4","3"),("J5","4"),
             ("U2","GND"),("U3","GND"),("U2","SENSE1"),("U2","SENSE2"),
             ("U3","SENSE1"),("U3","SENSE2"),
             ("U4","GND"),("U4","DIR"),("U4","PGO"),("U5","GND"),("U5","DIR"),("U5","PGO"),
             ("U6","GND"),("U6","AD0"),("U6","FSYNC"),("U6","CLKIN"),("U6","RESV"),
             ("U7","GND"),("U7","AGND"),("U8","GND"),("U9","GND"),("U9","S"),("U10","GND"),
             ("C1","2"),("C2","2"),("C3","2"),("C4","2"),("C5","2"),("C6","2"),
             ("C11","2"),("C12","2"),("C13","2"),("C14","2"),("C15","2"),("C16","2"),
             ("C17","2"),("C18","2"),("C19","2"),("C20","2"),("C21","2"),
             ("C22","2"),("C23","2"),("C24","2"),("C25","2"),
             ("R3","2"),("R9","2"),("D2","K"),("R13","2")],
 # ---- L6234 支撑 ----
 "MP_VCP1":  [("U2","Vcp"),("C13","1")],
 "MP_VB1":   [("U2","Vboot"),("C14","1")],
 "MP_VR1":   [("U2","Vref"),("C15","1")],
 "MP_VCP2":  [("U3","Vcp"),("C16","1")],
 "MP_VB2":   [("U3","Vboot"),("C17","1")],
 "MP_VR2":   [("U3","Vref"),("C18","1")],
 # ---- STM32 支撑 ----
 "NRST":    [("U1","NRST"),("R10","1"),("C19","1")],
 "BOOT0":   [("U1","BOOT0"),("R9","1")],
 "LED_A":   [("R11","2"),("D2","A")],
 # ---- MPU6050 支撑 ----
 "MPU_CP":  [("U6","CPOUT"),("C20","1")],
 "MPU_RE":  [("U6","REGOUT"),("C21","1")],
 # ---- CH340C / USB ----
 "CH340_V3": [("U10","V3"),("C22","1")],
 "USB_DP":  [("U10","UD+"),("J5","3")],
 "USB_DM":  [("U10","UD-"),("J5","2")],
 # ---- 电机信号 ----
 "M1_PHA":  [("U2","IN1"),("U1","PA8")],
 "M1_PHB":  [("U2","IN2"),("U1","PA9")],
 "M1_PHC":  [("U2","IN3"),("U1","PA10")],
 "M1_EN":   [("U2","EN1"),("U2","EN2"),("U2","EN3"),("U1","PB1")],
 "M1_OUT1": [("U2","OUT1"),("J2","1")],
 "M1_OUT2": [("U2","OUT2"),("J2","2")],
 "M1_OUT3": [("U2","OUT3"),("J2","3")],
 "M2_PHA":  [("U3","IN1"),("U1","PA6")],
 "M2_PHB":  [("U3","IN2"),("U1","PA7")],
 "M2_PHC":  [("U3","IN3"),("U1","PB0")],
 "M2_EN":   [("U3","EN1"),("U3","EN2"),("U3","EN3"),("U1","PB12")],
 "M2_OUT1": [("U3","OUT1"),("J3","1")],
 "M2_OUT2": [("U3","OUT2"),("J3","2")],
 "M2_OUT3": [("U3","OUT3"),("J3","3")],
 "I2C1_SCL": [("U1","PB6"),("U4","SCL"),("R4","1")],
 "I2C1_SDA": [("U1","PB7"),("U4","SDA"),("R5","1")],
 "I2C2_SCL": [("U1","PB10"),("U5","SCL"),("U6","SCL"),("R6","1")],
 "I2C2_SDA": [("U1","PB11"),("U5","SDA"),("U6","SDA"),("R7","1")],
 "CAN_RX":  [("U1","PA11"),("U9","RXD")],
 "CAN_TX":  [("U1","PA12"),("U9","TXD")],
 "CAN_H":   [("U9","CANH"),("R8","1")],
 "CAN_L":   [("U9","CANL"),("R8","2")],
 "UART2_TX": [("U1","PA2"),("U10","RXD")],
 "UART2_RX": [("U1","PA3"),("U10","TXD")],
 "SWDIO":   [("U1","PA13"),("J4","1")],
 "SWCLK":   [("U1","PA14"),("J4","2")],
 "FB":      [("U7","FB"),("R2","1"),("R3","1")],
 "BAT_DIV": [("R12","1"),("R13","1"),("U1","PA0")],   # 电池分压中点 -> ADC
}
# R4-R7 另一端接 +3V3 (上拉)
for r in ("R4","R5","R6","R7"):
    NETS["+3V3"].append((r,"2"))


def uid(): return str(_uuid.uuid4())

class Lib:
    def __init__(self): self.c = {}
    def root(self, l):
        if l not in self.c:
            p = os.path.join(SYMDIR, l + '.kicad_sym')
            self.c[l] = sexp.load(p) if os.path.exists(p) else None
        return self.c[l]
    def pins(self, libname, symname):
        r = self.root(libname)
        s = sexp.find_symbol(r, symname) if r else None
        return sexp.symbol_pins(s, r) if s else []
    def embed(self, libname, symname):
        r = self.root(libname); s = sexp.find_symbol(r, symname)
        if not s: return None
        node = copy.deepcopy(s); node[1] = '"%s:%s"' % (libname, symname)
        parent = sexp.extends_of(node)
        node = [e for e in node if not (isinstance(e, list) and e and e[0] == 'extends')]
        if parent:
            ps = sexp.find_symbol(r, parent)
            if ps:
                for sub in ps:
                    if isinstance(sub, list) and sub and sub[0] == 'symbol':
                        s2 = copy.deepcopy(sub)
                        s2[1] = '"%s"' % s2[1].strip('"').replace(parent, symname)
                        node.append(s2)
        return sexp.dump(node)


# ---- 封装 (立创EDA ERC 要求每个元件有封装) ----
FOOTPRINTS = {
    'STM32F103C8T6': 'Package_QFP:LQFP-48_7x7mm_P0.5mm',
    'L6234':         'Package_SO:PowerSO-20_11.1x15.9mm_P1.27mm',
    'AS5600':        'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    'MPU6050':       'Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm',
    'AMS1117-3.3':   'Package_TO_SOT_SMD:SOT-223-3_TabPin2',
    'TJA1050':       'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    'CH340C':        'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    'MP2225':        'Package_TO_SOT_SMD:TSOT-23-8',
    'R':             'Resistor_SMD:R_0805_2012Metric',
    'C':             'Capacitor_SMD:C_0805_2012Metric',
    'L':             'Inductor_SMD:L_Bourns-SRN6045',
    'D_Schottky':    'Diode_SMD:D_SMA',
    'LED':           'LED_SMD:LED_0805_2012Metric',
    'SW_SPST':       'Button_Switch_SMD:SW_SPST_PTS645',
    'Conn_01x02':    'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
    'Conn_01x03':    'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
    'Conn_01x04':    'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
}

STUB = 3.81   # 引脚外伸导线长度 (mm)


def _custom_pins(typ):
    """解析自定义符号引脚 -> [(num, name, x, y, angle)]"""
    import re
    pins = []
    for line in CUSTOM[typ].split('\n'):
        if '(pin passive line' in line:
            m = re.search(r'\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)', line)
            nm = re.search(r'\(name "([^"]*)"', line)
            nu = re.search(r'\(number "([^"]*)"', line)
            if m and nm and nu:
                pins.append((nu.group(1), nm.group(1),
                             float(m.group(1)), float(m.group(2)), float(m.group(3))))
    return pins


def main():
    import math
    lib = Lib()
    lib_blocks, seen = [], set()
    symbols, pinpos, wires = [], {}, []
    lib_fp = {}   # lib_id -> 封装
    warnings = []

    for des, typ, val, x, y in COMPS:
        if typ in CUSTOM:
            pins = _custom_pins(typ)
            lib_id = 'CUSTOM:' + typ
            lib_fp.setdefault(lib_id, FOOTPRINTS.get(typ, ''))
            if lib_id not in seen:
                # 关键: lib_symbols 里的符号名必须与实例引用的 lib_id 一致
                blk = CUSTOM[typ].replace(f'(symbol "{typ}"', f'(symbol "{lib_id}"', 1)
                lib_blocks.append(blk); seen.add(lib_id)
        else:
            libname, symname = SYMMAP[typ]
            pins = lib.pins(libname, symname)
            lib_id = '%s:%s' % (libname, symname)
            lib_fp.setdefault(lib_id, FOOTPRINTS.get(typ, ''))
            if lib_id not in seen:
                e = lib.embed(libname, symname)
                if e: lib_blocks.append(e); seen.add(lib_id)
        pinpos[des] = [(n, nm, x + px, y - py, ang) for (n, nm, px, py, ang) in pins]
        # 符号实例 (带封装)
        fp = FOOTPRINTS.get(typ, '')
        s = [f'  (symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0) (unit 1)',
             '    (in_bom yes) (on_board yes)', f'    (uuid {uid()})',
             f'    (property "Reference" "{des}" (id 0) (at {x:.2f} {y-3:.2f} 0) (effects (font (size 1.27 1.27))))',
             f'    (property "Value" "{val}" (id 1) (at {x:.2f} {y+3:.2f} 0) (effects (font (size 1.27 1.27))))',
             f'    (property "Footprint" "{fp}" (id 2) (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) hide))',
             f'    (property "Datasheet" "" (id 3) (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) hide))']
        for (n, nm, px, py, ang) in pins:
            s.append(f'    (pin "{n}" (uuid {uid()}))')
        s.append('  )')
        symbols.append('\n'.join(s))

    # 生成"导线 + 线尾标签" (立创EDA 要求标签贴在线/总线上)
    labels = []
    for net, conns in NETS.items():
        for des, pname in conns:
            if des not in pinpos:
                warnings.append(f"{des} 不在元件表"); continue
            hit = False
            alias = ALIAS.get((des, pname), pname)
            for (num, nm, px, py, ang) in pinpos[des]:
                if nm == alias or num == pname or (nm and nm.startswith(alias + '_')):
                    a = math.radians(ang)
                    ex = px - STUB * math.cos(a)      # 导线朝引脚反向伸出
                    ey = py + STUB * math.sin(a)
                    wires.append(f'  (wire (pts (xy {px:.2f} {py:.2f}) (xy {ex:.2f} {ey:.2f}))\n'
                                 f'    (stroke (width 0) (type default)) (uuid {uid()}))')
                    labels.append(f'  (label "{net}" (at {ex:.2f} {ey:.2f} 0)\n'
                                  f'    (effects (font (size 1.0 1.0)) (justify left bottom))\n'
                                  f'    (uuid {uid()}))')
                    hit = True
            if not hit:
                warnings.append(f"{des}.{pname} ({net}) 未匹配引脚")

    # 未使用的引脚打 no_connect 标记 (让 ERC 干净)
    used = {}   # des -> set(引脚编号)
    for net, conns in NETS.items():
        for des, pname in conns:
            alias = ALIAS.get((des, pname), pname)
            for (num, nm, px, py, ang) in pinpos.get(des, []):
                if nm == alias or num == pname or (nm and nm.startswith(alias + '_')):
                    used.setdefault(des, set()).add(num)
    nocons = []
    for des in pinpos:
        for (num, nm, px, py, ang) in pinpos[des]:
            if num not in used.get(des, set()):
                nocons.append(f'  (no_connect (at {px:.2f} {py:.2f}) (uuid {uid()}))')

    # 把封装也写进 lib_symbols 定义 (立创EDA 从符号定义读取封装)
    patched = []
    for b in lib_blocks:
        for lid, fp in lib_fp.items():
            if fp and ('(symbol "%s"' % lid) in b:
                b = b.replace('(property "Footprint" ""',
                              '(property "Footprint" "%s"' % fp, 1)
                break
        patched.append(b)
    lib_blocks = patched

    # 写文件: 导线 -> 标签 -> 符号 -> 未连接
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('(kicad_sch (version 20210126) (generator eeschema)\n\n  (paper "A1")\n\n')
        f.write('  (title_block\n    (title "JB-Micro-Wheeled_leg-Robot Driver Board (STM32F103)")\n'
                '    (rev "1.0")\n  )\n\n  (lib_symbols\n')
        for b in lib_blocks: f.write(b + '\n')
        f.write('  )\n\n')
        for w in wires: f.write(w + '\n')
        f.write('\n')
        for l in labels: f.write(l + '\n')
        f.write('\n')
        for s in symbols: f.write(s + '\n\n')
        for n in nocons: f.write(n + '\n')
        f.write('\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n')

    print(f"生成 {OUT}")
    print(f"  元件 {len(symbols)}, 导线 {len(wires)}, 标签 {len(labels)}, "
          f"未连接 {len(nocons)}, 符号库 {len(lib_blocks)}")
    if warnings:
        print(f"  [警告] {len(warnings)} 条:")
        for w in warnings[:30]: print("    -", w)


if __name__ == '__main__':
    main()
