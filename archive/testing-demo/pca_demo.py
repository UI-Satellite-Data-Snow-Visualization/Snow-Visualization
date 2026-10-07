import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# SNOWMELT PCA — SMALL TEACHING DEMO
# ============================================================
#
# Goal:
#
#   Yearly FDL rasters
#          ↓
#   Flatten into vectors
#          ↓
#      D matrix
#          ↓
#   Center the data
#          ↓
#   Covariance matrix
#          ↓
#   Eigenvalues / Eigenvectors
#          ↓
#      D @ e1
#          ↓
#        PC1
#          ↓
#   Reshape into raster
#
#
# FDL = First Day of Land
#
# Each FDL value represents the day-of-year (DOY) when
# that geographic pixel was first observed as LAND
# after previously being snow covered.
#
# Smaller DOY = earlier melt
# Larger DOY  = later melt
#
# ============================================================


# ============================================================
# STEP 1 — CREATE THREE TINY FDL RASTERS
# ============================================================
#
# Pretend these are three years of satellite-derived data.
#
#
# 2022:
#
#       [110  120  130]
#       [120  130  140]
#       [130  140  150]
#
#
# Each location in the matrix represents the SAME geographic
# location across every year.
#
# For example:
#
# Pixel (0,0):
#
#     2022 = DOY 110
#     2023 = DOY 112
#     2024 = DOY 108
#
# That location consistently melts relatively early.
#
# ============================================================

fdl_2022 = np.array([
    [110, 120, 130],
    [120, 130, 140],
    [130, 140, 150]
], dtype=float)

fdl_2023 = np.array([
    [112, 119, 132],
    [121, 133, 141],
    [129, 142, 153]
], dtype=float)

fdl_2024 = np.array([
    [108, 122, 128],
    [118, 131, 143],
    [132, 139, 148]
], dtype=float)


print("\n")
print("==========================================")
print("STEP 1 — ORIGINAL FDL RASTERS")
print("==========================================")

print("\n2022:")
print(fdl_2022)

print("\n2023:")
print(fdl_2023)

print("\n2024:")
print(fdl_2024)


# ============================================================
# STEP 2 — FLATTEN EACH RASTER
# ============================================================
#
# PCA doesn't care that our data originally looked like:
#
#       [110 120 130]
#       [120 130 140]
#       [130 140 150]
#
#
# We can unwrap that raster into:
#
#       [110]
#       [120]
#       [130]
#       [120]
#       [130]
#       [140]
#       [130]
#       [140]
#       [150]
#
#
#             3 x 3
#
#               ↓
#
#             9 x 1
#
#
# IMPORTANT:
#
# We MUST preserve the ordering.
#
# Row 1 always represents Pixel 1.
# Row 2 always represents Pixel 2.
# etc.
#
# ============================================================

v2022 = fdl_2022.flatten()
v2023 = fdl_2023.flatten()
v2024 = fdl_2024.flatten()


print("\n")
print("==========================================")
print("STEP 2 — FLATTENED VECTORS")
print("==========================================")

print("\n2022 vector:")
print(v2022.reshape(-1, 1))

print("\n2023 vector:")
print(v2023.reshape(-1, 1))

print("\n2024 vector:")
print(v2024.reshape(-1, 1))


# ============================================================
# STEP 3 — BUILD THE D MATRIX
# ============================================================
#
# Put each YEAR beside the other years.
#
#
#                D
#
#             YEAR
#
#          2022   2023   2024
#
# Pixel 1 [110    112    108]
# Pixel 2 [120    119    122]
# Pixel 3 [130    132    128]
# Pixel 4 [120    121    118]
# Pixel 5 [130    133    131]
# Pixel 6 [140    141    143]
# Pixel 7 [130    129    132]
# Pixel 8 [140    142    139]
# Pixel 9 [150    153    148]
#
#
# Therefore:
#
#           D = 9 x 3
#
#        9 pixels x 3 years
#
#
# In the research paper:
#
#       D = 41,503 x 17
#
# 41,503 pixels x 17 years
#
# ============================================================

D = np.column_stack([
    v2022,
    v2023,
    v2024
])


print("\n")
print("==========================================")
print("STEP 3 — D MATRIX")
print("==========================================")

print(D)

print("\nD dimensions:")
print(D.shape)

print("\nRows = pixels")
print("Columns = years")


