import json
import requests
from requests.auth import HTTPBasicAuth
import os
from numba import jit
import tempfile
# pip install netCDF4
from netCDF4 import Dataset
import numpy as np
import fiona
from zipfile import ZipFile
import time
import xmltodict

from General_modules.module_logs import log_task_file
from General_modules.module_GeoServer_access import init_Params, get_url_user_pwd_geoserver, checkWorkspace, updateStyles, uploadNetCDF
from General_modules.module_access_external import download_FILE
from General_modules import global_settings
from General_modules.module_access_external import request_Data_External_Source

from WebEMEP.GeoserverProxy import get_Dict_EMEP
from WebEMEP.depositions import create_new_depositions_rasters, add_pollutants


headers_xml = {'Content-Type': 'application/xml'}
headers_xml_accept = {'accept': 'application/xml'}
gs_url, gs_rest_url, user, pwd = get_url_user_pwd_geoserver()
tmp_dir = global_settings.PATH_TMP_FILES
URL_BASE = global_settings.EMEP_URL_BASE


def netcdf(filename, dict_EMEP, resolution, polygon_path, mask, directory):
    """
        Creates a new NetCDF File where the location values corresponds only to the limits of the polygon (In this case is Continental Portugal)
    """

    with Dataset("%s/old_NC/%s"%(directory, filename)) as src_netcdf, \
        Dataset("%s/%s"%(directory, filename), "w", format="NETCDF4") as dst_netcdf, \
            fiona.open(polygon_path) as polygon_shape:
    
        dst_netcdf.setncatts(src_netcdf.__dict__)

        lats = src_netcdf["lat"][:]
        lons = src_netcdf["lon"][:]
        times_lenght = len(src_netcdf['time'][:])
        _limits = polygon_shape.bounds
        limits = {}
        limits['lat'] = [_limits[1]-0.1, _limits[3] + 0.2]
        limits['lon'] = [_limits[0]-0.1, _limits[2] + 0.1]

        if limits['lat'][0] < lats[0]:
            limits['lat'][0] = lats[0]

        if limits['lat'][1] > lats[-1]:
            limits['lat'][1] = lats[-1] + 0.1

        if limits['lon'][0] < lons[0]:
            limits['lon'][0] = lons[0]

        if limits['lon'][1] > lons[-1]:
            limits['lon'][1] = lons[-1] + 0.1

        # latitude lower and upper index
        latli = np.argmin( np.abs( lats - limits["lat"][0]))
        latui = np.argmin( np.abs( lats - limits["lat"][1]))


        # longitude lower and upper index
        lonli = np.argmin( np.abs( lons - limits["lon"][0]))
        lonui = np.argmin( np.abs( lons - limits["lon"][1]))

        # Latitude from 36.25 to 42.25 and longitude from -10.65 to -6.15. ( Retangulo de portugal Continental) lat 54 pontos long 37 pontos
        for name, dimension in src_netcdf.dimensions.items():
            if name == 'lon':
                dim = (limits['lon'][1] - limits['lon'][0]) / 0.1
                dim = int(round(dim))
            elif name == 'lat':
                dim = (limits['lat'][1] - limits['lat'][0]) / 0.1
                dim = int(round(dim))
            else:
                dim = len(dimension) if not dimension.isunlimited() else None
            dst_netcdf.createDimension(name, dim)

        for name, variable in src_netcdf.variables.items():
            x = dst_netcdf.createVariable(name, variable.datatype, variable.dimensions)
            dst_netcdf[name].setncatts(src_netcdf[name].__dict__)
            if name == 'lat' or name == 'lon':
                vals = src_netcdf[name][:]

                # latitude/longitude lower and upper index
                limli = np.argmin( np.abs( vals - limits[name][0]))
                limui = np.argmin( np.abs( vals - limits[name][1]))

                dst_netcdf[name][:] = src_netcdf[name][limli:limui]
            elif name == 'time':
                dst_netcdf[name][:] = src_netcdf[name][:]
            else:
                aux_dst = src_netcdf[name][:, latli:latui, lonli:lonui]
                if not mask is None:
                    for _time in range(times_lenght):
                        dst_netcdf[name][_time, :] = np.ma.masked_where(~mask, aux_dst[_time, :])
                else:
                    dst_netcdf[name][:] = aux_dst

                _max = float(dst_netcdf[name][:].max())
                _min = float(dst_netcdf[name][:].min())
                
                if dict_EMEP['max_min'][resolution][name] == None:
                    dict_EMEP['max_min'][resolution][name] = {}
                    dict_EMEP['max_min'][resolution][name]['max'] = _max
                    dict_EMEP['max_min'][resolution][name]['min'] = _min
                else:
                    if _max > dict_EMEP['max_min'][resolution][name]['max']:
                        dict_EMEP['max_min'][resolution][name]['max'] = _max
                    
                    if _min < dict_EMEP['max_min'][resolution][name]['min']:
                        dict_EMEP['max_min'][resolution][name]['min'] = _min

        if mask is not None:
            create_new_depositions_rasters(dst_netcdf, dict_EMEP, resolution)

    
    ZipFile("%s/%s"%(directory, filename.replace('.nc', '.zip')),mode='w').write("%s/%s"%(directory, filename))


