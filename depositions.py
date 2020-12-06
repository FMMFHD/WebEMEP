from netCDF4 import Dataset, num2date # pip install netCDF4


new_rasters = {
    'DDEP_N': ['DDEP_RDN_m2Grid', 'DDEP_OXN_m2Grid'],
    'WDEP_N': ['WDEP_OXN', 'WDEP_RDN'],
    'TDEP_N': ['WDEP_N', 'DDEP_N'],
    'TDEP_RDN': ['WDEP_RDN', 'DDEP_RDN_m2Grid'],
    'TDEP_OXN': ['DDEP_OXN_m2Grid', 'WDEP_OXN'],
    'TDEP_SOX': ['DDEP_SOX_m2Grid', 'WDEP_SOX'],
    'TDEP_N_critical_load': [],
}

def add_pollutants():
    """
        Return a list of new names for pollutants
    """
    return list(new_rasters.keys())


def create_new_depositions_rasters(src_netcdf, dict_EMEP, resolution):
    """
        Create new rasters for the depositions: \n
            - DDEP_RDN_m2Grid + DDEP_OXN_m2Grid = DDEP_N
            - WDEP_OXN + WDEP_RDN = WDEP_N
            - WDEP_N + DDEP_N = TDEP_N
            - WDEP_RDN + DDEP_RDN_m2Grid = TDEP_RDN
            - DDEP_OXN_m2Grid + WDEP_OXN = TDEP_OXN
            - DDEP_SOX_m2Grid + WDEP_SOX = TDEP_SOX
    """
    
    for new_raster in new_rasters:
        item_pollutant = None

        if new_raster == 'TDEP_N_critical_load':
            continue

        for item in src_netcdf.variables.items():
            if item[0] == new_rasters[new_raster][0]:
                item_pollutant = item
                break

        x = src_netcdf.createVariable(new_raster, item_pollutant[1].datatype, item_pollutant[1].dimensions)
        src_netcdf[new_raster].setncatts(src_netcdf[item_pollutant[0]].__dict__)
        src_netcdf[new_raster].setncattr('long_name', new_raster)

        src_netcdf[new_raster][:] = src_netcdf[new_rasters[new_raster][0]][:] + src_netcdf[new_rasters[new_raster][1]][:]

        _max = float(src_netcdf[new_raster][:].max())
        _min = float(src_netcdf[new_raster][:].min())
        
        if dict_EMEP['max_min'][resolution][new_raster] == None:
            dict_EMEP['max_min'][resolution][new_raster] = {}
            dict_EMEP['max_min'][resolution][new_raster]['max'] = _max
            dict_EMEP['max_min'][resolution][new_raster]['min'] = _min
        else:
            if _max > dict_EMEP['max_min'][resolution][new_raster]['max']:
                dict_EMEP['max_min'][resolution][new_raster]['max'] = _max
            
            if _min < dict_EMEP['max_min'][resolution][new_raster]['min']:
                dict_EMEP['max_min'][resolution][new_raster]['min'] = _min