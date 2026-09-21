import scipy.io as sio
import matplotlib.pyplot as plt
import numpy as np

mat = sio.loadmat("../../cases/tarragona/output/202609/Malla_ca00_F3_20260908_20260909.mat")

Xp = mat["Xp"]
Yp = mat["Yp"]
Depth = mat["Depth_20260908_000000"]

# Punto UTM
#utm_x = 349884
#utm_y = 4548954
utm_x = 349939
utm_y = 4549575

plt.figure(figsize=(10, 8))
plt.pcolormesh(Xp, Yp, Depth, shading="auto", cmap="turbo")

plt.scatter(utm_x, utm_y, s=80, c="red", edgecolor="black", label="Punto UTM")
plt.legend()

plt.colorbar(label="Profundidad relativa (0-1)")
plt.title("Dominio y batimetría")
plt.xlabel("X")
plt.ylabel("Y")
plt.gca().set_aspect("equal")
plt.tight_layout()
plt.show()

