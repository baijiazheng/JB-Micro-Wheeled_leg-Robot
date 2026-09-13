#!/usr/bin/env python3
"""
KiCad 原理图生成器 (驱动板 F103)

思路:
  1. 从 KiCad 官方库提取符号, 展平 extends 继承, 嵌入 lib_symbols
  2. 缺失元件 (L6234/AS5600/MP2225) 用自定义符号
  3. 放置符号实例
  4. 每个引脚贴同名网络标签 (label) 定义连接
  5. 输出 .kicad_sch, 用 kicad-cli 导出网表反向验证

用法: python3 gen_sch.py [driver|main]
"""

import sys, os, copy, uuid as _uuid
import sexp

SYMDIR = '/usr/share/kicad/symbols'

# ================= 自定义符号 =================
def _rect_symbol(name, left, right, pin_len=3.81, width=15.24):
    """生成矩形符号: left/right 是 ["编号:名称", ...]"""
    n = max(len(left), len(right))
    half_h = max(n * 2.54 / 2 + 2.54, 5.08)
    half_w = width / 2
    out = []
    out.append(f'    (symbol "{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)')
    out.append(f'      (property "Reference" "U" (id 0) (at 0 {half_h + 1.27:.2f} 0) (effects (font (size 1.27 1.27))))')
    out.append(f'      (property "Value" "{name}" (id 1) (at 0 {-half_h - 1.27:.2f} 0) (effects (font (size 1.27 1.27))))')
    out.append(f'      (property "Footprint" "" (id 2) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'      (property "Datasheet" "" (id 3) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'      (symbol "{name}_0_1"')
    out.append(f'        (rectangle (start {-half_w:.2f} {half_h:.2f}) (end {half_w:.2f} {-half_h:.2f})')
    out.append(f'          (stroke (width 0.254) (type default)) (fill (type background))))')
    out.append(f'      (symbol "{name}_1_1"')
    for i, item in enumerate(left):
        num, pn = item.split(':', 1) if ':' in item else (item, item)
        y = (len(left) - 1) * 2.54 / 2 - i * 2.54
        out.append(f'        (pin passive line (at {-half_w - pin_len:.2f} {y:.2f} 0) (length {pin_len}) '
                   f'(name "{pn}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
    for i, item in enumerate(right):
        num, pn = item.split(':', 1) if ':' in item else (item, item)
        y = (len(right) - 1) * 2.54 / 2 - i * 2.54
        out.append(f'        (pin passive line (at {half_w + pin_len:.2f} {y:.2f} 180) (length {pin_len}) '
                   f'(name "{pn}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
    out.append('      ))')
    return '\n'.join(out)


LIBTABLE = {
    'STM32F103C8Tx': ('MCU_ST_STM32F1', 'STM32F103C8Tx'),
    'MPU-6050':      ('Sensor_Motion', 'MPU-6050'),
    'AMS1117-3.3':   ('Regulator_Linear', 'AMS1117-3.3'),
    'TJA1051T':      ('Interface_CAN_LIN', 'Interface_CAN_LIN'),
    'CH340C':        ('Interface_USB', 'CH340C'),
    'R':             ('Device', 'Device'),
    'C':             ('Device', 'Device'),
    'GND':           ('power', 'power'),
    '+3V3':          ('power', 'power'),
    '+5V':           ('power', 'power'),
    'VBUS':          ('power', 'power'),
}


class Lib:
    def __init__(self):
        self.c = {}

    def root(self, libname):
        if libname not in self.c:
            p = os.path.join(SYMDIR, libname + '.kicad_sym')
            self.c[libname] = sexp.load(p) if os.path.exists(p) else None
        return self.c[libname]

    def sym(self, symname):
        if symname not in LIBTABLE:
            return None, None
        libname = LIBTABLE[symname][0]
        r = self.root(libname)
        if r is None:
            return None, None
        return sexp.find_symbol(r, symname), r

    def pins(self, symname):
        """[(编号, 名称, x, y), ...] 已展平继承"""
        sym, r = self.sym(symname)
        if sym is None:
            return []
        return sexp.symbol_pins(sym, r)

    def embed(self, symname):
        """返回可嵌入 lib_symbols 的展平符号文本"""
        sym, r = self.sym(symname)
        if sym is None:
            return None
        libname = LIBTABLE[symname][0]
        node = copy.deepcopy(sym)
        node[1] = '"%s:%s"' % (libname, symname)
        # 去掉 extends, 展平父符号的图形/引脚
        parent = sexp.extends_of(node)
        node = [e for e in node if not (isinstance(e, list) and e and e[0] == 'extends')]
        if parent:
            psym = sexp.find_symbol(r, parent)
            if psym is not None:
                for sub in psym:
                    if isinstance(sub, list) and sub and sub[0] == 'symbol':
                        s2 = copy.deepcopy(sub)
                        old = s2[1].strip('"')
                        s2[1] = '"%s"' % old.replace(parent, symname)
                        node.append(s2)
        return sexp.dump(node)


# ================= 原理图写出 =================
def uid():
    return str(_uuid.uuid4())


def place_symbol(designator, value, lib_id, x, y, pins, embedded_custom=None):
    """生成一个符号实例的 S 表达式"""
    s = []
    s.append(f'  (symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0) (unit 1)')
    s.append(f'    (in_bom yes) (on_board yes)')
    s.append(f'    (uuid {uid()})')
    s.append(f'    (property "Reference" "{designator}" (id 0) (at {x:.2f} {y - 2:.2f} 0) '
             f'(effects (font (size 1.27 1.27))))')
    s.append(f'    (property "Value" "{value}" (id 1) (at {x:.2f} {y + 2:.2f} 0) '
             f'(effects (font (size 1.27 1.27))))')
    s.append(f'    (property "Footprint" "" (id 2) (at {x:.2f} {y:.2f} 0) '
             f'(effects (font (size 1.27 1.27)) hide))')
    s.append(f'    (property "Datasheet" "" (id 3) (at {x:.2f} {y:.2f} 0) '
             f'(effects (font (size 1.27 1.27)) hide))')
    for num in pins:
        s.append(f'    (pin "{num}" (uuid {uid()}))')
    s.append('  )')
    return '\n'.join(s)


def place_label(net, x, y):
    return (f'  (label "{net}" (at {x:.2f} {y:.2f} 0)\n'
            f'    (effects (font (size 1.0 1.0)) (justify left bottom))\n'
            f'    (uuid {uid()}))')


def write_sch(path, title, lib_blocks, symbols, labels):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('(kicad_sch (version 20210126) (generator eeschema)\n\n')
        f.write('  (paper "A3")\n\n')
        f.write('  (title_block\n')
        f.write(f'    (title "{title}")\n')
        f.write('    (date "2026-01-01")\n')
        f.write('    (rev "1.0")\n')
        f.write('  )\n\n')
        f.write('  (lib_symbols\n')
        for b in lib_blocks:
            f.write(b + '\n')
        f.write('  )\n\n')
        for s in symbols:
            f.write(s + '\n\n')
        for l in labels:
            f.write(l + '\n')
        f.write('\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n')
        f.write(')\n')


if __name__ == '__main__':
    lib = Lib()
    # --- 小规模验证: 电源部分 ---
    # (designator, value, symbol, x, y)
    COMPS = [
        ('U8', 'AMS1117-3.3', 'AMS1117-3.3', 100, 100),
        ('C3', '22uF', 'C', 130, 100),
        ('C4', '0.1uF', 'C', 150, 100),
    ]
    # 网络: net -> [(designator, 引脚名)]
    NETS = {
        '+5V':  [('U8', 'VI'), ('C3', '1'), ('C4', '1')],
        '+3V3': [('U8', 'VO')],
        'GND':  [('U8', 'GND'), ('C3', '2'), ('C4', '2')],
    }

    lib_blocks = []
    seen_lib = set()
    symbols = []
    labels = []
    pinmap = {}   # designator -> {引脚名: 编号}

    for des, val, symname, x, y in COMPS:
        pins = lib.pins(symname)
        if not pins:
            print(f"[警告] {symname} 无引脚"); continue
        lib_id = '%s:%s' % (LIBTABLE[symname][0], symname)
        if lib_id not in seen_lib:
            e = lib.embed(symname)
            if e:
                lib_blocks.append(e)
                seen_lib.add(lib_id)
        pinmap[des] = {p[1]: p[0] for p in pins}
        symbols.append(place_symbol(des, val, lib_id, x, y, [p[0] for p in pins]))
        for p in pins:
            # 引脚绝对坐标 (Y 取负)
            px = x + p[2]
            py = y - p[3]
            labels.append((des, p[0], p[1], px, py))

    # 按网络生成标签 (匹配规则: 引脚名 或 引脚编号)
    label_txt = []
    missing = []
    for net, conns in NETS.items():
        for des, pname in conns:
            hit = False
            for (d, pnum, pn, px, py) in labels:
                if d == des and (pn == pname or pnum == pname):
                    label_txt.append(place_label(net, px, py))
                    hit = True
            if not hit:
                missing.append(f"{des}.{pname} ({net})")
    if missing:
        print("[警告] 未匹配的引脚:", missing)

    write_sch('/tmp/test_driver.kicad_sch', 'TEST', lib_blocks, symbols, label_txt)
    print(f"生成 /tmp/test_driver.kicad_sch: {len(symbols)} 元件, {len(label_txt)} 标签")