def uploadGeoserver(filename, resolution, year, directory):
    """
        Upload the file to the geoserver, by verifying the existence of the workspace resolution-year.
        And after the upload of the file, define the style for all the layers generate from teh file
    """
    
    with open("%s/%s"%(directory, filename.replace('.nc', '.zip')), 'rb') as fileobj:
        workspace = "%s-%s"%(resolution, year)

        if checkWorkspace(workspace, gs_rest_url, user, pwd):
            if uploadNetCDF(workspace, fileobj, gs_rest_url, user, pwd):
                updateStyles(workspace, global_settings.STYLE_NAME_GENERAL, gs_rest_url, user, pwd, global_settings.PATH_EMEP_STYLE)
                os.remove("%s/%s"%(directory, filename.replace('.nc', '.zip')))
                os.remove("%s/%s"%(directory, filename))
                os.remove("%s/old_NC/%s"%(directory, filename))
                return

        log_task_file("It was impossible to upload the file to geoserver.\nThe path file is %s"%("%s/%s"%(directory, filename.replace('.nc', '.zip'))))


def uploadEMEPData(year, resolution, dict_EMEP, datasets, mask, urlEmep, directory, polygon_path):
    """
        Upload EMEP data to the GeoServer

        Steps:
            - Download the file from EMEP site;
            - Cut the data to only contain data from Portugal;
            - Upload the data to the GeoServer

    """
    filename = download_FILE(urlEmep+datasets[resolution][year]['EMEPSite'], "%s-%s"%(resolution, year), directory+ "/old_NC")
    netcdf(filename, dict_EMEP, resolution, polygon_path, mask, directory)
    uploadGeoserver(filename, resolution, year, directory)
    log_task_file("Upload to Geoserver %s-%s"%(resolution, year))


def UploadEMEPDatasets(dict_EMEP):
    """
    Upload all the EMEP data to the Geoserver
    """
    with tempfile.TemporaryDirectory(dir=tmp_dir) as directory:
        os.mkdir(directory + '/old_NC')

        datasets = dict_EMEP['datasets']
        urlEmep = URL_BASE + dict_EMEP['services']['httpserver']
        polygon_path = get_shapefile_format(directory)
        mask = create_mask(dict_EMEP, directory, polygon_path, urlEmep)

        if mask == []:
            log_task_file("ERROR: Mask is empty!!")
            return

        for resolution in datasets:
            
            ###############################################################################################################################################
            # It is not downloading the hourly and daily resolution !!!!!!!!!!!!!!!!!!!
            if resolution == 'hour' or resolution == 'day':
                continue
            
            ##################################################################################################################################################

            for year in datasets[resolution]:
                uploadEMEPData(year, resolution, dict_EMEP, datasets, mask, urlEmep, directory, polygon_path)

        save_EMEP_dict(dict_EMEP)
        

