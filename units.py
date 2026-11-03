"""تبدیل واحدهای رایج اندازه‌گیری برای LIMS."""

LENGTH = {"m": 1.0, "mm": 1e-3, "um": 1e-6, "µm": 1e-6, "in": 0.0254}
PRESSURE = {"pa": 1.0, "kpa": 1e3, "mpa": 1e6, "bar": 1e5, "mbar": 1e2, "psi": 6894.757293168}
FORCE = {"n": 1.0, "kn": 1e3, "mn": 1e6, "kgf": 9.80665}
TORQUE = {"nm": 1.0, "knm": 1e3, "kgfm": 9.80665}

def _norm(u):
    return (u or "").strip().lower().replace("²", "2").replace(" ", "")

def convert(value, from_unit, to_unit):
    if value is None or not from_unit or not to_unit or _norm(from_unit) == _norm(to_unit):
        return float(value) if value is not None else None
    a, b = _norm(from_unit), _norm(to_unit)
    for table in (LENGTH, PRESSURE, FORCE, TORQUE):
        if a in table and b in table:
            return float(value) * table[a] / table[b]
    # absolute temperature conversions
    if a in ("c", "°c") and b in ("f", "°f"): return float(value) * 9.0/5.0 + 32.0
    if a in ("f", "°f") and b in ("c", "°c"): return (float(value) - 32.0) * 5.0/9.0
    if a in ("c", "°c") and b == "k": return float(value) + 273.15
    if a == "k" and b in ("c", "°c"): return float(value) - 273.15
    if a in ("f", "°f") and b == "k": return (float(value) - 32.0) * 5.0/9.0 + 273.15
    if a == "k" and b in ("f", "°f"): return (float(value) - 273.15) * 9.0/5.0 + 32.0
    raise ValueError(f"Unsupported unit conversion: {from_unit} -> {to_unit}")
