import earthaccess
import json

auth = earthaccess.login(persist=True)

#Search for data products related to what I want
# results = earthaccess.search_datasets(
#     keyword="L3m ocean color modis aqua chlorophyll",
#     instrument="MODIS"
# )

tspan = ('2024-01-01', '2024-01-10')
bbox = (-93.51893, 9.67272, -92.88085, 10.63788)


lon = -116.61690081286483
lat = 47.72847121284014
meters = 3000
# peak_next_to_fernan_saddle = ((lon, lat, meters))
peak_next_to_fernan_saddle = ((lon, lat))

results = earthaccess.search_data(
    short_name='MOD10A1',
    temporal=tspan,
    point=peak_next_to_fernan_saddle
)

# print(len(results))
# print(results[0])

# data_links = [{"links": i.data_links(), "size (MB)": i.size} for i in results]
# print(json.dumps(data_links, indent=4))

paths = earthaccess.download(results, "downloads")
print(paths)

# ['downloads/MOD10A1.A2024092.h10v04.061.2024094223614.hdf', 'downloads/MOD10A1.A2024093.h10v04.061.2024095031013.hdf', 'downloads/MOD10A1.A2024094.h10v04.061.2024096042455.hdf', 'downloads/MOD10A1.A2024095.h10v04.061.2024100195429.hdf', 'downloads/MOD10A1.A2024096.h10v04.061.2024098035701.hdf', 'downloads/MOD10A1.A2024097.h10v04.061.2024099031255.hdf', 'downloads/MOD10A1.A2024098.h10v04.061.2024100032845.hdf', 'downloads/MOD10A1.A2024099.h10v04.061.2024101033853.hdf', 'downloads/MOD10A1.A2024100.h10v04.061.2024102033937.hdf', 'downloads/MOD10A1.A2024101.h10v04.061.2024103045147.hdf']