def UploadEMEPDatasets_RecentYear(dict_EMEP):
    """
        Upload all the EMEP data from the recent year to the Geoserver (there is an error on the geoserver that the recent year is represent with a date from 1900... )
    """
    with tempfile.TemporaryDirectory(dir=tmp_dir) as directory:
        os.mkdir(directory + '/old_NC')

        datasets = dict_EMEP['datasets']
        urlEmep = URL_BASE + dict_EMEP['services']['httpserver']
        polygon_path = get_shapefile_format(directory)
        mask = create_mask(dict_EMEP, directory, polygon_path, urlEmep)

        if mask == []:
            log_task_file("ERROR: Mask is empty!!")
            return

        for resolution in datasets:
            
            ###############################################################################################################################################
            # It is not downloading the hourly and daily resolution !!!!!!!!!!!!!!!!!!!
            if resolution == 'hour' or resolution == 'day':
                continue
            
            ##################################################################################################################################################
            year = list(datasets[resolution].keys())[0]
            uploadEMEPData(year, resolution, dict_EMEP, datasets, mask, urlEmep, directory, polygon_path)

        save_EMEP_dict(dict_EMEP)


def download_Catalog_Datasets(url):
    """
        Download the catalog from the emep site
    """
    r = requests.get(URL_BASE + url, headers= headers_xml_accept)
    if r.status_code == 200:
        data = xmltodict.parse(r.content)
        return data
    return None


def save_EMEP_dict(dict_EMEP):
    with open(global_settings.PATH_EMEP_DICT_JSON, "w") as outfile:
        json.dump(dict_EMEP, outfile, indent=4) #, sort_keys=True)
        log_task_file("Save the EMEP dictionary, path: %s"%(global_settings.PATH_EMEP_DICT_JSON))


def retrieveGases(dataset):
    """
        For a given dataset it retrieves the gases
    """
    layers = dataset['WMS_Capabilities']['Capability']['Layer']['Layer']['Layer']
    
    gases = []
    if isinstance(layers, dict):
        gases.append(layers['Name'])
    else:
        for layer in layers:
            gases.append(layer['Name'])
    
    return gases


def checkDate(date, year):
    """
        For a given date, remove the year
    """
    if '-01-01T00:00:00.000Z' in date:
        date = '-01-01T00:00:00.000Z'
    else:
        date = date.split(year)[1]
    return date


def date_check(resolution):
    """
        Specific string for a given temporal resolution where it is different between a leap year and a no leap year
    """

    if resolution == 'year':
        return '-07'
    elif resolution == 'month':
        return '-02'
    elif resolution == 'day' or resolution == 'hour':
        return '-02-29'
    

def appendDate(dates, dates_02, date, year, resolution):
    """
        Create 2 lists:
            dates - general list that is common to all the years
            dates_02 - list that have specifics dates that correspond to the year being leap or no leap
    """
    auxDate = checkDate(date, year)
    check = date_check(resolution)
    if check in auxDate:
        if not auxDate in dates_02:
            dates_02.append(auxDate)
    else:
        if not auxDate in dates:
            dates.append(auxDate)


def retrieveDates(dataset, year, dates, dates_02, resolution):
    """
        For a given dataset, get all dates without the year
    """
    layers = dataset['WMS_Capabilities']['Capability']['Layer']['Layer']['Layer']

    if isinstance(layers, dict):
        for date in layers['Dimension']["#text"].split(','):
            appendDate(dates, dates_02, date, year, resolution)
    else:
        for layer in layers:
            for date in layer['Dimension']["#text"].split(','):
                appendDate(dates, dates_02, date, year, resolution)    
    return dates


def stylesretrieveLayer(layer, styles):
    for style in layer['Style']:
        if not style['Name'] in styles:
            styles.append(style['Name'])


