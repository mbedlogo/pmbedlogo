
import numbers, ts

def test(x):
    global result
    result = []
    pass3(x)
    return result

def run_line(line):
    ts.init(line)
    print compile_line(ts.readList())

def compile_line(code):
    global state
    state = record()
    state.name = '*toplevel*'
    state.toplevel = False
    state.command = True
    state.body = []

    global result, pc
    result = []
    pc = 0
    
    pass2_body(code)
    return pass3(result[:]) + [0]

def pass2_body(code):
    oldbody, state.body = state.body, code

    oldcommand, state.command = state.command, True
    while ([] != state.body):
        pass2_item(state.body.pop(0))

    state.command = oldcommand
    state.body = oldbody

def pass2_item(item):
    if isinstance(item, list): pass2_list(item)
    elif isinstance(item, int): pass2_number(item)
    elif isinstance(item, float): pass2_item(floatbits(item))
    elif isinstance(item, str): pass2_string(item)
    elif isinstance(item, ts.dsym): pass2_dsym(item)
    elif isinstance(item, ts.qsym): pass2_string(item.sym.pname)
    else: pass2_symbol(item)

def pass2_number(n):
    if -1 < n and n < 256:
        add_and_count(['byte', n], 2)
    else:
        add_and_count(['number', n], 5)

def pass2_string(s):
    s = s.replace('\\n', '\n')
    add_and_count(['string', s], len(s))

def pass2_list(item):
    if item != []:
        # deal with ## and #
        return
    
    oldcommand, state.command = state.command, True
    add_and_count(['-[-', 0], 3)
    pass2_body(item)
    add_and_count(['-]-', 0], 1)
    state.command = oldcommand

def pass2_dsym(item):
    offset = dsym_offset(item)
    add_and_count(['lthing', offset], 2)

def dsym_offset(item):
    if item in arglist: return len(arglist) - arglist.index[item] - 1
    return 0xff & 0 - locals.index[item] - 1

def pass2_symbol(item):
    nargs = item.args
    if nargs < 0: raise ValueError('not enough inputs to ' + item)
    if state.command:
        if item.outputs: raise ValueError("you don't say what to do with " + item)
    else:
        if not item.outputs: raise ValueError(item + " doesn't output")
    
    pass2_argloop(nargs)
    pass2_funcall(item)

def pass2_argloop(nargs):
    oldtoplevel, state.toplevel = state.toplevel, False
    oldcommand, state.command = state.command, False

    while 0 < nargs:
        if len(state.body) == 0: raise ValueError('not enough inputs to ' + item)
        pass2_item(state.body.pop(0))
        nargs -= 1
    
    state.toplevel = oldtoplevel
    state.command = oldcommand

def pass2_funcall(item):
    # handle ufun
    if item.type == 'external': add_and_count(['external', item], 2)
    elif item.special: handle_special(item)
    else: add_and_count(['prim', item], 1)


def pass3(body):
    global result, lists
    result = []
    lists = []

    while ([] != body):
        pass3_item(body.pop(0))

    return result

def pass3_item(item):
    x = item[2]
    selectq(item[1],
    [
        ('to', lambda: add(x.args, x.locals)),
        ('byte', lambda: add(1, byte(0, x))),
        ('number', lambda: add(2, byte(0, x), byte(1, x), byte(2, x), byte(3, x))),
        ('string', lambda: pass3_string(x)),
        ('prim', lambda: add(prim(x))),
        ('external', lambda: add_ext(x)),
    ])

def pass3_string(s):
    add(3, byte(0, 1 + len(s)), byte(1, 1 + len(s)))
    map(add, [ord(c) for c in s])
    add(0)

def byte(shift, x):
    shift *= 8
    return (x & (0xff << shift)) >> shift

def selectq(x, fcns):
    for each in fcns:
        token, fcn = each
        if token == x: return fcn()

def add_and_count(item, len):
    global pc
    add([pc] + item)
    pc += len
    
def add(*args):
    map(lambda x: result.append(x), args)

def setup_prims(primtype, dest, *newprims):
    for x in newprims:
        name, outputs, args = x
        sym = ts.intern(name)
        sym.args = args
        sym.outputs = outputs
        if sym.args < 0: infixes.append(sym)
        sym.type = primtype
        sym.special = False
        dest.append(sym)

def setup_specials(*newprims):
    for x in newprims:
        sym = ts.intern(x)
        sym.type = 'prim'
        sym.special = True

def prim(x):
    return prims.index(x) + 12

def add_ext(x):
    if x.outputs:
        add(11)
    else:
        add(10)
    
    add(externals.index(x))

prims = []
setup_prims('prim', prims,
    ('not', True, 1)
)

externals = []
setup_prims('external', externals,
    ('print', False, 1)
)

infixes = []

setup_specials('(', ')', 'waituntil', 'make', 'let')

class record: pass

class dsym: pass

class symbol:
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return '<symbol: ' + self.name + '>'

    def __str__(self):
        return self.name
