
import readline
import ts
import uartcomms
import traceback

class record: pass

class LogoError(ValueError):
    def __init__(self, msg):
        if state.name != '*toplevel*': msg += ' in ' + str(state.name)
        ValueError.__init__(self, msg)

def run_line(line):
    ts.init(line)
    command = compile_line(ts.readList())
    print '  %s' % command

    try:
        check_comms()
        if command != [0]: mbed.run_command(command)
    except:
        print '  no logochip'

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

def compile(file):
    code = compileOnly(file)
    try:
        check_comms()
        mbed.erase_flash(0xf)
        mbed.write_flash(0xf, 0xf000, code)
    except:
        print '  no logochip'

def dump(addr, count = 16):
    count = (count + 15) / 16 * 16
    l = mbed.read_memory(addr, count)
    while [] != l:
        print '%0.8x -' % addr, ' '.join(['%0.2x' % x for x in l[:16]])
        l = l[16:]
        addr += 16

def compileOnly(file):
    setup()
    f = open(file)
    ts.init(f.read())
    f.close()
    result = pass3(pass2(pass1(ts.readList())))
    print ' ', result
    print ' ', len(result), 'bytes'
    return result

def pass1(code):
    global result
    result = []
    while [] != code:
        token = code.pop(0)
        if str(token) == 'to': pass1_fcn(code.pop(0), pass1_args(code), pass1_body(code))
        elif str(token) == 'define': pass1_fcn(code.pop(0), [ts.dsym(x) for x in code.pop(0)], code.pop(0))
        elif str(token) == 'global': setup_globals(code.pop(0))
        elif str(token) == 'constants': setup_constants(code.pop(0))

    return result

def pass1_fcn(name, args, body):
    if 'type' in name.__dict__: raise ValueError(str(name) + " already defined")
    add((name, args, body))
    name.args = len(args)
    name.argnames = args
    name.type = 'ufun'
    name.outputs = mmmember(ts.intern('output'), body)

def mmmember(item, body):
    if isinstance(body, list): return [] != filter(lambda(x): mmmember(item, x), body)
    return item == body

def mmstr(item):
    if isinstance(item, list): return '[' + ' '.join(map(mmstr, item)) + ']'
    return str(item)

def pass1_args(code):
    result = []
    while [] != code:
        if not isinstance(code[0], ts.dsym): break
        result.append(code.pop(0));

    return result

def pass1_body(code):
    result = []
    while [] != code:
        token = code.pop(0)
        if isinstance(token, ts.symbol) and str(token) == 'end': break
        result.append(token)

    return result

def setup_globals(names):
    if not isinstance(names, list): names = [names]

    global next_global
    for x in names:
        ts.init('( gread ' + str(next_global) + ')');
        getter = ts.intern(str(x))
        getter.macro = ts.readList()
        setter = ts.intern('set' + str(x))
        ts.init('gwrite ' + str(next_global))
        setter.macro = ts.readList()
        next_global += 1

def setup_constants(defs):
    try:
        for x in defs:
            x[0].macro = const_eval(x[1:])
    except:
        raise ValueError('bad constants ' + mmstr(defs))

def const_eval(code):
    if len(code) == 1 and isinstance(code[0], list): code = code[0]
    val = eval(' '.join(map(const_eval_one, code)))
    if isinstance(val, int) or isinstance(val, float): return val
    raise ValueError('bad constant ' + mmstr(code))

def const_eval_one(item):
    if isinstance(item, ts.symbol) and 'macro' in item.__dict__:
        item = item.macro
    return str(item)

def pass2(code):
    global result, pc
    result = []
    pc = 0x1000
    while [] != code:
        pass2_fcn(code.pop(0))

    return result

def pass2_fcn(fcn):
    global state
    state = record()
    state.toplevel = True
    state.command = True
    state.body = []
    state.locals = []

    state.name, state.arglist, body = fcn

    state.name.addr = pc
    state.name.locals = 0
    add_and_count(['to', state.name], 2)
    pass2_body(body[:])
    add_and_count(['prim', ts.intern('stop')], 1)
    state.name.endaddr = pc

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
    elif isinstance(item, ts.qsym): pass2_string(item)
    else: pass2_symbol(item)

def floatbits(item):
    raise LogoError(str(item) + " isn't supported")

