#!/usr/bin/env python3
"""
KiCad S 表达式解析工具

用于从 .kicad_sym 库中提取符号定义块和引脚坐标, 以便生成原理图。
"""

def tokenize(s):
    """把 S 表达式切成 token, 保留括号和字符串"""
    toks = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in '()':
            toks.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if s[j] == '\\' and j + 1 < n:
                    buf.append(s[j:j+2]); j += 2; continue
                if s[j] == '"':
                    break
                buf.append(s[j]); j += 1
            toks.append('"' + ''.join(buf) + '"')
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and (not s[j].isspace()) and s[j] not in '()"':
                j += 1
            toks.append(s[i:j])
            i = j
    return toks


def parse(toks):
    """token -> 嵌套列表"""
    it = iter(toks)
    def helper():
        out = []
        for t in it:
            if t == '(':
                out.append(helper())
            elif t == ')':
                return out
            else:
                out.append(t)
        return out
    first = next(it)
    assert first == '('
    return helper()


def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return parse(tokenize(f.read()))


def dump(node, indent=0):
    """把嵌套列表还原成 S 表达式文本"""
    if not isinstance(node, list):
        return str(node)
    parts = []
    for x in node:
        parts.append(dump(x, indent + 1))
    return '(' + ' '.join(parts) + ')'


def find_all(node, tag):
    """递归找所有子节点中第一个元素 == tag 的"""
    out = []
    if isinstance(node, list):
        if node and node[0] == tag:
            out.append(node)
        for x in node:
            out.extend(find_all(x, tag))
    return out


def find_symbol(lib_root, name):
    """在库根节点下找名为 name 的 symbol"""
    for sym in find_all(lib_root, 'symbol'):
        if len(sym) > 1 and sym[1] == '"%s"' % name:
            return sym
    return None


def extends_of(sym):
    """若符号有 extends, 返回父符号名"""
    for e in sym:
        if isinstance(e, list) and e and e[0] == 'extends' and len(e) > 1:
            return e[1].strip('"')
    return None


def symbol_pins(sym, lib_root=None, _seen=None):
    """
    提取符号的引脚 (编号, 名称, x, y)。自动去重 + 解析 extends 继承。
    注意: 库符号内 Y 轴向上, 原理图 Y 轴向下, 调用方需取负。
    """
    if _seen is None:
        _seen = set()

    # extends 继承: 用父符号的引脚
    parent = extends_of(sym)
    if parent and lib_root is not None and parent not in _seen:
        _seen.add(parent)
        psym = find_symbol(lib_root, parent)
        if psym is not None:
            return symbol_pins(psym, lib_root, _seen)

    pins = {}
    for sub in find_all(sym, 'symbol'):
        for pin in find_all(sub, 'pin'):
            num = pname = None
            at = None
            ang = 0.0
            for e in pin:
                if isinstance(e, list):
                    if e[0] == 'number' and len(e) > 1:
                        num = e[1].strip('"')
                    elif e[0] == 'name' and len(e) > 1:
                        pname = e[1].strip('"')
                    elif e[0] == 'at' and len(e) > 2:
                        at = (float(e[1]), float(e[2]))
                        if len(e) > 3:
                            ang = float(e[3])
            if num is not None and at is not None and num not in pins:
                pins[num] = (num, pname, at[0], at[1], ang)
    return list(pins.values())


if __name__ == '__main__':
    import sys
    root = load(sys.argv[1])
    name = sys.argv[2]
    sym = find_symbol(root, name)
    if sym is None:
        print("not found")
        sys.exit(1)
    pins = symbol_pins(sym, root)
    print(f"符号 {name}: {len(pins)} 个引脚")
    for p in pins[:60]:
        print(f"  pin {p[0]:>4}  {str(p[1]):<18} at ({p[2]}, {p[3]})")