def retrieveStyles(dataset):
    """
        From the data set get all the default styles
    """
    layers = dataset['WMS_Capabilities']['Capability']['Layer']['Layer']['Layer']

    styles = []
    if isinstance(layers, dict):
        stylesretrieveLayer(layers, styles)
    else:
        for layer in layers:
            stylesretrieveLayer(layer, styles)
    
    return styles


def EMEP_Create_dict(actual_year, old_year):
    """
    Convert the EMEP Catalog to a dictionary more simpler
    """
    resolutions =['year', 'month', 'hour', 'day']

    DATASET_QUERY = '?service=WMS&version=1.3.0&request=GetCapabilities'

    Catalog = download_Catalog_Datasets(global_settings.CATALOG_EMEP_URL.replace("XXXX", actual_year))
    old_Catalog = download_Catalog_Datasets(global_settings.CATALOG_EMEP_URL.replace("XXXX", old_year))

    dict_EMEP = {}
    dict_EMEP['services'] = {}
    dict_EMEP['resolutions'] = resolutions
    dict_EMEP['datasets'] = {}
    dict_EMEP['ListGases'] = {}
    dict_EMEP['ListDates'] = {}
    dict_EMEP['styles'] = []

    dict_EMEP['LimitsBounds'] = {}
    dict_EMEP['LimitsBounds']['west'] = -10.65
    dict_EMEP['LimitsBounds']['east'] = -6.15
    dict_EMEP['LimitsBounds']['south'] = 36.25
    dict_EMEP['LimitsBounds']['north'] = 42.25

    for res in resolutions:
        dict_EMEP['datasets'][res] = {}

    for res in resolutions:
        dict_EMEP['ListGases'][res] = []
        dict_EMEP['ListDates'][res] = {}
        dict_EMEP['ListDates'][res]['General'] = []
        dict_EMEP['ListDates'][res]['Leap'] = []
        dict_EMEP['ListDates'][res]['NoLeap'] = []

    catalog = Catalog['catalog']

    for serv in catalog['service']['service']:
        dict_EMEP['services'][serv['@serviceType'].lower()] = serv['@base']
    
    recent_datasets = catalog['dataset']['dataset']

    old_datasets = old_Catalog['catalog']['dataset']['dataset']

    datasets = recent_datasets + old_datasets
    
    for dataset in datasets:
        for res in resolutions:
            if res in dataset['@name']:
                resolution = res
                break
        meteo_year = dataset['@name'].split(resolution+'.')[1].split('met')[0]

        emissions_year =  dataset['@name'].split(resolution+'.')[1].split('met_')[1].split('emis')[0]

        if emissions_year != meteo_year:
            continue

        year = meteo_year

        if year not in dict_EMEP['datasets'][resolution].keys():
            dict_EMEP['datasets'][resolution][year] = {}
            dict_EMEP['datasets'][resolution][year]['EMEPSite'] = dataset['@urlPath']
            dict_EMEP['datasets'][resolution][year]['Geoserver'] = "%s-%s"%(resolution,year)

            infodataset =download_Catalog_Datasets(dict_EMEP['services']['wms']+dataset['@urlPath'] + DATASET_QUERY)

            ListGases = dict_EMEP['ListGases'][resolution]

            gases = ListGases + list(set(retrieveGases(infodataset))-set(ListGases))

            dict_EMEP['ListGases'][resolution] = gases

            ListDatesNoLeap = len(dict_EMEP['ListDates'][resolution]['NoLeap'])

            ListDatesLeap = len(dict_EMEP['ListDates'][resolution]['Leap'])

            if ListDatesLeap == 0 or ListDatesNoLeap == 0 or ListDatesLeap == 0:
                if dict_EMEP['styles'] == []:
                    dict_EMEP['styles'] = retrieveStyles(infodataset)

                if ListDatesNoLeap == 0:
                    if int(year)%4 != 0:
                        dates = []
                        dates_02 = []
                        dates = retrieveDates(infodataset, year, dates, dates_02, resolution)
                        dict_EMEP['ListDates'][resolution]['NoLeap'] = dates_02

                        if len(dict_EMEP['ListDates'][res]['General']) == 0:
                            dict_EMEP['ListDates'][res]['General'] = dates

                if ListDatesLeap == 0:
                    if int(year)%4 == 0:
                        dates = []
                        dates_02 = []
                        dates = retrieveDates(infodataset, year, dates, dates_02, resolution)
                        dict_EMEP['ListDates'][resolution]['Leap'] = dates_02

                        if len(dict_EMEP['ListDates'][res]['General']) == 0:
                            dict_EMEP['ListDates'][res]['General'] = dates

    dict_EMEP['max_min'] = {}
    for res in resolutions:
        dict_EMEP['max_min'][res] = {}
        dict_EMEP['ListGases'][res] += add_pollutants()
        for gas in dict_EMEP['ListGases'][res]:
            dict_EMEP['max_min'][res][gas] = None
            if gas == 'TDEP_N_critical_load':
                dict_EMEP['max_min'][res][gas] = {}
                dict_EMEP['max_min'][res][gas]['max'] = 2
                dict_EMEP['max_min'][res][gas]['min'] = 0

    save_EMEP_dict(dict_EMEP)
    return dict_EMEP


