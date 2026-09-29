from pyhdf.SD import SD, SDC
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
import re

# Convert Lat / lon to MODIS sinusoidal coordinates (MODIS sinusoidal is in meters)
def latlon_to_modis(lat, lon):
    R = 6371007.181
    
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)

    x = R * lon_rad * np.cos(lat_rad)
    y = R * lat_rad

    return x, y

# Get the tile bounds from the tile, this will get used to narrow down to our lat / lon point later
def get_tile_bounds(hdf):
    metadata = hdf.attributes()["StructMetadata.0"]

    upper_left = re.search(
        r"UpperLeftPointMtrs=\(([-\d.]+),([-\d.]+)\)",
        metadata
    )

    lower_right = re.search(
        r"LowerRightMtrs=\(([-\d.]+),([-\d.]+)\)",
        metadata
    )

    if upper_left is None or lower_right is None:
        raise ValueError("Could not find tile bounds in HDF metadata.")

    x_min = float(upper_left.group(1))
    y_max = float(upper_left.group(2))

    x_max = float(lower_right.group(1))
    y_min = float(lower_right.group(2))

    return x_min, y_max, x_max, y_min


def get_study_area(snow, row, col, size_km, pixel_width, pixel_height):
    size_m = size_km * 1000

    half_rows = int((size_m / 2) / pixel_height)
    half_cols = int((size_m / 2) / pixel_width)

    row_start = max(0, row - half_rows)
    row_end = min(snow.shape[0], row + half_rows + 1)

    col_start = max(0, col - half_cols)
    col_end = min(snow.shape[1], col + half_cols + 1)

    return snow[row_start:row_end, col_start:col_end]


download_folder = Path("downloads")

paths = sorted(download_folder.glob("*.hdf"))

# paths = ['downloads/MOD10A1.A2024092.h10v04.061.2024094223614.hdf', 'downloads/MOD10A1.A2024093.h10v04.061.2024095031013.hdf', 'downloads/MOD10A1.A2024094.h10v04.061.2024096042455.hdf', 'downloads/MOD10A1.A2024095.h10v04.061.2024100195429.hdf', 'downloads/MOD10A1.A2024096.h10v04.061.2024098035701.hdf', 'downloads/MOD10A1.A2024097.h10v04.061.2024099031255.hdf', 'downloads/MOD10A1.A2024098.h10v04.061.2024100032845.hdf', 'downloads/MOD10A1.A2024099.h10v04.061.2024101033853.hdf', 'downloads/MOD10A1.A2024100.h10v04.061.2024102033937.hdf', 'downloads/MOD10A1.A2024101.h10v04.061.2024103045147.hdf']
# print(paths[0])

# exit(0)

for path in paths:



    hdf = SD(str(path), SDC.READ)
    # print(hdf.datasets().keys()) #Find the keys, looking for NDSI_Snow_Cover

    snow_dataset = hdf.select('NDSI_Snow_Cover')
    snow = snow_dataset[:]

    # print(type(snow))
    # print(snow.shape)
    # print(snow.dtype)

    # values, counts = np.unique(snow, return_counts=True)

    # for value, count in zip(values, counts):
    #     if value <= 40:
    #         print(value, count)




    # The lat / lon of the location we are looking for
    lon = -116.61690081286483
    lat = 47.72847121284014
    
    x, y = latlon_to_modis(lat, lon)
    x_min, y_max, x_max, y_min = get_tile_bounds(hdf)

    #Rows and Cols of tile
    rows, cols = snow.shape

    #Find our point we are looking for (Reduce tile size to our area)
    pixel_width = (x_max - x_min) / cols
    pixel_height = (y_max - y_min) / rows

    # print("Pixel width:", pixel_width)
    # print("Pixel height:", pixel_height)





    row = int((y_max - y) / pixel_height)
    col = int((x - x_min) / pixel_width)

    if 0 <= row < rows and 0 <= col < cols:
        print("Point is inside this MODIS tile.")
        print("NDSI value:", snow[row, col])
    else:
        print("Point is outside this MODIS tile.")

    # print("Row:", row)
    # print("Column:", col)




    area = snow[
        row - 3:row + 4,
        col - 3:col + 4
    ]

    # 250 means clouds
    print(area)

    # print(path)
    print("NDSI:", snow[row, col])


    mountain_area = get_study_area(
        snow,
        row,
        col,
        size_km=40,
        pixel_width=pixel_width,
        pixel_height=pixel_height
    )

    print("\nFile:", path)
    print("Study area shape:", mountain_area.shape)

    values, counts = np.unique(
        mountain_area,
        return_counts=True
    )

    for value, count in zip(values, counts):
        print(value, count)

    plt.imshow(mountain_area)
    plt.colorbar(label="NDSI Snow Cover")
    plt.title(path.name)
    plt.xlabel("Pixel Column")
    plt.ylabel("Pixel Row")
    plt.show()
    
    ndsi_area = mountain_area.astype(float)

    # Anything above 100 is a special MODIS code, not an NDSI value
    ndsi_area[ndsi_area > 100] = np.nan

    plt.imshow(
        ndsi_area,
        vmin=0,
        vmax=100,
        interpolation="nearest"
    )
    plt.colorbar(label="NDSI Snow Cover")
    plt.title(path.name + " - NDSI Only")
    plt.xlabel("Pixel Column")
    plt.ylabel("Pixel Row")
    plt.show()


    hdf.end()

