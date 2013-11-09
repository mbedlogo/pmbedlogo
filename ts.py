source = ''
offset = 0
oblist = {}

def init(s):
    global source, offset
    source = s
    offset = 0
    skipSpace()

def eof():
    return len(source) == offset

def readList():
    result = []
    while not eof():
        token = readToken()
        if (None != token): result.append(token)
        else: break

    return result

def readToken():
    s = next();
    if len(s) == 0: return intern(s)
    
    if s[0] == '$':
        try: return int(s[1:], 16)
        except ValueError: pass
    
    if s[0] == '"': return qsym(intern(s[1:]))
    if s[0] == ':': return dsym(intern(s[1:]))
    if s[0] == '|': return s[1:]
    if s[0] == ']': return None
    if s[0] == '[': return readList()
    if s[0] == '#':
        try: return int(s[1:], 2)
        except ValueError: pass
    
    if s[-1] == 'f':
        try: return float(s[:-1])
        except ValueError: pass

    try: return int(s)
    except ValueError: pass
    
    try: return float(s)
    except ValueError: pass
    
    try: return int(s, 8)
    except ValueError: pass
    
    try: return int(s, 16)
    except ValueError: pass
    
    return intern(s)

def next():
    s = ''
    if not delim(peekChar()):
        while not eof() and not delim(peekChar()):
            if peekChar() == '|':
                s += getVbarString()
                skipSpace()
                return s
            else:
                s += nextChar()
    else:
        s = nextChar()
    
    skipSpace()
    return s

def getVbarString():
    s = ''
    nextChar()
    while not eof():
        if peekChar() == '|':
            nextChar()
            break
        else: s += nextChar()
    
    return s

def peekChar():
    return source[offset]

def nextChar():
    global offset
    pos = offset
    offset += 1
    return source[pos]

def delim(s): return "()[] ,\t\r\n".find(s[0]) != -1

def skipSpace():
    global offset
    while not eof() and ' ;,\t\r\n'.find(peekChar()) != -1:
        if peekChar() == ';':
            while not eof() and '\r\n'.find(peekChar()) == -1:
                offset += 1
        else: offset += 1

def intern(s):
    if len(s) == 0: lcstr = s
    elif s[0] == '|': lcstr = s[1:]
    else: lcstr = s.lower()
    sym = oblist.get(lcstr)
    if sym == None:
        sym = symbol(s)
        oblist[lcstr] = sym
    return sym

class symbol:
    def __init__(self, pname): self.pname = pname
    
    def __repr__(self): return '<symbol: ' + self.pname + '>'

class qsym:
    def __init__(self, sym): self.sym = sym
    
    def __repr__(self): return '<qsym: ' + self.sym.pname + '>'

    def __str__(self): return self.sym.pname
        
class dsym:
    def __init__(self): self.sym = sym
    
    def __repr__(self): return '<dsym: ' + self.sym.pname + '>'
