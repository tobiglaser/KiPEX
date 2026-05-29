from math import sqrt, pi

def _sequence(n, ratio: int = 2):
    if n % 2 == 0:
        raise ValueError("n must be an odd number")
    m = n // 2
    return [ratio ** (m - abs(k - m)) for k in range(n)]

def _skin_depth(f: float) -> float:
    mu_0 = 4 * pi * 1e-7
    mu_r = 0.999994 # copper
    sigma = 58e6 # S/m
    delta_m = sqrt(1 / (pi * f * mu_0 * mu_r * sigma))
    return delta_m

def get_filament_number(w_mm: float, f: float, ratio: int = 2) -> int:
    w = w_mm / 1_000 # convert mm to m
    n_fh = 1
    smallest_filament = w * 1 / sum(_sequence(n_fh, ratio))
    delta = _skin_depth(f)
    while (delta < smallest_filament):
        n_fh += 2
        smallest_filament = w * 1 / sum(_sequence(n_fh, ratio))
    return n_fh


if __name__ == "__main__":
    f = 50e6

    w_mm = 0.3
    print(w_mm, "mm; ", f, "Hz; ", get_filament_number(w_mm, f))
    w_mm = 0.250
    print(w_mm, "mm; ", f, "Hz; ", get_filament_number(w_mm, f))
    w_mm = 0.250
    print(w_mm, "mm; ", f, "Hz; ", get_filament_number(w_mm, f))
    w_mm = 0.200
    print(w_mm, "mm; ", f, "Hz; ", get_filament_number(w_mm, f))
    w_mm = 0.400
    print(w_mm, "mm; ", f, "Hz; ", get_filament_number(w_mm, f))
    print("height")
    w_mm = 0.040
    print(w_mm, "mm; ", f, "Hz; ", get_filament_number(w_mm, f))
