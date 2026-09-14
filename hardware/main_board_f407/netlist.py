#!/usr/bin/env python3
"""
主控板 F407 网表校验 (薄封装)

网表的"逻辑真相"只存在于一处: hardware/kicad_gen/gen_main.py 的 g.GROUPS / g.NETS。
本文件不再重复定义网表, 只转调总校验程序。

用法:
    python3 netlist.py             # 校验全部 4 块板 + 板间连接器
    python3 ../check_netlists.py   # 等价
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, '..', 'check_netlists.py')

print('主控板网表定义见 hardware/kicad_gen/gen_main.py (单一来源)')
print('本文件已改为转调 hardware/check_netlists.py\n')

sys.exit(subprocess.call([sys.executable, CHECKER]))
