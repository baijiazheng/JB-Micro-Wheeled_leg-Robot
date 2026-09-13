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
    'SW_SPST':[('1','1'), ('2','2')],
    'Conn_01x02': [('1','1'), ('2','2')],
    'Conn_01x03': [('1','1'), ('2','2'), ('3','3')],
    'Conn_01x04': [('1','1'), ('2','2'), ('3','3'), ('4','4')],
    'USB':    [('1','VBUS'), ('2','D-'), ('3','D+'), ('4','GND')],
    'L6234':  [('1','GND'),('2','SENSE1'),('3','EN2'),('4','IN2'),('5','OUT2'),('6','OUT1'),
               ('7','IN1'),('8','EN1'),('9','Vs'),('10','GND'),('11','GND'),('12','Vs'),
               ('13','EN3'),('14','IN3'),('15','OUT3'),('16','Vref'),('17','Vcp'),('18','Vboot'),
               ('19','SENSE2'),('20','GND')],
    'AS5600': [('1','VDD5V'),('2','VDD3V3'),('3','OUT'),('4','GND'),
               ('5','PGO'),('6','SDA'),('7','SCL'),('8','DIR')],
    'MP2225': [('1','AGND'),('2','IN'),('3','SW'),('4','GND'),
               ('5','BST'),('6','EN'),('7','VCC'),('8','FB')],
    'AMS1117-3.3': [('1','GND'),('2','VO'),('3','VI')],
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
STM32F103 = stm32_pins([
    (1,'VBAT'),(2,'PC13'),(3,'PC14'),(4,'PC15'),(5,'PD0'),(6,'PD1'),(7,'NRST'),(8,'VSSA'),
    (9,'VDDA'),(10,'PA0'),(11,'PA1'),(12,'PA2'),(13,'PA3'),(14,'PA4'),(15,'PA5'),(16,'PA6'),
    (17,'PA7'),(18,'PB0'),(19,'PB1'),(20,'PB2'),(21,'PB10'),(22,'PB11'),(23,'VSS'),(24,'VDD'),
    (25,'PB12'),(26,'PB13'),(27,'PB14'),(28,'PB15'),(29,'PA8'),(30,'PA9'),(31,'PA10'),
    (32,'PA11'),(33,'PA12'),(34,'PA13'),(35,'VSS'),(36,'VDD'),(37,'PA14'),(38,'PA15'),
    (39,'PB3'),(40,'PB4'),(41,'PB5'),(42,'PB6'),(43,'PB7'),(44,'BOOT0'),(45,'PB8'),(46,'PB9'),
    (47,'VSS'),(48,'VDD'),
])

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
    for i, (num, nm) in enumerate(left):
        py = y - hh + 15 + i * 10
        subs.append(gen_pin(x - hw, py, 0, num, uid()))
        pinpos[num] = (x - hw, py, 0)
    for i, (num, nm) in enumerate(right):
        py = y - hh + 15 + i * 10
        subs.append(gen_pin(x + hw, py, 180, num, uid()))
        pinpos[num] = (x + hw, py, 180)
    settings = (f'package`{pkg}`nameAlias`Value``BOM_Supplier Part``BOM_Supplier``'
                f'Contributor`LCEDA_Lib`spicePre`U`spiceSymbolName`{symbol_name}``~~')
    header = f'LIB~{fmt(x)}~{fmt(y)}~{settings}0~{uid()}~{uid()}~{uid()}~0~~yes~yes~~0~'
    return header + ''.join(subs), pinpos

def gen_pin(x, y, rot, num, pid, length=10):
    """格式对齐参考项目模板 (短格式): 连接点=引脚坐标, 线向符号体内延伸"""
    x, y = float(x), float(y)
    if rot == 180:      # 朝左: 线向左延 (-)
        line = f'M {fmt(x)} {fmt(y)} h -{length}'
    else:               # 朝右: 线向右延 (+)
        line = f'M {fmt(x)} {fmt(y)} h {length}'
    return (f'#@$P~show~0~{num}~{fmt(x)}~{fmt(y)}~{rot}~{pid}~0'
            f'^^{fmt(x)}~{fmt(y)}^^{line}~')

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
            ex = px + (14 if rot == 180 else -14)
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

    # ---- 驱动板 F103 ----
    comps_d, i = [], 0
    for grp in gd.GROUPS:
        for (d, t, v) in grp:
            r, c = divmod(i, 6)
            comps_d.append((d, t, v, 300 + c * 260, 300 + r * 220))
            i += 1
    PINS['STM32F103C8T6'] = STM32F103
    n1 = build(comps_d, gd.NETS, os.path.join(ROOT, 'driver_board_f103', 'driver_f103_立创EDA.json'),
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
    F407 = [(str(n), nm) for n, nm in [
        (1,'VBAT'),(6,'VBAT'),(12,'PH0'),(13,'PH1'),(14,'NRST'),(19,'VSSA'),(20,'VREF-'),
        (21,'VREF+'),(22,'VDDA'),(23,'PA0'),(24,'PA1'),(25,'PA2'),(26,'PA3'),(29,'PA4'),
        (30,'PA5'),(31,'PA6'),(32,'PA7'),(33,'PB0'),(34,'PB1'),(35,'PB2'),(36,'PB3'),
        (37,'PB4'),(38,'PB5'),(39,'PB6'),(40,'PB7'),(41,'PB8'),(42,'PB9'),(45,'PB10'),
        (46,'PB11'),(49,'VSS'),(50,'VDD'),(51,'PB12'),(52,'PB13'),(53,'PB14'),(54,'PB15'),
        (55,'PD8'),(56,'PD9'),(57,'PD10'),(58,'PD11'),(59,'PD12'),(60,'PD13'),(61,'PD14'),
        (62,'PD15'),(63,'PC6'),(64,'PC7'),(65,'PC8'),(66,'PC9'),(67,'PA8'),(68,'PA9'),
        (69,'PA10'),(70,'PA11'),(71,'PA12'),(72,'PA13'),(76,'PA14'),(77,'PA15'),(78,'PC10'),
        (79,'PC11'),(80,'PC12'),(81,'PD0'),(82,'PD1'),(83,'PD2'),(84,'PD3'),(85,'PD4'),
        (86,'PD5'),(87,'PD6'),(88,'PD7'),(89,'PB3'),(90,'PB4'),(91,'PB5'),(92,'PB6'),
        (93,'PB7'),(94,'BOOT0'),(95,'PB8'),(96,'PB9'),(97,'PE0'),(98,'PE1'),(99,'VSS'),(100,'VDD'),
    ]]
    PINS['STM32F103C8T6_F4'] = F407
    build(comps_m, gm.g.NETS, os.path.join(ROOT, 'main_board_f407', 'main_f407_立创EDA.json'),
          'JB-Micro-Wheeled_leg-Robot 主控板 (STM32F407)', pin_override={'STM32F103C8T6': F407})
