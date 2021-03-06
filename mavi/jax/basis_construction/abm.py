# from math import perm
# from sympy.logic.boolalg import term_to_integer
# from sympy.utilities.iterables import filter_symbols
from mavi.jax.base_class.symbolic_basis import SBasist as _Basist
from mavi.jax.base_class.symbolic_basis import Intermidiate as _Intermidiate
from mavi.jax.util.util import matrixfact, blow, argsort
from mavi.jax.util.symbolic_util import border_terms

import jax.numpy as np
import sympy as sm 
from sympy.polys.orderings import monomial_key

class Basist(_Basist):
    def __init__(self, G, F):
        super().__init__(G, F)

class Intermidiate(_Intermidiate):
    def __init__(self, FX, Fsymb, gens, term_order):
        super().__init__(FX, Fsymb, gens)
        self.term_order = term_order

def initialize(X, term_order='grevlex'):  # mush have term_order as keyword arg

    npoints, nvars = X.shape
    constant = 1.

    F = [np.ones((1,1))*constant]
    G = [np.zeros((0,0))]

    FX = np.ones((npoints, 1)) * constant

    gens = sm.symbols(f'x:{nvars}')
    Fsymb = [sm.poly(constant, gens=gens, domain='RR')]
    interm = Intermidiate(FX, Fsymb, gens, term_order)

    basis0 = Basist([], [sm.poly(constant, gens=gens)])
    return [basis0], interm


def init_candidates(X, term_order='grevlex'):  # must have gen & term_order as keyword arg
    nvars = X.shape[1]

    gens = sm.symbols(f'x:{nvars}')
    cands_symb = [sm.poly(gen, gens=gens) for gen in gens]
    
    perm = argsort(cands_symb, key=monomial_key(term_order, gens), reverse=True)  # accesnding
    cands = X[:, perm]
    cands_symb = np.asarray(cands_symb)[perm].tolist()
    
    return Intermidiate(cands, cands_symb, gens, term_order)


def candidates(int_1, int_t):
    cands, cands_symb = border_terms(int_1.FX, int_t.FX, int_1.Fsymb, int_t.Fsymb, int_1.gens, int_1.term_order)
    return Intermidiate(cands, cands_symb, int_1.gens, int_1.term_order)


def construct_basis_t(cands, intermidiate, eps, **kwargs):
    CtX = cands.FX        # evaluation matrix of candidate polynomials
    FX = intermidiate.FX  # evlauation matrix of nonvanishing polynomials up to degree t-1
    Fsymb = intermidiate.Fsymb
    Ftsymb = []  # order ideal of degree t
    Gtsymb = []
    FtX = np.zeros((FX.shape[0], 0))
    for i, bterm in enumerate(cands.Fsymb): 
        bX = CtX[:, i].reshape(-1, 1)
        M = np.hstack([FX, FtX, bX])
        d, V = matrixfact(M)

        if np.min(d) > eps: 
            Ftsymb.append(bterm)
            FtX = np.hstack([FtX, bX])
        else: 
            g = sum((Fsymb + Ftsymb + [bterm]) * V[:, np.argmin(d)])
            Gtsymb.append(g)

    return (Basist(Gtsymb, Ftsymb), 
            Intermidiate(FtX, Ftsymb, intermidiate.gens, intermidiate.term_order))