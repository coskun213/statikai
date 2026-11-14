"""Load distribution helpers that do not depend on the solver."""
import numpy as np


def envelope_segments(length,half_short_span,peak):
    """Line load along one slab-panel edge by the 45 degree envelope rule.

    Returns (w1, w2, x1, x2) pieces: a triangle on the short side, a trapezoid
    otherwise. ``peak`` is w * (short span) / 2, the ramp length is half the
    short span.
    """
    a=half_short_span
    if length-2*a<=1e-9*length:
        mid=length/2
        return [(0.,peak,0.,mid),(peak,0.,mid,length)]
    return [(0.,peak,0.,a),(peak,peak,a,length-a),(peak,0.,length-a,length)]


def segment_resultant(start,end,w1,w2,x1,x2):
    """Global downward resultant and its point for a trapezoidal line-load piece."""
    start,end=np.asarray(start,float),np.asarray(end,float)
    unit=(end-start)/np.linalg.norm(end-start)
    magnitude=(w1+w2)/2*(x2-x1)
    local=x1+(x2-x1)*(w1+2*w2)/(3*(w1+w2)) if w1+w2 else (x1+x2)/2
    return np.array([0.,-magnitude,0.]),start+unit*local


def tributary_weights(spans_x,spans_z):
    """Plan tributary area fraction of every grid node, keyed by (ix, iz).

    Storey lateral forces are shared in this ratio, so their resultant acts at
    the plan-area centroid (the mass centre for a uniform slab load).
    """
    def half_widths(spans):
        return [((spans[i-1] if i>0 else 0.)+(spans[i] if i<len(spans) else 0.))/2
                for i in range(len(spans)+1)]
    wx,wz=half_widths(spans_x),half_widths(spans_z)
    total=sum(spans_x)*sum(spans_z)
    return {(ix,iz):wx[ix]*wz[iz]/total for ix in range(len(wx)) for iz in range(len(wz))}
