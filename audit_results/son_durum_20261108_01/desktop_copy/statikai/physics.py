"""Statically determinate pin/roller beam, two downward point loads only.

Positions: metres from left support; forces: kN; upward reactions: positive.
No visual inference or OCR occurs in this module.
"""
import math


def validated_inputs(L, P1, x1, P2, x2):
    raw = (L, P1, x1, P2, x2)
    try:
        if any(isinstance(v, bool) for v in raw):
            raise ValueError('Boolean values are not engineering quantities')
        values = tuple(float(v) for v in raw)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError('Five finite numerical inputs are required') from error
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Inputs must be finite (NaN and infinity are invalid)')
    L, P1, x1, P2, x2 = values
    if not (0 < x1 < x2 < L and P1 > 0 and P2 > 0):
        raise ValueError('Supported domain requires 0 < x1 < x2 < L and P1,P2 > 0')
    return values


def reactions(L, P1, x1, P2, x2):
    L, P1, x1, P2, x2 = validated_inputs(L, P1, x1, P2, x2)
    rb = math.fsum((P1 * (x1/L), P2 * (x2/L)))
    ra = math.fsum((P1, P2, -rb))
    if not all(math.isfinite(v) and v > 0 for v in (ra, rb)):
        raise ValueError('Reaction calculation exceeded the numerical supported range')
    return ra, rb


def residuals(L, P1, x1, P2, x2, ra, rb):
    L, P1, x1, P2, x2 = validated_inputs(L, P1, x1, P2, x2)
    ra, rb = float(ra), float(rb)
    if not all(math.isfinite(v) for v in (ra, rb)):
        raise ValueError('Predicted reactions must be finite')
    force = math.fsum((ra, rb, -P1, -P2))
    moment = math.fsum((rb*L, -P1*x1, -P2*x2))
    if not all(math.isfinite(v) for v in (force, moment)):
        raise ValueError('Residual calculation exceeded the numerical supported range')
    return force, moment
