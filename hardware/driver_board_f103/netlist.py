#!/usr/bin/env python3
"""
驱动板 F103 网表校验 (薄封装)

网表的"逻辑真相"只存在于一处: hardware/kicad_gen/gen_driver.py 的 GROUPS / NETS。
本文件不再重复定义网表, 只转调总校验程序。

为什么要这样改:
    之前本文件手抄了一份 CONNECTORS 表, 把电机连接器写成 "2P", 而实际网表连了
    3 个引脚 —— 同一份信息两处维护必然漂移, 而且给出的是**假信息**。
    现在改为"单一来源 + 自动校验"。

用法:
    python3 netlist.py             # 校验全部 4 块板
    python3 ../check_netlists.py   # 等价
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, '..', 'check_netlists.py')

print('驱动板网表定义见 hardware/kicad_gen/gen_driver.py (单一来源)')
print('本文件已改为转调 hardware/check_netlists.py\n')

sys.exit(subprocess.call([sys.executable, CHECKER]))
