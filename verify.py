import pyogrio
import geopandas as gpd
gdf = gpd.read_file(r'data/AI Test.gdb', layer='SubDivisionParcelBoundary')
print(gdf['SUBTYPE'].dtype)
print(gdf['SUBTYPE'].value_counts().head(20))