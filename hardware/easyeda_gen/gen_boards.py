#!/usr/bin/env python3
"""
生成两块板的立创EDA 原生原理图

策略 (为兼容性优先):
  - 元件符号: 自己生成矩形+引脚 (引脚位置完全可控 -> 布线精确)
  - 封装名: 从参考项目模板提取的**立创EDA 原生命名** (保证被识别)
  - 连接: 导线 + 线尾网络标签 (立创EDA 要求)

输出: hardware/*/ 下的 .json (立创EDA 可直接打开)
"""

import json, os, re, uuid as _uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
TPL = json.load(open(os.path.join(HERE, 'templates.json')))

def uid():  return 'gge' + _uuid.uuid4().hex[:10]
def fmt(v):
    v = float(v)
    return str(int(v)) if v == int(v) else f'{v:.2f}'.rstrip('0').rstrip('.')

# ---------- 立创EDA 原生封装名 (从参考模板提取) ----------
PKG = {
    'R':        'R0805',
    'C':        'C0805',
    'L':        'IND-SMD_L7.3-W6.6',
    'D_Schottky': 'SOD-123_L2.8-W1.8-LS3.7-RD',
    'LED':      'LED0805_RED',
    'L6234':    'POWERSO20_L15.9-W11.0-P1.27-LS14.2-BL-EP',
    'AS5600':   'SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL',
    'MP2225':   'TSOT-23-8_L2.9-W1.6-P0.65-LS2.8-BR',
    'AMS1117-3.3': 'SOT-223_L6.7-W3.5-P2.30-BR',
    'TJA1050':  'SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL',
    'CH340C':   'SOP-16_L10.0-W3.9-P1.27-LS6.0-BL',
    'MPU6050':  'QFN-24_L4.0-W4.0-P0.50-BL-EP',
    'STM32F103C8T6': 'LQFP-48_L7.0-W7.0-P0.50-LS9.0-BL',
    'STM32F103C8T6_F4': 'LQFP-100_L14.0-W14.0-P0.50-LS16.0-BL',
    'Conn_01x02': 'HDR-M-2.54_1X2',
    'Conn_01x03': 'HDR-M-2.54_1X3',
    'Conn_01x04': 'HDR-M-2.54_1X4',
    'Conn_GH4':   'GH1.25_4P',
    'Conn_02x04': 'HDR-M-2.54_2X4',
    'SW_SPST':  'SW-TH_SS-12D02-VG4',
    'USB':      'MICRO-USB-SMD_U-C-M5SS-Y-1',
}

# ---------- 引脚定义 (编号:名称) ----------
PINS = {
    'R':      [('1','1'), ('2','2')],
    'C':      [('1','1'), ('2','2')],
    'L':      [('1','1'), ('2','2')],
    'D_Schottky': [('1','K'), ('2','A')],
    'LED':    [('1','K'), ('2','A')],
    'SW_SPST':[('1','1'), ('2','2'), ('3','3'), ('4','4'), ('5','5')],
    'Conn_01x02': [('1','1'), ('2','2')],
    'Conn_01x03': [('1','1'), ('2','2'), ('3','3')],
    'Conn_01x04': [('1','1'), ('2','2'), ('3','3'), ('4','4')],
    # GH1.25 4P 卫星板线序 (全部卫星板统一, 防止插错烧片)
    'Conn_GH4': [('1','+3V3'), ('2','SCL'), ('3','SDA'), ('4','GND')],
    # 板间堆叠 2x4: VIN x2 / GND x4 / CAN 差分对相邻
    'Conn_02x04': [('1','VIN'), ('2','VIN'), ('3','GND'), ('4','GND'),
                   ('5','CAN_H'), ('6','CAN_L'), ('7','GND'), ('8','GND')],
    'USB':    [('1','VBUS'), ('2','D-'), ('3','D+'), ('4','GND')],
    'L6234':  [('1','GND'),('2','SENSE1'),('3','EN2'),('4','IN2'),('5','OUT2'),('6','OUT1'),
               ('7','IN1'),('8','EN1'),('9','Vs'),('10','GND'),('11','GND'),('12','Vs'),
               ('13','EN3'),('14','IN3'),('15','OUT3'),('16','Vref'),('17','Vcp'),('18','Vboot'),
               ('19','SENSE2'),('20','GND')],
    'AS5600': [('1','VDD5V'),('2','VDD3V3'),('3','OUT'),('4','GND'),
               ('5','PGO'),('6','SDA'),('7','SCL'),('8','DIR')],
    'MP2225': [('1','AGND'),('2','IN'),('3','SW'),('4','GND'),
               ('5','BST'),('6','EN'),('7','VCC'),('8','FB')],
    'AMS1117-3.3': [('1','GND'),('2','VO'),('3','VI'),('4','VO')],
    'TJA1050': [('1','TXD'),('2','GND'),('3','VCC'),('4','RXD'),
                ('5','NC'),('6','CANL'),('7','CANH'),('8','S')],
    'CH340C': [('1','GND'),('2','TXD'),('3','RXD'),('4','V3'),('5','UD+'),('6','UD-'),
               ('7','NC'),('8','NC'),('9','NC'),('10','NC'),('11','NC'),('12','NC'),
               ('13','NC'),('14','NC'),('15','R232'),('16','VCC')],
    'MPU6050': [('1','CLKIN'),('2','NC'),('3','NC'),('4','NC'),('5','NC'),('6','AUX_DA'),
                ('7','AUX_CL'),('8','VLOGIC'),('9','AD0'),('10','REGOUT'),('11','FSYNC'),
                ('12','INT'),('13','VDD'),('14','NC'),('15','NC'),('16','NC'),('17','NC'),
                ('18','GND'),('19','RESV'),('20','CPOUT'),('21','RESV'),('22','RESV'),
                ('23','SCL'),('24','SDA')],
    'TJA1051T': [('1','TXD'),('2','GND'),('3','VCC'),('4','RXD'),
                 ('5','NC'),('6','CANL'),('7','CANH'),('8','S')],
}

