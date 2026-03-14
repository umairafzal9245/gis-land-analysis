import geopandas as gpd
import pyogrio

GDB_PATH = "data/AI _Test.gdb"
layer_name = "SubdivisionParcelBoundary"
gdf = gpd.read_file(GDB_PATH, layer=layer_name)

print("--- DETAILSLANDUSE ---")
print(gdf['DETAILSLANDUSE'].value_counts())

print("\n--- SUBTYPE ---")
print(gdf['SUBTYPE'].value_counts())

print("\n--- MAINLANDUSE ---")
print(gdf['MAINLANDUSE'].value_counts())

print("\n--- PARCELSTATUS ---")
if 'PARCELSTATUS' in gdf.columns:
    print(gdf['PARCELSTATUS'].value_counts())
else:
    print("PARCELSTATUS column not found")
