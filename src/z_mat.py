from math import pi, sqrt
from spice_generator import generate_spice
from engineering_notation import EngUnit

class Z_mat:
    def __init__(self, csv_path, mat_path):
        self.read_ports(mat_path)
        self.read_imps(csv_path)
        self.calculate_coupling()

    def read_imps(self, csv_path: str) -> None:
        self.res = []
        self.ind = []
        self.x_l = []
        with open(csv_path) as file:
            self.freqs = []
            current_freq = None
            rs  = []
            ls  = []
            xls = []
            for line in file:
                freq, imps = self.parse_impedance_line(line)
                r_line  = []
                l_line  = []
                xl_line = []
                for r, xl in imps:
                    l = xl / (2 * pi * freq)
                    r_line.append(r)
                    l_line.append(l)
                    xl_line.append(xl)
                
                if not current_freq:
                    current_freq = freq
                    self.freqs.append(freq)
                elif freq != current_freq:
                    self.res.append(rs.copy())
                    self.ind.append(ls.copy())
                    self.x_l.append(xls.copy())
                    rs.clear()
                    ls.clear()
                    xls.clear()
                    current_freq = freq
                    self.freqs.append(freq)
                
                rs.append(r_line)
                ls.append(l_line)
                xls.append(xl_line)
            self.res.append(rs)
            self.ind.append(ls)
            self.x_l.append(xls)
        pass

    def read_ports(self, mat_path: str) -> None:
        with open(mat_path) as file:
            ports = []
            for line in file:
                if line.startswith("Row"):
                    name = line.split()[-1]
                    ports.append(name)
                else:
                    ports.reverse()
                    self.ports = ports
                    return

    def parse_impedance_line(self, line: str) -> tuple[float, list[tuple[float, float]]]:
        entries = line.split()
        freq = float(entries[0])
        i = 1
        imps = []
        while i < len(entries) - 1:
            res = float(entries[i])
            x_l = float(entries[i+1].removesuffix("j"))
            imps.append((res, x_l))
            i += 2
        return freq, imps

    def calculate_coupling(self) -> None:
        L = self.ind
        self.K = []
        for f, freq in enumerate(self.freqs):
            K_f = []
            for i, L_i in enumerate(L[f]):
                K_i = []
                for j, L_ij in enumerate(L_i):
                    k_ij = abs(L_ij) / sqrt(L[f][i][i] * L[f][j][j])
                    K_i.append(k_ij)
                K_f.append(K_i)
            self.K.append(K_f)

    def GetResistance(self) -> list[list[list[float]]]:
        return self.res
    def GetInductance(self) -> list[list[list[float]]]:
        return self.ind
    def GetFrequencies(self) -> list[float]:
        return self.freqs
    def GetRowPortNames(self) -> list[str]:
        return self.ports
    def GetCoupling(self) -> list[list[list[float]]]:
        return self.K


    def export_spice(self, file_name: str, target_frequency: float) -> None:
        index = 0
        smallest_difference = 1e9
        for i, f in enumerate(self.freqs):
            if abs(target_frequency - f) < smallest_difference:
                smallest_difference = abs(target_frequency - f)
                index = i
                if smallest_difference == 0:
                    break
        comment = f"Generated with KiPEX at f={EngUnit(self.freqs[index], 2, 0, 'Hz')}"
        generate_spice(file_name, self.ports, self.res[index], self.ind[index], self.K[index], comment=comment)



if __name__ == "__main__":
    from engineering_notation import EngUnit
    z = Z_mat("Zc.csv", "Zc.mat")
    F = z.GetFrequencies()
    L = z.GetInductance()
    R = z.GetResistance()
    P = z.GetRowPortNames()
    for i, f in enumerate(F):
        f = EngUnit(f, 0, 0, 'Hz')
        print(f"   {f}")
        for j, row in enumerate (R[i]):
            line = f"{P[j]}\t"
            for k, col in enumerate(row):
                r = EngUnit(R[i][j][k], 3, 0, 'Ω')
                l = EngUnit(L[i][j][k], 3, 0, 'H')
                line += f"{r} {l}\t"
            print(line)
