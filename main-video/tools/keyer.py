"""Green-screen keyer: green-dominance matte with spill suppression."""
import numpy as np

T_LO, T_HI = 12.0, 42.0  # g - max(r, b): <= T_LO is opaque, >= T_HI is transparent


def key(rgb):
    """rgb: HxWx3 uint8 -> HxWx4 uint8 premultiplied-free RGBA."""
    f = rgb.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    mx = np.maximum(r, b)
    d = g - mx
    a = 1.0 - np.clip((d - T_LO) / (T_HI - T_LO), 0.0, 1.0)
    # despill: never let green exceed the brighter of red/blue
    g2 = np.minimum(g, mx + 4.0)
    out = np.empty(rgb.shape[:2] + (4,), np.uint8)
    out[..., 0] = r
    out[..., 1] = g2
    out[..., 2] = b
    out[..., 3] = (a * 255.0 + 0.5).astype(np.uint8)
    return out