def stm32_pins(names_by_num):
    return [(str(n), nm) for n, nm in names_by_num]

# STM32F103C8 (48 脚) — 只列用到的+电源, 其余标号
STM32F103 = [
    ('1','VBAT'),
    ('2','PC13'),
    ('3','PC14'),
    ('4','PC15'),
    ('5','PD0'),
    ('6','PD1'),
    ('7','NRST'),
    ('8','VSSA'),
    ('9','VDDA'),
    ('10','PA0'),
    ('11','PA1'),
    ('12','PA2'),
    ('13','PA3'),
    ('14','PA4'),
    ('15','PA5'),
    ('16','PA6'),
    ('17','PA7'),
    ('18','PB0'),
    ('19','PB1'),
    ('20','PB2'),
    ('21','PB10'),
    ('22','PB11'),
    ('23','VSS'),
    ('24','VDD'),
    ('25','PB12'),
    ('26','PB13'),
    ('27','PB14'),
    ('28','PB15'),
    ('29','PA8'),
    ('30','PA9'),
    ('31','PA10'),
    ('32','PA11'),
    ('33','PA12'),
    ('34','PA13'),
    ('35','VSS'),
    ('36','VDD'),
    ('37','PA14'),
    ('38','PA15'),
    ('39','PB3'),
    ('40','PB4'),
    ('41','PB5'),
    ('42','PB6'),
    ('43','PB7'),
    ('44','BOOT0'),
    ('45','PB8'),
    ('46','PB9'),
    ('47','VSS'),
    ('48','VDD'),
]