def get_shapefile_format(directory):
    """ 
        Get from geoserver a shapefile
    """
    params = init_Params("WFS", "2.0.0", "GetFeature")
    params['typeName'] = global_settings.BOUND_EMEP_LAYER_GEOSERVER_NAME
    params['outputFormat'] = "shape-zip" 
    params['srsName'] = 'EPSG:4326'

    response = request_Data_External_Source('get', gs_url, params=params, user=user, pwd=pwd, timer=False, authentication=True)

    filename = response.headers['Content-Disposition'].split('filename=')[1]

    # with open(global_settings.PATH_TMP_FILES + '/' + filename, "wb") as f:
    with open(directory + '/' + filename, "wb") as f:
        f.write(response.content)
    
    result_filename = directory + '/' + filename.replace(".zip", '.shp')
    # result_filename = global_settings.PATH_TMP_FILES + '/' + filename.replace(".zip", '.shp')

    with ZipFile(directory + '/' + filename, 'r') as zipObj:
        zipObj.extractall(directory + '/')

    return result_filename


# https://stackoverflow.com/questions/60233081/extract-data-from-netcdf-file-contained-within-a-shapefiles-boundaries
# https://www.dgp.toronto.edu/~mac/e-stuff/point_in_polygon.py

@jit(nopython=True, nogil=True)
def is_left(_lon, _lat, shp_lon_i_0, shp_lat_i_0, shp_lon_i_1, shp_lat_i_1):
    """
    Input: 3 points: P0 =[_lon, _lat], P1 = [shp_lon_i_0, shp_lat_i_0], P2 = [shp_lon_i_1, shp_lat_i_1]
    Check if a point P0 is Left|On|Right of an infinite line (P1, P2)
    Return: >0 for P0 left of the line through P1 and P2, 
            0 for P0 on the line,
            <0 for P0 right of the line
    """

    return (shp_lon_i_1-shp_lon_i_0) * (_lat-shp_lat_i_0) - (_lon-shp_lon_i_0) * (shp_lat_i_1-shp_lat_i_0)


@jit(nopython=True, nogil=True)
def is_inside(_lon, _lat, shp_lon, shp_lat, shp_size):
    """
    Given location (_lon,_lat) and set of line segments (shp_lon, shp_lat), determine
    whether (_lon,_lat) is inside polygon.
    """
    wn = 0
    for i in range(shp_size-1):
        # Calculate winding number
        if shp_lat[i] <= _lat:
            if shp_lat[i+1] > _lat:
                if (is_left(_lon, _lat, shp_lon[i], shp_lat[i], shp_lon[i+1], shp_lat[i+1]) > 0):
                    wn += 1
        else:
            if shp_lat[i+1] <= _lat:
                if (is_left(_lon, _lat, shp_lon[i], shp_lat[i], shp_lon[i+1], shp_lat[i+1]) < 0):
                    wn -= 1

    if wn == 0:
        return False
    else:
        return True