def pass2_number(n):
    command_check(n)
    if -1 < n and n < 256:
        add_and_count(['byte', n], 2)
    else:
        add_and_count(['number', n], 5)

def pass2_string(item):
    command_check(item)
    s = str(item).replace('\\n', '\n')
    add_and_count(['string', s], len(s))

def pass2_list(item):
    command_check(item)
    # TODO: deal with ## and #

    oldcommand, state.command = state.command, True
    add_and_count(['-[-', 0], 3)
    pass2_body(item)
    add_and_count(['-]-', 0], 1)
    state.command = oldcommand

def pass2_dsym(item):
    command_check(item)
    offset = dsym_offset(item)
    add_and_count(['lthing', offset], 2)

def dsym_offset(item):
    try:
        if item in state.arglist: return len(state.arglist) - state.arglist.index(item) - 1
        return 0xff & 0 - state.locals.index(item) - 1
    except:
        raise LogoError(str(item) + " isn't a local")

def handle_opening():
    pass2_argloop(1, ')')
    if [] == state.body or state.body.pop(0) != ts.intern(')'): raise LogoError('() error')

def handle_closing():
    raise LogoError('misplaced )')

def handle_waituntil():
    add_and_count(['-[-', 0], 3)
    newbody = state.body.pop(0)
    oldbody, state.body = state.body, newbody
    pass2_argloop(1, 'waituntil')
    add_and_count(['-]-r', 0], 1)
    add_and_count(['prim', ts.intern('waituntil')], 1)
    state.body = oldbody

def handle_make():
    var = sym(state.body.pop(0))
    offset = dsym_offset(var)
    pass2_argloop(1, 'make')
    add_and_count(['lmake', offset], 2)

def handle_let():
    if state.name == '*toplevel*': raise ValueError('let can only be used in a procedure')
    newbody = state.body.pop(0)
    oldbody, state.body = state.body, newbody
    if not isinstance(state.body, list): raise LogoError('let needs a list as input')
    while [] != state.body:
        state.locals.append(sym(state.body[0]))
        state.name.locals += 1
        handle_make()

    state.body = oldbody

def sym(x):
    if not isinstance(x, ts.symbol) and not isinstance(x, ts.qsym):
        raise LogoError(mmstr(x) + " isn't a valid local")
    return ts.dsym(ts.intern(str(x)))

def pass2_symbol(item):
    if not 'args' in item.__dict__:
        try_macro(item)
        return

    nargs = item.args
    if nargs < 0: raise LogoError('not enough inputs to ' + item)
    if state.command:
        if item.outputs: raise LogoError("you don't say what to do with " + str(item))
    else:
        if not item.outputs: raise LogoError(str(item) + " doesn't output")

    pass2_argloop(nargs, str(item))
    pass2_funcall(item)

def try_macro(item):
    if not 'macro' in item.__dict__: raise LogoError(str(item) + ' undefined')
    val = item.macro
    if not isinstance(val, list): val = [val]
    state.body = val + state.body
    pass2_item(state.body.pop(0))

def pass2_argloop(nargs, item):
    oldtoplevel, state.toplevel = state.toplevel, False
    oldcommand, state.command = state.command, False

    while 0 < nargs:
        if len(state.body) == 0: raise LogoError('not enough inputs to ' + item)
        pass2_item(state.body.pop(0))
        infix_check()
        nargs -= 1

    state.toplevel = oldtoplevel
    state.command = oldcommand

def pass2_funcall(item):
    if item.type == 'ufun': add_and_count(['ufun', item], 3)
    elif item.type == 'external': add_and_count(['external', item], 2)
    elif item.special: item.handler()
    else: add_and_count(['prim', item], 1)

def command_check(item):
    if state.command: raise LogoError("you don't say what to do with " + mmstr(item))

def infix_check():
    if not is_infix(): return
    fcn = state.body.pop(0)
    pass2_item(state.body.pop(0))
    pass2_funcall(fcn)
    infix_check()

def is_infix():
    return [] != state.body and state.body[0] in infixes

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
        ('-[-', lambda: pass3_start_list()),
        ('string', lambda: pass3_string(x)),
        ('-]-', lambda: add_eol(4)),
        ('-]-r', lambda: add_eol(5)),
        ('lthing', lambda: add(6, x)),
        ('lmake', lambda: add(7, x)),
        ('ufun', lambda: add(8, byte(0, x.addr), byte(1, x.addr))),
        ('prim', lambda: add(prim(x))),
        ('external', lambda: add_ext(x)),
    ])