# ============================================================
# STEP 4 — CENTER THE DATA
# ============================================================
#
# First calculate the mean of EACH YEAR.
#
#
# Example:
#
#              2022   2023   2024
#
# Mean =       mean   mean   mean
#
#
# Then subtract the appropriate year's mean from every value.
#
#
# ORIGINAL:
#
#       [110 112 108]
#
#
# CENTERED:
#
#       [110 - mean2022,
#        112 - mean2023,
#        108 - mean2024]
#
#
# Why?
#
# PCA is interested in how the values VARY around their
# average rather than simply their absolute DOY values.
#
# ============================================================

year_means = np.mean(D, axis=0)

D_centered = D - year_means


print("\n")
print("==========================================")
print("STEP 4 — CENTER THE DATA")
print("==========================================")

print("\nYear means:")
print(year_means)

print("\nCentered D matrix:")
print(D_centered)


# ============================================================
# STEP 5 — COVARIANCE MATRIX
# ============================================================
#
# Now determine how the YEARS vary together.
#
# We have 3 years.
#
# Therefore our covariance matrix is:
#
#
#                   2022       2023       2024
#
#        2022   [   cov        cov        cov   ]
#
# C =    2023   [   cov        cov        cov   ]
#
#        2024   [   cov        cov        cov   ]
#
#
#                     3 x 3
#
#
# If two years have similar spatial melt behavior,
# their covariance should reflect that relationship.
#
# ============================================================

C = np.cov(D_centered, rowvar=False)


print("\n")
print("==========================================")
print("STEP 5 — COVARIANCE MATRIX")
print("==========================================")

print(C)

print("\nCovariance dimensions:")
print(C.shape)


# ============================================================
# STEP 6 — FIND EIGENVALUES AND EIGENVECTORS
# ============================================================
#
# THIS SHOULD LOOK FAMILIAR FROM LINEAR ALGEBRA:
#
#
#                 A v = λv
#
#
# Here our matrix A is the covariance matrix C:
#
#
#                 C v = λv
#
#
# Eigenvectors:
#
#     directions in the data
#
#
# Eigenvalues:
#
#     how much variance exists in those directions
#
#
# PCA wants the eigenvector associated with the
# LARGEST eigenvalue first.
#
# ============================================================

eigenvalues, eigenvectors = np.linalg.eigh(C)


# np.linalg.eigh gives them smallest → largest.
#
# We want:
#
# largest → smallest

order = np.argsort(eigenvalues)[::-1]

eigenvalues = eigenvalues[order]
eigenvectors = eigenvectors[:, order]


print("\n")
print("==========================================")
print("STEP 6 — EIGENVALUES")
print("==========================================")

print(eigenvalues)


print("\nEigenvectors:")
print(eigenvectors)


# ============================================================
# STEP 7 — EXPLAINED VARIANCE
# ============================================================
#
# Add all eigenvalues together.
#
# Then ask:
#
#     What percentage belongs to each eigenvalue?
#
#
# Example:
#
# PC1 = 95%
# PC2 = 4%
# PC3 = 1%
#
#
# This DOES NOT mean:
#
#       "PC1 is 95% accurate."
#
#
# It means:
#
#       PC1 accounts for 95% of the variance
#       contained in this dataset.
#
# ============================================================

explained_variance = (
    eigenvalues / np.sum(eigenvalues)
)


print("\n")
print("==========================================")
print("STEP 7 — EXPLAINED VARIANCE")
print("==========================================")

for i, variance in enumerate(explained_variance):

    print(
        f"PC{i + 1}: "
        f"{variance * 100:.2f}%"
    )


# ============================================================
# STEP 8 — TAKE THE FIRST EIGENVECTOR
# ============================================================
#
# The largest eigenvalue corresponds to the first
# eigenvector.
#
#
# Suppose NumPy gives something similar to:
#
#
#              e1
#
#           [ 0.57 ]
#           [ 0.59 ]
#           [ 0.57 ]
#
#
#             3 x 1
#
#
# There is one component corresponding to each YEAR.
#
# ============================================================

e1 = eigenvectors[:, 0]


print("\n")
print("==========================================")
print("STEP 8 — FIRST EIGENVECTOR e1")
print("==========================================")

print(e1.reshape(-1, 1))


