import torch
from mavi.torch.base_class.numerical_basis import Nbasist_fn
from mavi.torch.base_class.numerical_basis import NBasist as _Basist
from mavi.torch.base_class.numerical_basis import Intermidiate as _Intermidiate
from mavi.torch.util.util import res, pres, matrixfact, blow, blow1

class Basist(_Basist):
    def __init__(self, G, F):
        super().__init__(G, F)

class Intermidiate(_Intermidiate):
    def __init__(self, FX):
        super().__init__(FX)

    def extend(self, interm):
        super().extend(interm)

def initialize(X, **kwargs):
    device = X.device
    npoints, ndims = X.shape
    constant = 1./npoints**0.5

    F0 = Nbasist_fn(torch.ones(1,1, device=device)*constant)
    G0 = Nbasist_fn(torch.zeros(0,0, device=device))

    FX = torch.ones(npoints, 1, device=device) * constant

    interm = Intermidiate(FX)

    basis0 = Basist(G0, F0)
    return [basis0], interm


def init_candidates(X, **kwargs):
    return Intermidiate(X)


def candidates(int_1, int_t, degree=None):
    if degree == 2: 
        return Intermidiate(blow1(int_1.FX))
    else:
        return Intermidiate(blow(int_1.FX, int_t.FX))
        
# @profile
def construct_basis_t(cands, intermidiate, eps, **kwargs):
    CtX = cands.FX        # evaluation matrix of candidate polynomials
    FX = intermidiate.FX  # evlauation matrix of nonvanishing polynomials up to degree t-1

    CtX_, L = pres(CtX, FX)  # orthogonal projection

    d, V = matrixfact(CtX_)

    FtX = CtX_ @ V[:, d>eps]
    scales = FtX.norm(dim=0)
    FtX /= scales
    Ft = Nbasist_fn(V[:, d>eps] / scales, L)
    Gt = Nbasist_fn(V[:, d<=eps], L)

    return Basist(Gt, Ft), Intermidiate(FtX)