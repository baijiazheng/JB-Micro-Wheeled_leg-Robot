#!/usr/bin/env python3
"""
立创EDA 原生原理图生成器

为什么不用 KiCad 格式: 立创EDA 导入 KiCad 时封装/符号会丢失 (实测)。
改用**立创EDA 原生 JSON 格式**, 元件定义直接复用参考项目的原生 LIB
(封装天然正确), 从根本上避免兼容问题。

EasyEDA 原理图结构:
  {editorVersion, docType, title, schematics:[{docType,title,dataStr:{
     head, canvas, shape:[...], BBox, colors}}]}

shape 元素类型:
  LIB~...   元件 (含符号图形与引脚, 封装写在 package`XXX` 里)
  W~...     导线
  N~...     网络标签
"""

import json, os, re, uuid as _uuid

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = json.load(open(os.path.join(HERE, 'templates.json')))

def uid():
    return 'gge' + _uuid.uuid4().hex[:12]

def fmt(v):
    v = float(v)
    return f'{v:.4f}'.rstrip('0').rstrip('.') if v != int(v) else str(int(v))

# ---------- 引脚生成 (从参考模板反推的格式) ----------
def gen_pin(x, y, rot, num, pid, length=10):
    x, y = float(x), float(y)
    if rot == 180:            # 连接点朝右, 引脚线向左伸
        line = f'M {fmt(x+length)} {fmt(y)} h -{length}'
        t1 = (x+length+4, y, 'start')
        t2 = (x+length-4, y-4, 'end')
        ax, ay = x-length-3, y
        arrow = (f'M {fmt(x-length)} {fmt(y+3)} L {fmt(x-length+3)} {fmt(y)} '
                 f'L {fmt(x-length)} {fmt(y-3)}')
    else:                     # rot 0: 连接点朝左, 引脚线向右伸
        line = f'M {fmt(x-length)} {fmt(y)} h {length}'
        t1 = (x-length-4, y, 'end')
        t2 = (x-length+4, y-4, 'start')
        ax, ay = x+length+3, y
        arrow = (f'M {fmt(x+length)} {fmt(y-3)} L {fmt(x+length-3)} {fmt(y)} '
                 f'L {fmt(x+length)} {fmt(y+3)}')
    return (f'#@$P~show~0~{num}~{fmt(x)}~{fmt(y)}~{rot}~{pid}~0^^{fmt(x)}~{fmt(y)}^^'
            f'{line}~#800^^0~{fmt(t1[0])}~{fmt(t1[1])}~0~{num}~{t1[2]}~~~#800'
            f'^^0~{fmt(t2[0])}~{fmt(t2[1])}~0~{num}~{t2[2]}~~~#800'
            f'^^0~{fmt(ax)}~{fmt(ay)}^^0~{arrow}')

# ---------- 子元素坐标平移 ----------
def shift_sub(s, dx, dy):
    """平移一个子元素的坐标"""
    if s.startswith('#@$T'):           # 文本: T~orient~x~y~rot~...
        f = s.split('~')
        if len(f) > 3:
            try:
                f[2] = fmt(float(f[2]) + dx); f[3] = fmt(float(f[3]) + dy)
            except ValueError:
                pass
        return '~'.join(f)
    if s.startswith('#@$R'):           # 矩形: R~x~y~..~w~h~..
        f = s.split('~')
        try:
            f[1] = fmt(float(f[1]) + dx); f[2] = fmt(float(f[2]) + dy)
        except (ValueError, IndexError):
            pass
        return '~'.join(f)
    if s.startswith('#@$PL'):          # 折线: PL~points~..
        f = s.split('~')
        if len(f) > 1:
            pts = []
            for tok in f[1].split(' '):
                if tok in ('M', 'L'):
                    pts.append(tok); continue
                pts.append(tok)   # 坐标成对处理
            # 坐标是 "x y x y ..." 形式
            out = []
            nums = [t for t in f[1].split(' ') if t not in ('M', 'L')]
            j = 0
            res = []
            for tok in f[1].split(' '):
                if tok in ('M', 'L'):
                    res.append(tok)
                else:
                    try:
                        v = float(tok)
                        res.append(fmt(v + (dx if j % 2 == 0 else dy)))
                        j += 1
                    except ValueError:
                        res.append(tok)
            f[1] = ' '.join(res)
        return '~'.join(f)
    if s.startswith('#@$P'):           # 引脚: 重新生成
        m = re.match(r'#@\$P~show~(\d+)~(\d+)~([\d.]+)~([\d.]+)~(\d+)~(\S+?)~', s)
        if m:
            num, x, y, rot, pid = m.group(2), float(m.group(3)), float(m.group(4)), int(m.group(5)), m.group(6)
            return gen_pin(x + dx, y + dy, rot, num, pid)
        return s
    return s

