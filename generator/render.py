import sys,math,time,numpy as np
sys.path.insert(0,sys.argv[1]); import ldr
from PIL import Image
ldr.setlib(sys.argv[2]); src,out=sys.argv[3],sys.argv[4]
yaw=math.radians(float(sys.argv[5])); pitch=math.radians(float(sys.argv[6])); W=int(sys.argv[7]) if len(sys.argv)>7 else 1400
cols=ldr.colors(); cols.setdefault(1136,("Reddish Orange",(202,76,11)))
T=[];C=[]
for line in open(src):
    t=line.split()
    if not t or t[0]!='1': continue
    c=int(t[1]); v=list(map(float,t[2:14])); o=np.array(v[:3]); M=np.array(v[3:]).reshape(3,3)
    for cc,tr in ldr.load(t[14]).items():
        if cc==24: continue
        rgb=cols[c if cc==16 else cc][1]
        T.append(tr@M.T+o); C.append(np.tile(rgb,(len(tr),1)))
T=np.concatenate(T).astype(float); C=np.concatenate(C).astype(float)
print('triangles',len(T))
# world: x right, y down (LDraw), z toward back. camera looks from front (-z), rotated by yaw, from above by pitch
P=T.copy(); P[...,1]*=-1        # y up
cy,sy=math.cos(yaw),math.sin(yaw); cp,sp=math.cos(pitch),math.sin(pitch)
Ry=np.array([[cy,0,-sy],[0,1,0],[sy,0,cy]]); Rx=np.array([[1,0,0],[0,cp,sp],[0,-sp,cp]])
P=P@(Rx@Ry).T        # now z = depth (larger = farther)
n=np.cross(P[:,1]-P[:,0],P[:,2]-P[:,0]); nn=np.linalg.norm(n,axis=1); keep=nn>1e-9
P,C,n=P[keep],C[keep],n[keep]/nn[keep][:,None]
L1=np.array([-0.4,0.7,-0.6]); L1/=np.linalg.norm(L1); L2=np.array([0.6,0.2,-0.5]); L2/=np.linalg.norm(L2)
sh=0.55+0.4*np.abs(n@L1)+0.15*np.abs(n@L2)
Cs=np.clip(C*sh[:,None],0,255)
mn=P[...,:2].reshape(-1,2).min(0); mx=P[...,:2].reshape(-1,2).max(0)
pad=0.06; span=(mx-mn).max()*(1+2*pad); H=int(W*(mx[1]-mn[1]+2*pad*span)/span*1.0)+1
s=W/span; off=np.array([W/2,H/2])-((mn+mx)/2)*s*np.array([1,-1])
X=P[...,0]*s+off[0]; Y=-P[...,1]*s+off[1]; Z=P[...,2]
zb=np.full((H,W),np.inf); img=np.zeros((H,W,3)); img[:]=(245,244,240)
t0=time.time()
for i in range(len(P)):
    x0,x1,x2=X[i]; y0,y1,y2=Y[i]
    xa=max(int(math.floor(min(x0,x1,x2))),0); xb=min(int(math.ceil(max(x0,x1,x2))),W-1)
    ya=max(int(math.floor(min(y0,y1,y2))),0); yb=min(int(math.ceil(max(y0,y1,y2))),H-1)
    if xa>xb or ya>yb: continue
    d=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
    if abs(d)<1e-12: continue
    gx,gy=np.meshgrid(np.arange(xa,xb+1)+0.5,np.arange(ya,yb+1)+0.5)
    w0=((y1-y2)*(gx-x2)+(x2-x1)*(gy-y2))/d; w1=((y2-y0)*(gx-x2)+(x0-x2)*(gy-y2))/d; w2=1-w0-w1
    m=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)
    if not m.any(): continue
    z=w0*Z[i,0]+w1*Z[i,1]+w2*Z[i,2]
    sub=zb[ya:yb+1,xa:xb+1]; upd=m&(z<sub)
    sub[upd]=z[upd]; img[ya:yb+1,xa:xb+1][upd]=Cs[i]
print('raster s',round(time.time()-t0,1))
# outline: darken depth discontinuities
dz=np.zeros_like(zb); zf=np.where(np.isinf(zb),1e9,zb)
for a in (0,1):
    g=np.abs(np.diff(zf,axis=a,prepend=zf[:1] if a==0 else zf[:,:1])); dz=np.maximum(dz,g)
edge=dz>6
img[edge]=img[edge]*0.45
im=Image.fromarray(img.astype(np.uint8)).resize((W//2,H//2),Image.LANCZOS)
im.save(out); print('saved',out,im.size)
