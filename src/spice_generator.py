from copy import deepcopy

def generate_spice(file_name: str,
                    net_names: list[str],
                    R: list[list[float]],
                    L: list[list[float]],
                    K: list[list[float]],
                    C: list[list[float]] | None = None,
                    external_gnd: bool = False,
                    comment: str = "") -> None:
    with open(file_name, 'w') as file:
        if comment:
            file.write(f"*{comment}\n")
        file.write(".SUBCKT PCB")
        for net in net_names:
            file.write(f" {net}_a {net}_b")
        
        gnd_ref = 0
        if external_gnd:
            file.write(" GND")
            gnd_ref = "GND"
        file.write("\n\n")

        nc: int = 1

        for i, net in enumerate(net_names):
            file.write(f"R{i+1} {net}_a N{nc} {R[i][i]}\n")
            for j, cross_L in enumerate(L[i]):
                next_node = f"N{nc+1}"
                if j == len(L)-1:
                    next_node = f"{net}_b"
                if L[i][j] >= 0:
                    file.write(f"L{i+1}{j+1} N{nc} {next_node} {L[i][j]}\n")
                elif L[i][j] < 0:
                    file.write(f"L{i+1}{j+1} {next_node} N{nc} {L[i][j]}\n")
                nc += 1
            file.write("\n")
        
        if C:
            C = deepcopy(C)
            for i, row in enumerate(C):
                for j, c in enumerate(row):
                    if c != 0:
                        for side in ['a', 'b']:
                            port = f"{net_names[i]}_{side}"
                            other_port = f"{net_names[j]}_{side}" if i != j else f"{gnd_ref}"
                            
                            file.write(f"C{i+1}{j+1}_{side} {port} {other_port} {abs(C[i][j])/2}\n")
                        C[i][j] = 0
                        C[j][i] = 0
            file.write("\n")

        K = deepcopy(K)
        for i, row in enumerate(K):
            K[i][i] = 0
            for j, k in enumerate(row):
                if k != 0:
                    file.write(f"K{i+1}{j+1}_{j+1}{i+1} L{i+1}{j+1} L{j+1}{i+1} {K[i][j]}\n")
                    K[i][j] = 0
                    K[j][i] = 0

        file.write("\n.ENDS PCB\n")


if __name__ == "__main__":
    generate_spice(
        file_name="my_spice_test.txt",
        net_names=['A', 'B', 'C'],
        R=[[11, 12, 13],
            [21, 22, 23],
            [31, 32, 33]],
        L=[[11, 12, 13],
            [21, 22, 23],
            [31, 32, 33]],
        K=[[0.00, 0.12, 0.13],
            [0.12, 0.00, 0.23],
            [0.13, 0.23, 0.00]],
        C=[[22, 24, 26],
            [24, 44, 46],
            [26, 46, 66]])
