import os,re,numpy as np
LIB=None; _cache={}
def setlib(p):
    global LIB; LIB=p
def find(name):
    n=name.replace(chr(92),'/').lower()
    for d in ['parts','p','models','']:
        f=os.path.join(LIB,d,n)
        if os.path.exists(f): return f
    raise FileNotFoundError(name)
def load(name):
    """returns list of (colorcode, tri Nx3x3) in local coords; color 16 = inherit"""
    key=name.lower()
    if key in _cache: return _cache[key]
    tris={}
    with open(find(name),encoding='utf-8',errors='replace') as fh:
        for line in fh:
            t=line.split()
            if not t: continue
            if t[0]=='1':
                c=int(t[1]); v=list(map(float,t[2:14])); sub=' '.join(t[14:])
                M=np.array([[v[3],v[4],v[5]],[v[6],v[7],v[8]],[v[9],v[10],v[11]]]); o=np.array(v[0:3])
                for cc,tr in load(sub).items():
                    out=c if cc==16 else cc
                    tris.setdefault(out,[]).append(tr@M.T+o)
            elif t[0] in('3','4'):
                c=int(t[1]); p=np.array(list(map(float,t[2:]))).reshape(-1,3)
                tl=[p[[0,1,2]]] if t[0]=='3' else [p[[0,1,2]],p[[0,2,3]]]
                tris.setdefault(c,[]).append(np.array(tl))
    res={c:np.concatenate(v) for c,v in tris.items()}
    _cache[key]=res; return res
def colors():
    cols={}
    for line in open(os.path.join(LIB,'LDConfig.ldr'),encoding='utf-8'):
        m=re.search(r'!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9A-Fa-f]{6})',line)
        if m: cols[int(m.group(2))]=(m.group(1),tuple(int(m.group(3)[i:i+2],16) for i in (0,2,4)))
    return cols