@jit(nopython=True, nogil=True)
def calc_mask(mask, lon, lat, shp_lon, shp_lat):
    """
    Calculate mask where the points are inside of the polygon
    """
    for j in range(lat.size):    
        for i in range(lon.size):
            if is_inside(lon[i], lat[j], shp_lon, shp_lat, shp_lon.size):
                mask[j,i] = True


def create_mask(dict_EMEP, directory, polygon_path, urlEmep):
    """
        For a given shapefile, it will create a mask array that makes easier to cut the netcdfs to contain only the only useful informations
    """
    mask = []
    
    mask_path = directory + '/mask.npy'

    # if not os.path.exists(mask_path):
    resolution = list(dict_EMEP['datasets'].keys())[0]
    year = list(dict_EMEP['datasets'][resolution].keys())[0]
    _time = 0
    filename = download_FILE(urlEmep +dict_EMEP['datasets'][resolution][year]['EMEPSite'], resolution +  '-' + year, directory + "/old_NC")
    
    if filename is not None:
        netcdf(filename, dict_EMEP, resolution, polygon_path, None, directory)
            
        with Dataset("%s/%s"%(directory,filename)) as nc, fiona.open(polygon_path) as fc:
            nc_lon = nc.variables['lon'][:]
            nc_lat = nc.variables['lat'][:]
            nc_gas  = nc.variables['SURF_ugN_NOX'][_time,:,:]

            feature = next(iter(fc))

            coords = feature['geometry']['coordinates'][0]
            shp_lon = np.array(coords)[:,0]
            shp_lat = np.array(coords)[:,1]

            mask = np.zeros_like(nc_gas, dtype=bool)
            
            start = time.time()
            calc_mask(mask, nc_lon, nc_lat, shp_lon, shp_lat)
            end = time.time()

            log_task_file("DONE! Mask array is compute: %s time: %f"%(mask_path, (end - start)))
            
            mask.dump(mask_path)
        # else:
        #     mask = np.load(mask_path, allow_pickle=True)
        
    return mask


if __name__ == "__main__":
    # dict_EMEP = EMEP_Create_dict("2020", "2019")
    # print(json.dumps(dict_EMEP, indent=2))

    directory = global_settings.PATH_TMP_FILES
    dict_EMEP = get_Dict_EMEP()
    filename = 'EMEP01_rv4_35_year.2018met_2018emis.nc'
    polygon_path = '/home/fmmf/Desktop/TESE/my_geonode/geonode_tmp/Poligonos_mar_buffer.shp'
    # mask = np.load(directory + '/mask.npy', allow_pickle=True)

    # UploadEMEPDatasets(dict_EMEP)

    # filename = download_FILE(dict_EMEP['services']['httpserver']+dict_EMEP['datasets']['year']['2018']['EMEPSite'], "year-2018", directory + '/old_NC')
    
    # print(filename)

    # uploadNetCDF("year-2018")

    # netcdf(filename, dict_EMEP, 'year', polygon_path, mask, directory)

    # create_new_depositions_rasters(filename, dict_EMEP, 'year', directory)

    
    # filename = "EMEP01_L20EC_rv4_33_year.2017met_2017emis.nc"#"EMEP01_L20EC_rv4_33_year.2018met_2017emis.nc" 
    # netcdf(filename, dict_EMEP, 'year', )
    # uploadGeoserver(filename,'year', '2018')


    # filename = download(dict_EMEP['services']['httpserver']+dict_EMEP['datasets']['month']['2017']['EMEPSite'])
    # # print(filename)
    # # filename = "EMEP01_L20EC_rv4_33_month.2017met_2017emis.nc"
    # netcdf(filename)

    # filename = download(dict_EMEP['services']['httpserver']+dict_EMEP['datasets']['day']['2018']['EMEPSite'])
    # print(filename)