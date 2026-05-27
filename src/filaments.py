from math import sqrt, pi

def _sequence(n, ratio: int = 2):
    if n % 2 == 0:
        raise ValueError("n must be an odd number")
    m = n // 2
    return [ratio ** (m - abs(k - m)) for k in range(n)]

def _skin_depth(f: float) -> float:
    mu_0 = 4 * pi * 1e-7
    mu_r = 0.999994 # copper
    sigma = 58e6
    return sqrt(1 / (pi * f * mu_0 * mu_r * sigma))

def get_filament_number(w: float, f: float, ratio: int = 2) -> int:
    #TODO Check units in filamentation.
    w = w * 1e-3
    n_fh = 1
    smallest_filament = w * 1 / sum(_sequence(n_fh, ratio))
    delta = _skin_depth(f)
    while (delta < smallest_filament):
        n_fh += 2
        smallest_filament = w * 1 / sum(_sequence(n_fh, ratio))
    return n_fh


if __name__ == "__main__":
    f = 50e6

    w = 300e-6
    print(w, f, get_filament_number(w, f))
    w = 250e-6
    print(w, f, get_filament_number(w, f))
    w = 250e-6
    print(w, f, get_filament_number(w, f))
    w = 200e-6
    print(w, f, get_filament_number(w, f))
    w = 400e-6
    print(w, f, get_filament_number(w, f))
    print("height")
    w = 40e-6
    print(w, f, get_filament_number(w, f))
