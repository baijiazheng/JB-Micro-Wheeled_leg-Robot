#!/usr/bin/env python3
"""
网表总校验 —— 4 块板 + 板间连接器交叉核对

设计原则: 网表的"逻辑真相"只存在于 kicad_gen/gen_driver.py 与 gen_main.py
两处, 本文件不再重复定义任何网表, 只做校验。

(之所以不重复定义: 之前 netlist.py 里手抄了一份连接器表, 写着 "2P" 而实际
 连了 3 个引脚, 给出假信息。单一来源 + 自动校验才能杜绝这类漂移。)

用法:
  python3 check_netlists.py
退出码 0 = 全部通过, 1 = 有错误
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'kicad_gen'))

import gen_driver as gd
# 快照驱动板数据 —— gen_main 在 import 时会复用 gen_driver 作引擎并覆盖 gd.NETS/gd.GROUPS
DRIVER = {
    'name': '驱动板 F103',
    'comps': [c for grp in gd.GROUPS for c in grp],
    'nets': {k: list(v) for k, v in gd.NETS.items()},
}

import gen_main as gm
MAIN = {
    'name': '主控板 F407',
    'comps': [c for grp in gm.g.GROUPS for c in grp],
    'nets': {k: list(v) for k, v in gm.g.NETS.items()},
}

# 卫星板 (定义在 easyeda_gen/gen_boards.py 的 __main__ 里, 这里单独登记以便一起校验)
SATELLITE = [
    ('编码器板 (AS5600) x2',
     ['U1', 'J2', 'R1', 'R2', 'C1', 'C2'],
     {
         '+3V3': [('U1', 'VDD5V'), ('U1', 'VDD3V3'), ('C1', '1'), ('C2', '1'),
                  ('R1', '2'), ('R2', '2'), ('J2', '1')],
         'SCL':  [('U1', 'SCL'), ('R1', '1'), ('J2', '2')],
         'SDA':  [('U1', 'SDA'), ('R2', '1'), ('J2', '3')],
         'GND':  [('U1', 'GND'), ('U1', 'DIR'), ('U1', 'PGO'),
                  ('C1', '2'), ('C2', '2'), ('J2', '4')],
     }),
    ('IMU 板 (MPU6050) x1',
     ['U1', 'J1', 'J2', 'C1', 'C2', 'C3'],
     {
         '+3V3': [('U1', 'VDD'), ('U1', 'VLOGIC'), ('C1', '1'), ('J1', '1'), ('J2', '1')],
         'SCL':  [('U1', 'SCL'), ('J1', '2'), ('J2', '2')],
         'SDA':  [('U1', 'SDA'), ('J1', '3'), ('J2', '3')],
         'GND':  [('U1', 'GND'), ('U1', 'AD0'), ('U1', 'FSYNC'), ('U1', 'CLKIN'),
                  ('U1', '19'), ('U1', '21'), ('U1', '22'),
                  ('C1', '2'), ('C2', '2'), ('C3', '2'), ('J1', '4'), ('J2', '4')],
         'CPOUT':  [('U1', 'CPOUT'), ('C2', '1')],
         'REGOUT': [('U1', 'REGOUT'), ('C3', '1')],
     }),
]

# 每块板必须存在的网络
REQUIRED = {
    '驱动板 F103':            ['BAT_RAW', 'SW_OUT', 'VIN', '+5V', '+3V3', 'GND',
                               'CAN_H', 'CAN_L'],
    '主控板 F407':            ['BAT_RAW', 'SW_OUT', 'VIN', '+5V', '+3V3', 'GND',
                               'CAN_H', 'CAN_L', 'SERVO_DATA'],
    '编码器板 (AS5600) x2':   ['+3V3', 'SCL', 'SDA', 'GND'],
    'IMU 板 (MPU6050) x1':    ['+3V3', 'SCL', 'SDA', 'GND', 'CPOUT', 'REGOUT'],
}

# GH1.25 4P 统一线序 (所有卫星板必须一致, 否则插错烧片)
GH4_PINOUT = {'1': '+3V3', '2': 'SCL', '3': 'SDA', '4': 'GND'}


def check_board(name, comps, nets):
    errs = []
    # 1. 引脚是否被重复连到两个网络
    seen = {}
    for net, conns in nets.items():
        for des, pin in conns:
            key = (des, str(pin))
            if key in seen:
                errs.append(f'引脚 {des}.{pin} 同时连到 {seen[key]} 和 {net}')
            seen[key] = net
    # 2. 关键网络
    for req in REQUIRED.get(name, []):
        if req not in nets:
            errs.append(f'缺少关键网络: {req}')
    # 3. 悬空网络 (只有 1 个连接 = 没接上)
    for net, conns in nets.items():
        if len(conns) < 2:
            errs.append(f'悬空网络 {net}: 只有 {conns}')
    # 4. 网表引用的位号是否都在元件表里
    des_set = {c[0] for c in comps}
    for net, conns in nets.items():
        for des, pin in conns:
            if des not in des_set:
                errs.append(f'网络 {net} 引用了不存在的元件 {des}')
    return errs, seen


def check_power_chain(nets, label):
    """BAT_RAW -> SW1 -> SW_OUT -> D1 -> VIN 必须首尾相接"""
    errs = []
    chain = [('BAT_RAW', 'J1', '1'), ('BAT_RAW', 'SW1', '1'),
             ('SW_OUT', 'SW1', '2'), ('SW_OUT', 'D1', 'A'),
             ('VIN', 'D1', 'K')]
    for net, des, pin in chain:
        if (des, pin) not in [(d, str(p)) for d, p in nets.get(net, [])]:
            errs.append(f'{label}: {des}.{pin} 不在 {net} 上 (开关/防反接断链)')
    # 开关不能被旁路: J1 不能直接出现在 VIN 上
    if any(d == 'J1' for d, _ in nets.get('VIN', [])):
        errs.append(f'{label}: J1 直接挂在 VIN 上 -> 总开关被旁路, 开关失效')
    return errs


def cross_check(driver_nets, main_nets, dref='J8', mref='J3'):
    """板间堆叠连接器必须逐脚一致"""
    errs = []
    def jmap(nets, ref):
        return {str(p): net for net, conns in nets.items()
                for d, p in conns if d == ref}
    a, b = jmap(driver_nets, dref), jmap(main_nets, mref)
    if not a:
        errs.append(f'驱动板找不到板间连接器 {dref}')
    if not b:
        errs.append(f'主控板找不到板间连接器 {mref}')
    for p in sorted(set(a) | set(b), key=lambda x: int(x) if x.isdigit() else 0):
        if a.get(p) != b.get(p):
            errs.append(f'板间 pin{p} 不一致: 驱动板={a.get(p, "--")} 主控板={b.get(p, "--")}')
    return errs, a, b


def main():
    all_errs = []
    print('=' * 62)
    print('  网表总校验  (4 块板 + 板间连接器)')
    print('=' * 62)

    boards = [(DRIVER['name'], DRIVER['comps'], DRIVER['nets']),
              (MAIN['name'], MAIN['comps'], MAIN['nets'])]
    for nm, comps, nets in SATELLITE:
        boards.append((nm, [(d, '', '') for d in comps], nets))

    for nm, comps, nets in boards:
        errs, seen = check_board(nm, comps, nets)
        n_conn = sum(len(v) for v in nets.values())
        status = 'OK' if not errs else f'FAIL ({len(errs)})'
        print(f'\n[{status}] {nm}')
        print(f'        元件 {len(comps)} | 网络 {len(nets)} | 连线 {n_conn}')
        for e in errs:
            print(f'        - {e}')
        all_errs += [f'{nm}: {e}' for e in errs]

    print('\n' + '-' * 62)
    print('电源链 & 开关有效性')
    for nm, comps, nets in boards[:2]:
        errs = check_power_chain(nets, nm)
        if errs:
            all_errs += errs
            for e in errs:
                print(f'  [FAIL] {e}')
        else:
            print(f'  [ OK ] {nm}: J1 -> SW1 -> D1 -> VIN 链路完整, 开关未被旁路')

    print('\n' + '-' * 62)
    print('板间堆叠连接器交叉核对')
    errs, a, b = cross_check(DRIVER['nets'], MAIN['nets'])
    for p in sorted(a, key=int):
        mark = 'OK' if a.get(p) == b.get(p) else 'XX'
        print(f'  [{mark}] pin{p}: 驱动板 J8={a.get(p, "--"):7} <-> 主控板 J3={b.get(p, "--")}')
    if errs:
        all_errs += errs
        for e in errs:
            print(f'  [FAIL] {e}')

    print('\n' + '-' * 62)
    print('GH1.25 4P 卫星板线序一致性')
    for nm, comps, nets in boards[2:]:
        rev = {}
        for net, conns in nets.items():
            for des, pin in conns:
                if des in ('J1', 'J2'):
                    rev.setdefault(str(pin), net)
        ok = all(rev.get(p) == n for p, n in GH4_PINOUT.items())
        print(f'  [{"OK" if ok else "XX"}] {nm}: ' +
              ' '.join(f'{p}={rev.get(p, "--")}' for p in sorted(GH4_PINOUT)))
        if not ok:
            all_errs.append(f'{nm}: GH1.25 线序与统一约定不符')

    print('\n' + '=' * 62)
    if all_errs:
        print(f'  [FAIL] 共 {len(all_errs)} 个问题')
        for e in all_errs:
            print(f'    - {e}')
        return 1
    print('  [ OK ] 全部通过 — 4 块板网表自洽, 板间连接一致, 线序统一')
    print('=' * 62)
    return 0


if __name__ == '__main__':
    sys.exit(main())
