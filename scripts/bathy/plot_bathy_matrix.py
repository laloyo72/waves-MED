import numpy as np
import matplotlib.pyplot as plt

def plot_depth_matrix(matrix_file):
    """Reads and plots a depth matrix file (structured as a grid)."""
    # Load depth matrix (each row is a y-coordinate, each column is an x-coordinate)
    depth_matrix = np.loadtxt(matrix_file)

    # Plot using imshow (image-style) or contourf (contour-style)
    plt.figure(figsize=(10, 8))
    
    # Use `imshow` for a fast visualization
    plt.imshow(depth_matrix, cmap='viridis', origin='upper', aspect='auto', vmax=0, vmin=-1)#, vmax=-1)

    # Optional: Use `contourf` for a smoother plot (comment `imshow` above if using this)
    #plt.contourf(depth_matrix, levels=50, cmap='viridis')

    plt.colorbar(label="Depth (m)")  # Color legend
    plt.xlabel("X (grid columns)")
    plt.ylabel("Y (grid rows)")
    plt.title("Bathymetry Depth Grid")
    plt.axis('equal')
    plt.show()

# File path to depth matrix
#depth_matrix_file = "../../cases/palma/bathy/bottom_ca00_matrix.dat"
#depth_matrix_file = "../../cases/cala_millor/bathy/bottom_ca21_HRES_matrix.dat"
#depth_matrix_file = "../../cases/murcia/bathy/bottom_ca01_HRES_matrix.dat"
#depth_matrix_file = "../../bathy/bottom_ca12_matrix.dat"
#depth_matrix_file = "../../cases/alcudia/bathy/bottom_ca03_matrix.dat"
depth_matrix_file = "../../cases/tarragona/bathy/bottom_ca00_matrix.dat"
# Plot depth matrix
plot_depth_matrix(depth_matrix_file)
