import numpy as np
from scipy import linalg
from sympy.polys.orderings import monomial_key
# import cvxpy as cp 
from scipy.optimize import minimize

def blow(A, B):  
    # A = F1 = {p1(X), p2, ...}, B = F2 = {q1, q2, ...}
    # output: {p1(X)*q1(X), p1*q2, ....}
    A, B = np.asarray(A), np.asarray(B)
    n1, n2 = A.shape[-1], B.shape[-1]
    C = np.repeat(A, n2, axis=-1) * np.tile(B, n1)
    return C

def dblow(A, B, dA, dB):
    A, B, dA, dB = np.asarray(A), np.asarray(B), np.asarray(dA), np.asarray(dB)
    n1, n2 = A.shape[1], B.shape[1]
    ndims = np.int(dA.shape[0]/A.shape[0])

    C = np.repeat(A, n2, axis=-1) * np.tile(B, n1)
    dC1 = np.repeat(np.repeat(A, ndims, axis=0), n2, axis=-1) * np.tile(dB, n1)
    dC2 = np.repeat(dA, n2, axis=-1) * np.tile(np.repeat(B, ndims, axis=0), n1)
    dC = dC1 + dC2 
    # dC = (np.repeat(np.repeat(A, ndims, axis=0), n2, axis=1) * np.tile(dB, n1) 
    #       + np.repeat(dA, n2, axis=1) * np.tile(np.repeat(B, ndims, axis=0), n1))
    return C, dC

## extract residual components and projection operator
def pres(C, F):
    L = np.linalg.lstsq(F, C, rcond=None)[0]
    res = C - F @ L     # by definition, res == torch.hstack([F, C]) @ L
    return res, L

## project C to residual space
def res(C, F, L):
    return C - F @ L

def matrixfact(C):
    _, d, Vt = np.linalg.svd(C, full_matrices=C.shape[0] <= C.shape[1])
    d = np.append(d, np.zeros(Vt.shape[0] - len(d)))
    return d, Vt.T

def matrixfact_gep(C, N, gamma=1e-9, diag_normalizer=False):

    if diag_normalizer: 
        if np.all(np.diag(N) > gamma): 
            ## reduce GEP to EP
            # (Di^-1.T C.T C Di) v = rv, v.Tv = 1
            # C.T C (Div) = r (Div), (Div).T (D.T D) (Div) = 1
            # C.T C u = ru, u.T u = 1
            # u = Div

            Di = np.diag(1./np.diag(N))
            d, V = matrixfact(C @ Di)
            d = d 
            V = Di @ V

            # Di = np.diag(1./diag)
            # d, V = matrixfact(C / diag)
            # V = diag.reshape(-1,1) * V

            return d, V

    A = C.T @ C
    B = N.T @ N

    r = np.linalg.matrix_rank(B, gamma)
    gamma_ = np.mean(np.diag(B))*gamma
    d, V = linalg.eigh(A, B+gamma_*np.identity(B.shape[0]))
    # d, V = indirect_ged(A, B, gamma=gamma)  a bit slower
    d = np.sqrt(np.abs(d))

    gnorms = np.diag(V.T@B@V)
    valid = np.argsort(-gnorms)[:r]

    d, V = d[valid], V[:, valid]
    gnorms = gnorms[valid]
   
    perm = np.argsort(-d)

    return d[perm], V[:, perm]

def indirect_ged(C, N, gamma=1e-9):
    A = C.T @ C
    B = N.T @ N
    '''
    Reduce GED to two SVD
    '''
    Vb, db, _ = np.linalg.svd(B, hermitian=True, full_matrices=False)
    db, Vb = db[db > gamma], Vb[:, db > gamma]
    Vb_ = Vb / (db)

    A_ = Vb_.T @ A @ Vb_
    Va, d, _ = np.linalg.svd(A_, hermitian=True)
    V = Vb_ @ Va
    return d**0.5, V

def argsort(arr, key=None, reverse=False):
    arr_ = enumerate(arr)
    arr_ = sorted(arr_, key=lambda x: key(x[1]), reverse=reverse)
    perm = list(zip(*arr_))[0]
    return list(perm)

def power_ged(C, N, k=1.1, max_iter=100):
    A = C.T @ C
    B = N.T @ N

    pged = PowerGED()
    pged.fit(A, B, max_iter=max_iter)
    rmax, v =  pged.d, pged.v

    pged = PowerGED()
    pged.fit(k*rmax*B - A, B, max_iter=max_iter)
    d, v =  pged.d, pged.v

    d = (v.T @ A @ v)[0]**0.5
    return d, v

class PowerGED:
    def __init__(self):
        ''
    def fit(self, A, B, max_iter=100):
        n = A.shape[0]
        v = np.random.randn(n, 1)
        v /= (v.T @ B @ v)[0,0]**0.5


        for t in range(max_iter):
            beta = ((v.T @ A @ v) / (v.T @ B @ v))[0,0]
            v = self.qsoler(B, A @ v, x0=beta*v)
            v /= (v.T @ B @ v)[0,0]**0.5
        
        d = (v.T @ A @ v)[0]

        self.v = v 
        self.d = d
        return self

    def qsoler(self, S, r, x0):
        '''
        min_x  x.T @ S @ x - r.T @ x
        '''
        ## cvxpy does not work with m1 mac
        # n = cp.Variable(len(v)) 
        # obj = cp.Minimize(cp.Minimize((1/2)*cp.quad_form(v, S) + r.T @ v))
        # prob = cp.Problem(obj, [])
        # prob.solve()

        if x0 is None:
            x0 = np.random.randn(len(r), 1)
            x0 /= np.linalg.norm(x0)

        x0 = x0.flatten() 
        r = r.flatten()
        obj = lambda x: 0.5 * x.T @ S @ x - r.T @ x
        jac = lambda x: S @ x - r

        res = minimize(obj, x0, method='BFGS', jac=jac)# , options={'disp': True})
        return res.x.reshape(-1, 1)
