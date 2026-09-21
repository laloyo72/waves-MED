import scipy.io as sio

matfile = "../../cases/tarragona/output/202609/Malla_ca00_F3_20260908_20260909.mat"

# Cargar el archivo .mat
data = sio.loadmat(matfile)

print("\nVariables disponibles en el archivo:\n")

for k, v in data.items():
    # Ignorar metadatos internos de MATLAB
    if k.startswith("__"):
        continue

    # Imprimir nombre y forma de la variable
    try:
        shape = v.shape
    except AttributeError:
        shape = "scalar / estructura"

    print(f"  - {k:30s}  →  {shape}")