# ============================================================
# STEP 9 — MATRIX MULTIPLICATION
# ============================================================
#
# THIS IS THE BIG ONE.
#
#
#       D_centered     @       e1
#
#
#          9 x 3              3 x 1
#
#
#                    =
#
#
#                   PC1
#
#                   9 x 1
#
#
# ------------------------------------------------------------
#
# Visually:
#
#
#   D_centered               e1              PC1
#
# [ a11 a12 a13 ]          [ e1 ]           [ p1 ]
# [ a21 a22 a23 ]          [ e2 ]           [ p2 ]
# [ a31 a32 a33 ]          [ e3 ]           [ p3 ]
# [ a41 a42 a43 ]                           [ p4 ]
# [ a51 a52 a53 ]      x                    [ p5 ]
# [ a61 a62 a63 ]                           [ p6 ]
# [ a71 a72 a73 ]                           [ p7 ]
# [ a81 a82 a83 ]                           [ p8 ]
# [ a91 a92 a93 ]                           [ p9 ]
#
#
# ------------------------------------------------------------
#
# For Pixel 1:
#
#
# p1 =
#
# (Pixel1 centered 2022 * e1[0])
#
#             +
#
# (Pixel1 centered 2023 * e1[1])
#
#             +
#
# (Pixel1 centered 2024 * e1[2])
#
#
# That's just ordinary matrix multiplication.
#
# ============================================================

PC1 = D_centered @ e1


print("\n")
print("==========================================")
print("STEP 9 — PC1 VECTOR")
print("==========================================")

print(PC1.reshape(-1, 1))

print("\nPC1 dimensions:")
print(PC1.shape)


# ============================================================
# STEP 10 — SHOW PIXEL 1 BY HAND
# ============================================================
#
# Let's prove that NumPy is really just doing the
# matrix multiplication we learned in class.
#
# Take ROW 1 of D_centered:
#
#
#       [a11 a12 a13]
#
#
# Multiply by:
#
#
#       [e1]
#       [e2]
#       [e3]
#
#
# Result:
#
#
# a11*e1 + a12*e2 + a13*e3
#
#
# That gives PC1's value for Pixel 1.
#
# ============================================================

pixel1 = D_centered[0]

pixel1_pc1 = (
    pixel1[0] * e1[0]
    + pixel1[1] * e1[1]
    + pixel1[2] * e1[2]
)


print("\n")
print("==========================================")
print("STEP 10 — PIXEL 1 BY HAND")
print("==========================================")

print("\nPixel 1 centered values:")
print(pixel1)

print("\nEigenvector:")
print(e1)

print("\nCalculation:")

print(
    f"({pixel1[0]:.3f} * {e1[0]:.3f}) + "
    f"({pixel1[1]:.3f} * {e1[1]:.3f}) + "
    f"({pixel1[2]:.3f} * {e1[2]:.3f})"
)

print("\nPixel 1 PC1 value:")
print(pixel1_pc1)

print("\nNumPy PC1[0]:")
print(PC1[0])


# ============================================================
# STEP 11 — TURN PC1 BACK INTO A RASTER
# ============================================================
#
# PC1 currently looks like:
#
#
#       [p1]
#       [p2]
#       [p3]
#       [p4]
#       [p5]
#       [p6]
#       [p7]
#       [p8]
#       [p9]
#
#
# But remember where every pixel came from.
#
#
# So we can reconstruct:
#
#
#       [p1 p2 p3]
#
#       [p4 p5 p6]
#
#       [p7 p8 p9]
#
#
# In the real project we preserve the geographic
# coordinates/georeferencing information.
#
# ============================================================

pc1_raster = PC1.reshape(3, 3)


print("\n")
print("==========================================")
print("STEP 11 — PC1 RASTER")
print("==========================================")

print(pc1_raster)


# ============================================================
# STEP 12 — VISUALIZE IT
# ============================================================

fig, axes = plt.subplots(
    1,
    4,
    figsize=(14, 4)
)


datasets = [

    ("2022 FDL", fdl_2022),

    ("2023 FDL", fdl_2023),

    ("2024 FDL", fdl_2024),

    (
        f"PC1 Pattern\n"
        f"{explained_variance[0] * 100:.1f}% variance",
        pc1_raster
    )
]


for ax, (title, data) in zip(
    axes,
    datasets
):

    image = ax.imshow(data)

    ax.set_title(title)

    ax.set_xlabel("Column")
    ax.set_ylabel("Row")

    ax.set_xticks(range(3))
    ax.set_yticks(range(3))

    # Put the actual value inside each pixel.
    for row in range(3):

        for col in range(3):

            ax.text(
                col,
                row,
                f"{data[row, col]:.1f}",
                ha="center",
                va="center",
                fontsize=9
            )


plt.suptitle(
    "FDL Rasters → Linear Algebra → Recurring Snowmelt Pattern",
    fontsize=15,
    fontweight="bold"
)

plt.tight_layout()

plt.show()