"""Measure an LDraw part: footprint (studs), height (plate layers), per-voxel fill fraction, studs per column, for 4 rotations."""
import numpy as np, ldr
ROTS=[np.eye(3), np.array([[0,0,1],[0,1,0],[-1,0,0]]), np.array([[-1,0,0],[0,1,0],[0,0,-1]]), np.array([[0,0,-1],[0,1,0],[1,0,0]])]
def tris_of(part):
    g=ldr.load(part+'.dat'); return np.concatenate([v for c,v in g.items() if c!=24])
def topmap(T,xs,zs):
    """highest surface (min LDraw y) under each (x,z) sample; nan if no hit"""
    a,b,c=T[:,0],T[:,1],T[:,2]
    out=np.full(len(xs),np.nan)
    d=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2])
    ok=np.abs(d)>1e-9; a,b,c,d=a[ok],b[ok],c[ok],d[ok]
    for n,(x,z) in enumerate(zip(xs,zs)):
        w0=((b[:,2]-c[:,2])*(x-c[:,0])+(c[:,0]-b[:,0])*(z-c[:,2]))/d
        w1=((c[:,2]-a[:,2])*(x-c[:,0])+(a[:,0]-c[:,0])*(z-c[:,2]))/d
        w2=1-w0-w1; m=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)
        if m.any():
            y=w0[m]*a[m,1]+w1[m]*b[m,1]+w2[m]*c[m,1]; out[n]=y.min()
    return out
def analyse(part):
    T0=tris_of(part); res=[]
    for r,R in enumerate(ROTS):
        T=T0@R.T; V=T.reshape(-1,3)
        bot=V[:,1].max()
        # footprint from geometry below the stud line
        mnx,mxx,mnz,mxz=V[:,0].min(),V[:,0].max(),V[:,2].min(),V[:,2].max()
        nx=int(round((mxx-mnx)/20)); nz=int(round((mxz-mnz)/20))
        if nx<1 or nz<1 or abs(mxx-mnx-20*nx)>2.5 or abs(mxz-mnz-20*nz)>2.5: return None
        per=[(-7,-7),(0,-7),(7,-7),(-7,0),(7,0),(-7,7),(0,7),(7,7)]; ring=[(4.6,0),(-4.6,0),(0,4.6),(0,-4.6)]
        xs=[];zs=[]
        for i in range(nx):
            for k in range(nz):
                cx=mnx+20*i+10; cz=mnz+20*k+10
                for dx,dz in per+ring: xs.append(cx+dx); zs.append(cz+dz)
        y=topmap(T,np.array(xs),np.array(zs)); h=bot-y; h=np.where(np.isnan(h),0,h).reshape(nx,nz,12)
        hp=h[:,:,:8]; hr=h[:,:,8:].max(2); body=hp.max(2)
        stud=(hr-body>3)&(hr-body<5.5)&(np.abs(body/8-np.round(body/8))<0.15)
        ny=int(np.ceil(body.max()/8-0.15))
        if ny<1: return None
        fill=np.zeros((nx,ny,nz))
        for l in range(ny): fill[:,l,:]=np.clip((hp-8*l)/8,0,1).mean(2)
        res.append(dict(rot=r,nx=nx,nz=nz,ny=ny,fill=fill.tolist(),stud=stud.tolist(),off=[float(mnx),float(bot),float(mnz)]))
    return res