def instantiate(template, x, y, des, val):
    """把模板 LIB 实例化到 (x,y), 设置位号和值"""
    parts = template.split('#@$')
    header, subs = parts[0], ['#@$' + p for p in parts[1:]]
    hf = header.split('~')
    ox, oy = float(hf[1]), float(hf[2])
    hf[1], hf[2] = fmt(x), fmt(y)
    # 置新的 uuid
    for i in (6, 7, 8):
        if len(hf) > i:
            hf[i] = uid()
    header = '~'.join(hf)

    dx, dy = x - ox, y - oy
    out = []
    for s in subs:
        s = shift_sub(s, dx, dy)
        # 替换位号 (T~P~...comment~DES~) 和值 (T~N~...comment~VAL~)
        s = re.sub(r'(#@\$T~P~[^~]*~[^~]*~[^~]*~[^~]*~[^~]*~~~~~comment~)[^~]*(~)',
                   lambda m: m.group(1) + des + m.group(2), s)
        s = re.sub(r'(#@\$T~N~[^~]*~[^~]*~[^~]*~[^~]*~[^~]*~~~~~comment~)[^~]*(~)',
                   lambda m: m.group(1) + val + m.group(2), s)
        out.append(s)
    return header + ''.join(out)

# ---------- 导线 / 网络标签 ----------
def gen_wire(x1, y1, x2, y2, color='#008800'):
    return f'W~{fmt(x1)} {fmt(y1)} {fmt(x2)} {fmt(y2)}~{color}~1~0~none~{uid()}~0'

def gen_netlabel(x, y, name, rot=0):
    return (f'N~{fmt(x)}~{fmt(y)}~{rot}~#0000ff~{name}~{uid()}~end~'
            f'{fmt(x-2)}~{fmt(y+2)}~Times New Roman~7pt~0')

# ---------- 自定义元件 (STM32 / MPU6050, 参考项目没有) ----------
def gen_custom_lib(x, y, des, val, pkg, left_pins, right_pins, body_w=60):
    """
    生成一个矩形元件。
    left_pins/right_pins: [(pin_number, pin_name), ...]
    """
    n = max(len(left_pins), len(right_pins))
    h = max(n * 10 + 20, 40)
    hw = body_w / 2
    hh = h / 2
    subs = []
    # 位号
    subs.append(f'#@$T~P~{fmt(x-10)}~{fmt(y-hh-10)}~0~#000080~Arial~~~~~comment~{des}~1~start~{uid()}~0~')
    # 值
    subs.append(f'#@$T~N~{fmt(x-10)}~{fmt(y+hh+10)}~0~#000080~Arial~~~~~comment~{val}~1~start~{uid()}~0~')
    # 外框
    subs.append(f'#@$R~{fmt(x-hw)}~{fmt(y-hh)}~~~{fmt(body_w)}~{fmt(h)}~#880000~1~0~none~{uid()}~0~')
    # 左引脚
    for i, (num, nm) in enumerate(left_pins):
        py = y - hh + 10 + i * 10
        subs.append(gen_pin(x - hw, py, 0, num, uid()))
        subs.append(f'#@$T~L~{fmt(x-hw+4)}~{fmt(py)}~0~#000000~Arial~7pt~~~comment~{nm}~1~start~{uid()}~0~')
    # 右引脚
    for i, (num, nm) in enumerate(right_pins):
        py = y - hh + 10 + i * 10
        subs.append(gen_pin(x + hw, py, 180, num, uid()))
        subs.append(f'#@$T~L~{fmt(x+hw-4)}~{fmt(py)}~0~#000000~Arial~7pt~~~comment~{nm}~1~end~{uid()}~0~')
    settings = (f'`package`{pkg}`nameAlias`Value``BOM_Supplier Part``BOM_Supplier``'
                f'Contributor`LCEDA_Lib`spicePre`U`spiceSymbolName`{val}``~~')
    header = f'LIB~{fmt(x)}~{fmt(y)}~{settings}0~{uid()}~{uid()}~{uid()}~0~~yes~yes~~0~'
    return header + ''.join(subs)

# ---------- 文档封装 ----------
def make_doc(title, shapes):
    xs, ys = [], []
    for s in shapes:
        if s.startswith('LIB~'):
            f = s.split('~'); xs.append(float(f[1])); ys.append(float(f[2]))
    bbox = {'x': int(min(xs) - 50) if xs else 0,
            'y': int(min(ys) - 50) if ys else 0,
            'width': int(max(xs) - min(xs) + 200) if xs else 1000,
            'height': int(max(ys) - min(ys) + 200) if ys else 1000}
    return {
        'editorVersion': '6.5.34', 'docType': '5', 'title': title,
        'description': '', 'colors': {},
        'schematics': [{
            'docType': '1', 'title': 'v1.0', 'description': '',
            'dataStr': {
                'head': {'docType': '1', 'editorVersion': '6.5.34', 'newgId': True,
                         'c_para': {'Prefix Start': '1'}, 'c_spiceCmd': 'null',
                         'hasIdFlag': True, 'uuid': _uuid.uuid4().hex,
                         'x': '0', 'y': '0', 'portOfADImportHack': '',
                         'importFlag': 0, 'transformList': ''},
                'canvas': 'CA~1000~1000~#FFFFFF~yes~#CCCCCC~5~1000~1000~line~5~pixel~5~0~0',
                'shape': shapes,
                'BBox': bbox,
                'colors': {},
            }
        }]
    }

if __name__ == '__main__':
    # 自检: 测试实例化一个模板
    t = TPL['R0805|2']
    print('模板:', t[:80], '...')
    r = instantiate(t, 200, 200, 'R1', '10k')
    print('实例化后:', r[:80], '...')
    print('引脚数:', r.count('#@$P~'))
    print('包含 R1:', 'R1' in r, '| 包含 10k:', '10k' in r)
