# client

The front end. **Not started**; the stack is undecided (D09).

Planned role: a map of Idaho where the user picks a watershed (from the map or a list), a sensor (MODIS or VIIRS) and a time period, then views the recurring melt pattern (PC1) over the map and downloads it as a GeoTIFF. All computation happens in `api/`; the client only calls it.

Display maps in Web Mercator (reprojected by the api, nearest neighbor, display only). Darker = earlier melt, lighter = later; values are relative, not dates.