# ---------- 元件符号生成 ----------
def make_lib(x, y, des, val, pkg, pins, symbol_name):
    """生成一个矩形符号元件 (引脚左右分列)"""
    left  = pins[0::2] if len(pins) > 6 else pins[:len(pins)//2]
    right = pins[1::2] if len(pins) > 6 else pins[len(pins)//2:]
    if len(pins) <= 6:
        left  = pins[:max(1, len(pins)//2)]
        right = pins[max(1, len(pins)//2):]
    n = max(len(left), len(right), 1)
    h = n * 10 + 20
    hw = 60
    hh = h / 2
    subs = []
    subs.append(f'#@$T~P~{fmt(x-20)}~{fmt(y-hh-14)}~0~#000080~Arial~~~~~comment~{des}~1~start~{uid()}~0~')
    subs.append(f'#@$T~N~{fmt(x-20)}~{fmt(y+hh+14)}~0~#000080~Arial~~~~~comment~{val}~1~start~{uid()}~0~')
    subs.append(f'#@$R~{fmt(x-hw)}~{fmt(y-hh)}~~~120~{fmt(h)}~#880000~1~0~none~{uid()}~0~')
    pinpos = {}
    PINLEN = 10
    for i, (num, nm) in enumerate(left):
        py = y - hh + 15 + i * 10
        px = x - hw - PINLEN                      # 连接点在矩形外侧
        subs.append(gen_pin(px, py, 180, num, uid(), nm, PINLEN))
        pinpos[num] = (px, py, 180)
    for i, (num, nm) in enumerate(right):
        py = y - hh + 15 + i * 10
        px = x + hw + PINLEN                      # 连接点在矩形外侧
        subs.append(gen_pin(px, py, 0, num, uid(), nm, PINLEN))
        pinpos[num] = (px, py, 0)
    settings = (f'package`{pkg}`nameAlias`Value``BOM_Supplier Part``BOM_Supplier``'
                f'Contributor`LCEDA_Lib`spicePre`U`spiceSymbolName`{symbol_name}``~~')
    header = f'LIB~{fmt(x)}~{fmt(y)}~{settings}0~{uid()}~{uid()}~{uid()}~0~~yes~yes~~0~'
    return header + ''.join(subs), pinpos

def gen_pin(x, y, rot, num, pid, name='~', length=10):
    """完整引脚格式 (对齐参考项目): 头 + 连接点 + 线 + 名字文本 + 编号文本 + 端部装饰
    约定: rot=180 -> 指向右(线向 +x, 用于符号左侧引脚)
          rot=0   -> 指向左(线向 -x, 用于符号右侧引脚)"""
    x, y = float(x), float(y)
    col = '#000000'
    if rot == 180:      # 指向右
        line = f'M {fmt(x)} {fmt(y)} h {length}'
        nx1, ny1, a1 = x + 13.7, y + 4, 'start'
        nx2, ny2, a2 = x + 9.5,  y - 1, 'end'
        ax, ay = x + 7, y
        dec = f'M {fmt(x+10)} {fmt(y+3)} L {fmt(x+13)} {fmt(y)} L {fmt(x+10)} {fmt(y-3)}'
    else:               # 指向左
        line = f'M {fmt(x)} {fmt(y)} h -{length}'
        nx1, ny1, a1 = x - 13.7, y + 4, 'end'
        nx2, ny2, a2 = x - 9.5,  y - 1, 'start'
        ax, ay = x - 7, y
        dec = f'M {fmt(x-10)} {fmt(y+3)} L {fmt(x-13)} {fmt(y)} L {fmt(x-10)} {fmt(y-3)}'
    return (f'#@$P~show~0~{num}~{fmt(x)}~{fmt(y)}~{rot}~{pid}~0^^{fmt(x)}~{fmt(y)}^^'
            f'{line}~{col}^^1~{fmt(nx1)}~{fmt(ny1)}~0~{name}~{a1}~~~'
            f'{col}^^1~{fmt(nx2)}~{fmt(ny2)}~0~{num}~{a2}~~~'
            f'{col}^^0~{fmt(ax)}~{fmt(ay)}^^0~{dec}')

# ---------- 导线 / 网络标签 ----------
def gen_wire(x1, y1, x2, y2):
    return f'W~{fmt(x1)} {fmt(y1)} {fmt(x2)} {fmt(y2)}~#008800~1~0~none~{uid()}~0'

def gen_netlabel(x, y, name, rot=0):
    return (f'N~{fmt(x)}~{fmt(y)}~{rot}~#0000ff~{name}~{uid()}~end~'
            f'{fmt(x)}~{fmt(y+8)}~Times New Roman~7pt~0')

# ---------- 文档 ----------
def make_doc(title, shapes):
    return {
        'editorVersion': '6.5.34', 'docType': '5', 'title': title,
        'description': '', 'colors': {},
        'schematics': [{'docType': '1', 'title': 'v1.0', 'description': '',
            'dataStr': {
                'head': {'docType': '1', 'editorVersion': '6.5.34', 'newgId': True,
                         'c_para': {'Prefix Start': '1'}, 'c_spiceCmd': 'null',
                         'hasIdFlag': True, 'uuid': _uuid.uuid4().hex,
                         'x': '0', 'y': '0', 'portOfADImportHack': '',
                         'importFlag': 0, 'transformList': ''},
                'canvas': 'CA~1000~1000~#FFFFFF~yes~#CCCCCC~5~1000~1000~line~5~pixel~5~0~0',
                'shape': shapes,
                'BBox': {'x': 0, 'y': 0, 'width': 4000, 'height': 3000},
                'colors': {},
            }}]
    }

def build(comps, nets, out_path, title, pin_override=None):
    """comps: [(des, type, value, x, y)]; nets: {net: [(des, pin_name)]}"""
    shapes, allpins, pinmeta = [], {}, {}
    for des, typ, val, x, y in comps:
        pins = (pin_override or {}).get(typ) or PINS.get(typ)
        if not pins:
            print(f'  [跳过] {des} 类型 {typ} 无引脚定义'); continue
        pkg = PKG.get(typ, PKG.get('STM32F103C8T6_F4' if typ == 'STM32F103C8T6_F4' else typ, 'NONE'))
        lib, pp = make_lib(x, y, des, val, pkg, pins, typ)
        shapes.append(lib)
        allpins[des] = pp
        pinmeta[des] = dict((n, nm) for n, nm in pins)   # 编号 -> 名称

    n_label, n_wire, miss = 0, 0, []
    for net, conns in nets.items():
        for des, pname in conns:
            pp = allpins.get(des)
            if not pp:
                miss.append(f'{des}.{pname}'); continue
            hit = None
            for num, (px, py, rot) in pp.items():
                if num == str(pname) or pinmeta[des].get(num) == pname:
                    hit = (num, px, py, rot); break
            if not hit:
                miss.append(f'{des}.{pname} ({net})'); continue
            num, px, py, rot = hit
            ex = px + (-14 if rot == 180 else 14)
            shapes.append(gen_wire(px, py, ex, py)); n_wire += 1
            shapes.append(gen_netlabel(ex, py, net)); n_label += 1

    json.dump(make_doc(title, shapes), open(out_path, 'w'), ensure_ascii=False, indent=1)
    print(f'生成 {out_path}')
    print(f'  元件 {len(allpins)}, 导线 {n_wire}, 标签 {n_label}')
    if miss:
        print(f'  [警告] {len(miss)} 个未匹配: {miss[:12]}')
    return len(allpins), n_label


# ==================== 两块板的数据 (复用 KiCad 生成器的网表) ====================
if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.join(HERE, '..', 'kicad_gen'))
    import gen_driver as gd
    # 注意: gen_main 在 import 时会把 g.NETS / g.GROUPS 覆盖掉 (它复用 gen_driver 作引擎),
    # 所以这里必须先快照驱动板数据, 否则两块板会生成成同一份网表。
    DRIVER_NETS = {k: list(v) for k, v in gd.NETS.items()}
    DRIVER_GROUPS = [list(grp) for grp in gd.GROUPS]

    # ---- 驱动板 F103 ----
    comps_d, i = [], 0
    for grp in DRIVER_GROUPS:
        for (d, t, v) in grp:
            r, c = divmod(i, 6)
            comps_d.append((d, t, v, 300 + c * 260, 300 + r * 220))
            i += 1
    PINS['STM32F103C8T6'] = STM32F103
    n1 = build(comps_d, DRIVER_NETS, os.path.join(ROOT, 'driver_board_f103', 'driver_f103_立创EDA.json'),
               'JB-Micro-Wheeled_leg-Robot 驱动板 (STM32F103)')
    print()

    # ---- 主控板 F407 ----
    import re as _re
    gm = __import__('gen_main')
    comps_m, j = [], 0
    for grp in gm.g.GROUPS:
        for (d, t, v) in grp:
            r, c = divmod(j, 6)
            comps_m.append((d, t, v, 300 + c * 260, 300 + r * 220))
            j += 1
    F407 = [
        ('1','PE2'),
        ('2','PE3'),
        ('3','PE4'),
        ('4','PE5'),
        ('5','PE6'),
        ('6','VBAT'),
        ('7','PC13'),
        ('8','PC14'),
        ('9','PC15'),
        ('10','VSS'),
        ('11','VDD'),
        ('12','PH0'),
        ('13','PH1'),
        ('14','NRST'),
        ('15','PC0'),
        ('16','PC1'),
        ('17','PC2'),
        ('18','PC3'),
        ('19','VDD'),
        ('20','VSSA'),
        ('21','VREF+'),
        ('22','VDDA'),
        ('23','PA0'),
        ('24','PA1'),
        ('25','PA2'),
        ('26','PA3'),
        ('27','VSS'),
        ('28','VDD'),
        ('29','PA4'),
        ('30','PA5'),
        ('31','PA6'),
        ('32','PA7'),
        ('33','PC4'),
        ('34','PC5'),
        ('35','PB0'),
        ('36','PB1'),
        ('37','PB2'),
        ('38','PE7'),
        ('39','PE8'),
        ('40','PE9'),
        ('41','PE10'),
        ('42','PE11'),
        ('43','PE12'),
        ('44','PE13'),
        ('45','PE14'),
        ('46','PE15'),
        ('47','PB10'),
        ('48','PB11'),
        ('49','VCAP_1'),
        ('50','VDD'),
        ('51','PB12'),
        ('52','PB13'),
        ('53','PB14'),
        ('54','PB15'),
        ('55','PD8'),
        ('56','PD9'),
        ('57','PD10'),
        ('58','PD11'),
        ('59','PD12'),
        ('60','PD13'),
        ('61','PD14'),
        ('62','PD15'),
        ('63','PC6'),
        ('64','PC7'),
        ('65','PC8'),
        ('66','PC9'),
        ('67','PA8'),
        ('68','PA9'),
        ('69','PA10'),
        ('70','PA11'),
        ('71','PA12'),
        ('72','PA13'),
        ('73','VCAP_2'),
        ('74','VSS'),
        ('75','VDD'),
        ('76','PA14'),
        ('77','PA15'),
        ('78','PC10'),
        ('79','PC11'),
        ('80','PC12'),
        ('81','PD0'),
        ('82','PD1'),
        ('83','PD2'),
        ('84','PD3'),
        ('85','PD4'),
        ('86','PD5'),
        ('87','PD6'),
        ('88','PD7'),
        ('89','PB3'),
        ('90','PB4'),
        ('91','PB5'),
        ('92','PB6'),
        ('93','PB7'),
        ('94','BOOT0'),
        ('95','PB8'),
        ('96','PB9'),
        ('97','PE0'),
        ('98','PE1'),
        ('99','VSS'),
        ('100','VDD'),
    ]
    PINS['STM32F103C8T6_F4'] = F407
    build(comps_m, gm.g.NETS, os.path.join(ROOT, 'main_board_f407', 'main_f407_立创EDA.json'),
          'JB-Micro-Wheeled_leg-Robot 主控板 (STM32F407)', pin_override={'STM32F103C8T6': F407})
    print()

    # ==================== 卫星板 ====================
    # 线序统一: GH1.25 4P = 1:+3V3  2:SCL  3:SDA  4:GND
    os.makedirs(os.path.join(ROOT, 'encoder_board'), exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'imu_board'), exist_ok=True)

    # ---- 编码器板 (AS5600) ×2 ----
    # 磁铁 502 粘在电机转轴端面, AS5600 正对磁铁, 轴向间距 0.5~3mm
    enc_comps = [
        ('U1', 'AS5600',  'AS5600',           300, 300),
        ('J2', 'Conn_GH4', 'GH1.25-4P',       560, 300),
        ('R1', 'R', '4.7k',  300, 470),   # I2C 上拉
        ('R2', 'R', '4.7k',  400, 470),   # I2C 上拉
        ('C1', 'C', '100nF', 500, 470),
        ('C2', 'C', '1uF',   600, 470),
    ]
    enc_nets = {
        '+3V3': [('U1','VDD5V'),('U1','VDD3V3'),('C1','1'),('C2','1'),
                 ('R1','2'),('R2','2'),('J2','1')],
        'SCL':  [('U1','SCL'),('R1','1'),('J2','2')],
        'SDA':  [('U1','SDA'),('R2','1'),('J2','3')],
        'GND':  [('U1','GND'),('U1','DIR'),('U1','PGO'),
                 ('C1','2'),('C2','2'),('J2','4')],
    }
    build(enc_comps, enc_nets, os.path.join(ROOT, 'encoder_board', 'encoder_立创EDA.json'),
          'JB-Micro-Wheeled_leg-Robot 编码器板 (AS5600) x2')
    print()

    # ---- IMU 板 (MPU6050) ×1 ----
    # J1 = 从驱动板上行, J2 = 下行串接右轮编码器板 (I2C2 共用)
    imu_comps = [
        ('U1', 'MPU6050',  'MPU6050',   300, 300),
        ('J1', 'Conn_GH4', 'FROM-MCU',  560, 240),
        ('J2', 'Conn_GH4', 'TO-ENC2',   560, 400),
        ('C1', 'C', '100nF', 300, 500),
        ('C2', 'C', '2.2nF', 400, 500),   # CPOUT (手册: 2.2nF, 不是 2.2uF)
        ('C3', 'C', '100nF', 500, 500),   # REGOUT
    ]
    imu_nets = {
        '+3V3': [('U1','VDD'),('U1','VLOGIC'),('C1','1'),('J1','1'),('J2','1')],
        'SCL':  [('U1','SCL'),('J1','2'),('J2','2')],
        'SDA':  [('U1','SDA'),('J1','3'),('J2','3')],
        'GND':  [('U1','GND'),('U1','AD0'),('U1','FSYNC'),('U1','CLKIN'),
                 ('U1','19'),('U1','21'),('U1','22'),
                 ('C1','2'),('C2','2'),('C3','2'),('J1','4'),('J2','4')],
        'CPOUT':  [('U1','CPOUT'),('C2','1')],
        'REGOUT': [('U1','REGOUT'),('C3','1')],
    }
    build(imu_comps, imu_nets, os.path.join(ROOT, 'imu_board', 'imu_立创EDA.json'),
          'JB-Micro-Wheeled_leg-Robot IMU 板 (MPU6050)')
