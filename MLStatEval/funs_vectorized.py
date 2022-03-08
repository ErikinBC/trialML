# Functions that do vectorized operations for different summary statistics
import numpy as np
from funs_support import cvec

def vec_arange(starts, lengths):
    # Repeat start position index length times and concatenate
    cat_start = np.repeat(starts, lengths)
    # Create group counter that resets for each start/length
    cat_counter = np.arange(np.sum(lengths)) - np.repeat(np.cumsum(lengths) - lengths, lengths)
    # Add group counter to group specific starts
    cat_range = cat_start + cat_counter
    return cat_range

"""
Calculates the LOO quantile (returns same size as data)
"""
def loo_quant_by_bool(data, boolean, q):
    # (i) Prepare data
    x = np.where(boolean, data, np.nan)  # For False values, assign nan
    ndim = len(x.shape)
    assert ndim <= 3, 'Function only works for up to three dimensions'
    if ndim == 1:
        boolean = cvec(boolean)
        x = cvec(x)
    if ndim == 2:
        shape = (1,) + x.shape
        boolean = boolean.reshape(shape)
        x = x.reshape(shape)
    assert x.shape == boolean.shape
    ns, nr, nc = x.shape
    sidx = np.repeat(range(ns), nc)
    cidx = np.tile(range(nc), ns)

    # (ii) Sort by columns
    x = np.sort(x, axis=1)
    n = np.sum(boolean, axis=1)  # Number of non-missing rows    
    n_flat = n.flatten()

    # (iii) Do LOO calculations
    n2 = n - 2
    ridx = n2*q
    lidx = np.clip(np.floor(ridx).astype(int),0,n.max())
    uidx = np.clip(np.ceil(ridx).astype(int),0,n.max())
    frac = ridx - lidx
    l = lidx.flatten()  # For [i,:,j] indexing
    u = uidx.flatten()
    reshape = lidx.shape  # To return to shape after flatten
    ndim = ns * nc
    starts = np.repeat(0, ndim)
    # Holder
    q_loo = np.where(np.isnan(x), np.nan, 0)

    # (i) Values up to (and including) the lower bound
    xl = x[sidx, l+1, cidx].reshape(reshape)
    xu = x[sidx, u+1, cidx].reshape(reshape)
    xd = xu - xl
    x_interp = xl + xd*frac
    loo_1 = np.repeat(x_interp.flat, l+1)
    # Prepare indices
    idx_s = np.repeat(sidx, l+1)
    idx_c = np.repeat(cidx, l+1)
    idx_r = vec_arange(starts, l+1)
    assert idx_s.shape == idx_c.shape == idx_r.shape
    q_loo[idx_s, idx_r, idx_c] = loo_1
    
    # (ii) upped-bound removed
    xl = x[sidx, l, cidx].reshape(reshape)
    xu = x[sidx, u+1, cidx].reshape(reshape)
    xd = xu - xl
    x_interp = xl + xd*frac
    loo_2 = np.repeat(x_interp, 1)
    q_loo[sidx,l+1,cidx] = loo_2

    # (iv) Values above the upper bound
    xl = x[sidx, l, cidx].reshape(reshape)
    xu = x[sidx, u, cidx].reshape(reshape)
    xd = xu - xl
    x_interp = xl + xd*frac
    n_pos_u = u + 1 + (l==u)
    n_left = n_flat - n_pos_u
    loo_3 = np.repeat(x_interp.flat, n_left)    
    idx_s = np.repeat(sidx, n_left)
    idx_c = np.repeat(cidx, n_left)
    idx_r = vec_arange(n_pos_u, n_flat-n_pos_u)
    q_loo[idx_s,idx_r,idx_c] = loo_3
    
    # Return imputed value
    return q_loo



"""Find the quantile (linear interpolation) for specific rows of each column of data
data:           np.array of data (nsim x nobs x ncol)
boolean:        np.array of which (i,j) positions to include in calculation
q:              Quantile target
"""
# data=df_s_val[3];boolean=(df_y_val[3]==1);q=0.5;interpolate='linear'
def quant_by_bool(data, boolean, q, interpolate='linear'):
    assert interpolate in ['linear', 'lower', 'upper']
    # (i) Prepare data
    x = np.where(boolean, data, np.nan)  # For False values, assign nan
    ndim = len(x.shape)
    assert ndim <= 3, 'Function only works for up to three dimensions'
    if ndim == 1:
        boolean = cvec(boolean)
        x = cvec(x)
    if ndim == 2:
        shape = (1,) + x.shape
        boolean = boolean.reshape(shape)
        x = x.reshape(shape)
    assert x.shape == boolean.shape
    ns, nr, nc = x.shape
    sidx = np.repeat(range(ns), nc)
    cidx = np.tile(range(nc), ns)

    # (ii) Sort by columns
    x = np.sort(x, axis=1)
    n = np.sum(boolean, axis=1)  # Number of non-missing rows

    # (iii) Find the row position that corresponds to the quantile
    ridx = q*(n-1)
    lidx = np.clip(np.floor(ridx).astype(int),0,n.max())
    uidx = np.clip(np.ceil(ridx).astype(int),0,n.max())    
    frac = ridx - lidx

    # (iv) Return depends on method
    reshape = lidx.shape
    if ns == 1:
        reshape = (nc, )  # Flatten if ns == 1
    q_lb = x[sidx, lidx.flatten(), cidx].reshape(reshape)
    if interpolate == 'lower':
        return q_lb
    q_ub = x[sidx, uidx.flatten(), cidx].reshape(reshape)
    if interpolate == 'upper':
        return q_ub
    # do linear interpolation
    dq = q_ub - q_lb
    q_interp = q_lb + dq*frac
    q_interp = q_interp.reshape(reshape)
    return q_interp

# data = np.random.randn(100, 3); q=[0.5, 0.5, 0.5]
def quant_by_col(data, q):
    q = np.array(q)
    assert len(data.shape) == 2
    assert data.shape[1] == len(q), 'q needs to align with data column dimension'
    
    # (ii) Sort by columns
    x = np.sort(data, axis=0)
    n, c = x.shape
    cidx = np.arange(c)

    # (iii) Find the row position that corresponds to the quantile
    ridx = q*(n-1)
    lidx = np.floor(ridx).astype(int)
    uidx = np.ceil(ridx).astype(int)
    frac = ridx - lidx

    # (iv) Linear interpolation
    q_lb = x[lidx, cidx]
    q_ub = x[uidx, cidx]
    dq = q_ub - q_lb
    q_interp = q_lb + dq*frac
    return q_interp