def pass3_string(s):
    add(3, byte(0, 1 + len(s)), byte(1, 1 + len(s)))
    map(add, [ord(c) for c in s])
    add(0)

def pass3_start_list():
    add(3)
    lists.append(len(result))
    add(0)
    add(0)

def add_eol(indicator):
    add(indicator)
    offset = lists.pop()
    listlen = len(result) - offset - 2
    result[offset] = byte(0, listlen)
    result[offset+1] = byte(1, listlen)

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
        name, outputs, handler = x
        sym = ts.intern(name)
        sym.type = 'prim'
        sym.args = 0
        sym.outputs = outputs
        sym.special = True
        sym.handler = handler

def prim(x):
    return prims.index(x) + 12

def add_ext(x):
    if x.outputs:
        add(11)
    else:
        add(10)

    add(externals.index(x))

def setup():
    ts.oblist.clear()

    global prims, externals, infixes
    infixes = []
    prims = []
    setup_prims('prim', prims,
        ('stop', False, 0), ('output', False, 1),
        ('call', False, 1),
        ('run', False, 1),
        ('runmacro', False, 1),
        ('repeat', False, 2),
        ('loop', False, 1),
        ('if', False, 2),
        ('ifelse', False, 3),
        ('waituntil', False, 1),
        ('gwrite', False, 2),
        ('gread', True, 1),
        ('+', True, -1),
        ('-', True, -1),
        ('*', True, -1),
        ('/', True, -1),
        ('%', True, -1),
        ('random', True, 0),
        ('extend', True, 1),
        ('=', True, -1),
        ('!=', True, -1),
        ('>', True, -1),
        ('<', True, -1),
        ('and', True, -1),
        ('or', True, -1),
        ('xor', True, -1),
        ('not', True, 1),
        ('lsh', True, 2),
        ('g', True, 1), ('fl', True, 1),
        ('readb', True, 1), ('writeb', False, 2),
        ('readh', True, 1), ('writeh', False, 2),
        ('read', True, 1), ('write', False, 2),
        ('sp', True, 0),
    )

    externals = []
    setup_prims('external', externals,
        ('utimer', True, 0), ('resetut', False, 0),
        ('wait', False, 1),  ('mwait', False, 1),  ('uwait', False, 1),
        ('time', True, 0), ('settime', False, 1),
        ('malloc', True, 1), ('free', False, 1),
        ('print', False, 1), ('prh', False, 1), ('prs', False, 1),
        ('prn', False, 2), ('cr', False, 0),
        ('led1on', False, 0), ('led1off', False, 0),
        ('led2on', False, 0), ('led2off', False, 0),
        ('led3on', False, 0), ('led3off', False, 0),
        ('led4on', False, 0), ('led4off', False, 0),
        ('alloff', False, 0),
        ('spiwrite', False, 1),
        ('ticks', True, 0),
        ('pin20on', False, 0), ('pin20off', False, 0),
    )

    setup_specials(
        ('(', True, handle_opening),
        (')', True, handle_closing),
        ('waituntil', False, handle_waituntil),
        ('make', False, handle_make),
        ('let', False, handle_let)
    )

    global next_global
    next_global = 0
    setup_globals(['n', 'm'])

mbed = None
def check():
    global mbed
    for x in range(2):
        start_comms()
        mbed.stop_everything()
        if '\x17' == mbed.test_communication(): return True
        mbed.close()
        mbed = None

    raise Exception()

def start_comms():
    global mbed
    if None == mbed: mbed = uartcomms.mbedLogo()

def check_comms():
    """Prepares communications with mbed by:
    - opening the port if not opened previously
    - blindly sending the stop command blindly
    - and checking the communications """
    start_comms()
    check()

setup()
print 'Welcome to Logo!'
try:
    start_comms()
except:
    print '  no logochip'

while True:
    try: s = raw_input()
    except EOFError: break
    except KeyboardInterrupt:
        print 'Goodbye!'
        break

    try:
        if 1 < len(s) and s[0] == '.': exec s[1:]
        else: run_line(s)
    except ValueError as e: print e
    except: traceback.print_exc()

if None != mbed: mbed.close()
