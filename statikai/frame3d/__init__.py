"""User-defined orthogonal-grid 3D elastic frame analysis, not image reconstruction.

Units: m, kN, kNm; global Y is vertical. Rectangular gross sections, rigid
joints, Euler-Bernoulli members, first-order small-displacement analysis.

Load cases G (self weight + slab dead load), Q (slab live load), EX / EZ (user
lateral storey forces). Slab loads reach the beams as 45 degree envelope
line loads. Optional approximate rigid diaphragm per storey.

Modules: ``config`` (inputs, validation, migration), ``loads`` (load
distribution), ``model`` (PyNite assembly), ``analysis`` (solution and audit).
"""
import os
from pathlib import Path

_cache=Path(__file__).resolve().parents[2]/'work'/'matplotlib'
_cache.mkdir(parents=True,exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(_cache))

from .config import (CASES, LEGACY_SCHEMAS, MAX_BAYS, MAX_COMBINATIONS, MAX_FLOORS, SCHEMA,
                     FrameConfig, default_combinations, validate_combinations)
from .loads import envelope_segments, segment_resultant, tributary_weights
from .model import build_frame, node_name, rectangle_properties
from .analysis import QUANTITIES, member_diagram, solve_frame, story_drifts

__all__=['CASES','LEGACY_SCHEMAS','MAX_BAYS','MAX_COMBINATIONS','MAX_FLOORS','SCHEMA','QUANTITIES',
         'FrameConfig','default_combinations','validate_combinations','envelope_segments',
         'segment_resultant','tributary_weights','build_frame','node_name','rectangle_properties',
         'member_diagram','solve_frame','story_drifts']
