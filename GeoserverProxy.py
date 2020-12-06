import json
import urllib
import requests
from requests.auth import HTTPBasicAuth
import base64
# parse() xml->dict |||| unparse() dict->xml
import xmltodict
from collections import OrderedDict

from General_modules.module_GeoServer_access import get_url_user_pwd_geoserver, save_file_locally, init_Params
from General_modules.module_logs import log_task_file, log_error_file
from General_modules.module_access_external import request_Data_External_Source
import General_modules.global_settings as global_settings


gs_url, gs_rest_url, user, pwd = get_url_user_pwd_geoserver()
headers_xml_accept = {'accept': 'application/xml'}
headers_image_accept = {'accept': 'image/png'}
headers_json_accept = {'accept': 'application/json'}


def get_Dict_EMEP():
    """
        Copy the information from the EMEP dictionary file to a variable
    """

    try:
        with open(global_settings.PATH_EMEP_DICT_JSON, 'r') as json_file:
            data = json.load(json_file)
            return data
    except:
        return None


def createTimeDimension(year, listDates):
    """Create a string that contains all the possible datas for a layer"""
    dates = ''

    for date in listDates['General']:
        if '-01-01T00:00:00.000Z' in date:
            dates += str(int(year) + 1) + date + ','
        else:
            dates += year + date + ','

    if int(year) % 4 == 0:
        listLeap_NoLeap = listDates['Leap']
    else:
        listLeap_NoLeap = listDates['NoLeap']

    for date in listLeap_NoLeap:
        dates += year + date + ','

    return dates[:-1]


def checkLayer(layer, Geo_namespace, resolution, default_year, version):
    """Verify the name of the layer and its time dimension"""
    dict_EMEP = get_Dict_EMEP()
    if Geo_namespace in layer['Name']:
        layer['Name'] = layer['Name'].split(Geo_namespace + ':')[1] # ou layer['Title']

        if version == '1.1.1':
            key_time = 'Extent'
        else:
            key_time = "Dimension"

        if key_time in layer.keys():
            listDates = dict_EMEP['ListDates'][resolution]
            for year in dict_EMEP['datasets'][resolution]:
                if year != default_year:
                    layer[key_time]['#text'] += ',' + createTimeDimension(year, listDates)
        else:
            exceptions_Content(layer, resolution, default_year, dict_EMEP, key_time) 


def exceptions_Content(layer, resolution, default_year, dict_EMEP, key_time):
    """
        Add time dimension if layer is TDEP_N_critical_load
    """
    if layer['Name'] == 'TDEP_N_critical_load':
        listDates = dict_EMEP['ListDates'][resolution]
        layer[key_time] = OrderedDict()
        layer[key_time]['@name'] = 'time'
        layer[key_time]['@default'] = '2018-07-02T12:00:00Z'
        layer[key_time]['@units'] = 'ISO8601'
        layer[key_time]['#text'] = '2018-07-02T12:00:00.000Z'
        for year in dict_EMEP['datasets'][resolution]:
            if year != default_year:
                layer[key_time]['#text'] += ',' + createTimeDimension(year, listDates)

        

def Content_Capabilities(xmlcontent, Geo_namespace, resolution, default_year, version):
    """ Check the content of the response of the GetCapabilities
        Changes on each Layer:
            - Removing "resolution-year:"
            - Adding the time dimensions respecting the resolution
    """
    content = xmltodict.parse(xmlcontent)
    
    if version == '1.1.1': 
        aux_content = content['WMT_MS_Capabilities']
    else:
        aux_content = content['WMS_Capabilities']

    General_layer = aux_content['Capability']['Layer']

    if 'Layer' in General_layer.keys():
        Layers = aux_content['Capability']['Layer']['Layer']
        if isinstance(Layers, list):
            for layer in Layers:
                checkLayer(layer, Geo_namespace, resolution, default_year, version)
        else:
            checkLayer(Layers, Geo_namespace, resolution, default_year, version)
    
    return xmltodict.unparse(content)


def changeLayerName(layers, Geo_namespace):
    str_layers = ''
    for layer in layers:
        str_layers += Geo_namespace + ':' + layer + ','
    return str_layers[:-1]


def redirect(rec_params, resolution):
    """
        Change the parameters that are not common between the information that came from the view and the information that has to send to the rest geoserver to get the same thing
    """

    dict_EMEP = get_Dict_EMEP()
    if 'time' in rec_params.keys():
        year = rec_params['time'].split('-')[0]
        Geo_namespace = dict_EMEP['datasets'][resolution][year]['Geoserver']
    else:
        default_year = list(dict_EMEP['datasets'][resolution].keys())[0]
        Geo_namespace = dict_EMEP['datasets'][resolution][default_year]['Geoserver']

    rec_params['layers'] = changeLayerName(rec_params['layers'].split(','), Geo_namespace)

    if 'query_layers' in rec_params.keys():
        rec_params['query_layers'] = changeLayerName(rec_params['query_layers'].split(','), Geo_namespace)

    return Geo_namespace


def changeContentNamespace(xmlcontent, Geo_namespace):
    # content = xmltodict.parse(xmlcontent)
    # gml = content["wfs:FeatureCollection"]["gml:featureMember"]
    # if isinstance(gml, list):
    #     pass
    # else:
    #     new_gml = {}
    #     old_key = list(gml.keys())[0]
    #     new_key = old_key.split(Geo_namespace + ':')[1]
    #     new_gml[new_key] = {}
    #     for key in gml[old_key].keys():
    #         if key == old_key:
    #             new_gml[new_key][new_key] = gml[old_key][key]
    #         else:
    #             new_gml[new_key][key] = gml[old_key][key]
    #     content["wfs:FeatureCollection"]["gml:featureMember"] = new_gml
    return json.dumps(xmlcontent)


def Geo_GetCapabilities(rec_params, resolution):
    """Corresponds to the WMS service: Get Capabilities"""
    dict_EMEP = get_Dict_EMEP()
    default_year = list(dict_EMEP['datasets'][resolution].keys())[0]
    Geo_namespace = dict_EMEP['datasets'][resolution][default_year]['Geoserver']
    rec_params['namespace'] = Geo_namespace
    
    resp = request_Data_External_Source('get', gs_url, params=rec_params, headers=headers_xml_accept, user=user, pwd=pwd, timer=False, authentication=True)
    if resp is None:
        return [None, None]
    content = Content_Capabilities(resp.content, Geo_namespace, resolution, default_year, rec_params['version'])
    return [resp.headers['Content-Type'], content]


def Geo_GetMap(rec_params, resolution):
    """Corresponds to the WMS service: Get Map"""
    add_env_values(rec_params, resolution, rec_params['layers'])
    redirect(rec_params, resolution)

    resp = request_Data_External_Source('get', gs_url, params=rec_params, headers=headers_image_accept, user=user, pwd=pwd, timer=False, authentication=True)
    if resp is None:
        return [None, None]
    return [resp.headers['Content-Type'], resp.content]


def Geo_GetFeatureInfo(rec_params, resolution, bool_redirect):
    """Corresponds to the WMS service: Get GetFeatureInfo"""
    if bool_redirect:
        redirect(rec_params, resolution)
        
    rec_params['info_format'] = 'application/json'
    
    resp = request_Data_External_Source('get', gs_url, params=rec_params, user=user, pwd=pwd, timer=False, authentication=True)
    if resp is None:
        return [None, None]


    try:
        response_json = resp.json()
    except:
        response_json = None

    content = changeContent_GetFeatureInfo(rec_params, response_json)

    # content = changeContentNamespace(resp.json(), Geo_namespace)
    return ["application/json", json.dumps(content)]


def changeContent_GetFeatureInfo(rec_params, resp_json):
    """
        Change the response of the GET Feature Info
    """

    if resp_json is not None:
        if global_settings.ECOSSYSTEM_GEOSERVER_NAME in rec_params['layers']:
            path_dict_MAES = global_settings.PATH_EMEP + 'maes_style.json'
            try:
                with open(path_dict_MAES, 'r') as json_file:
                    dict_maes = json.load(json_file)
            except:
                return resp_json 
            
            for i in range(len(resp_json['features'])):
                index = str(resp_json['features'][i]['properties']['GRAY_INDEX'])
                try:
                    label = dict_maes[index]
                except:
                    label = ''
                resp_json['features'][i]['properties']['label'] = label
            
    return resp_json   


def Geo_GetLegendGraphic(rec_params, resolution):
    """
        For a specific layer it is possible to obtain the legend of the images obtain through the WMS service
    """
    dict_EMEP = get_Dict_EMEP()
    default_year = list(dict_EMEP['datasets'][resolution].keys())[0]
    Geo_namespace = dict_EMEP['datasets'][resolution][default_year]['Geoserver']

    add_env_values(rec_params, resolution, rec_params['layer'])

    rec_params['layer'] = Geo_namespace + ':' + rec_params['layer']
    rec_params['service'] = "wms"
    rec_params['version'] = "1.3.0"
    rec_params['format'] = "image/png"

    if 'palette' in rec_params:
        del rec_params['palette']

    resp = request_Data_External_Source('get', gs_url, params=rec_params, headers=headers_image_accept, user=user, pwd=pwd, timer=False, authentication=True)
    if resp is None:
        return [None, None]

    return [resp.headers['Content-Type'], base64.b64encode(resp.content)]


def add_env_values(rec_params, resolution, gas):
    dict_EMEP = get_Dict_EMEP()
    _max = dict_EMEP['max_min'][resolution][gas]['max']
    _min = dict_EMEP['max_min'][resolution][gas]['min']
    # print(_max, _min, resolution, gas)
    decimal_places = 5

    medium = (_max + _min) / 2

    medium_min = (medium + _min) / 2

    medium_max = (medium + _max) / 2

    if _min > 0.00005:
        _min = round(_min-0.00005, decimal_places)
    medium_min = round(medium_min, decimal_places)
    medium = round(medium, decimal_places)
    medium_max = round(medium_max, decimal_places)
    _max = round(_max, decimal_places)
    # if _min < 1:
    #     _min = 0.0

    # _min = 3
    # medium = 30
    # _max = 300

    # env=low:10;medium:200;high:500
    rec_params['env'] = "low:" + str(_min) + ";medium:" + str(medium) + ";high:" + str(_max) + ";medium_min:" + str(medium_min) + ";medium_max:" + str(medium_max)


def Geo_General(rec_params):
    """
        Responsible to get information that are not related with the EMEP Data. So it the general proxy
    """

    if rec_params['request'] == 'GetFeatureInfo':
        return Geo_GetFeatureInfo(rec_params, None, False)
    
    if rec_params['request'] == 'GetLegendGraphic':
        rec_params['service'] = "wms"
        rec_params['version'] = "1.3.0"
        rec_params['format'] = "image/png"

    resp = request_Data_External_Source('get', gs_url, params=rec_params, user=user, pwd=pwd, timer=False, authentication=True)
    if resp is None:
        return [None, None]

    if rec_params['request'] == 'GetLegendGraphic':
        return [resp.headers['Content-Type'], base64.b64encode(resp.content)]
        
    return [resp.headers['Content-Type'], resp.content]


def getEMEPData(EMEP_gas, resolution, year, dir_path):
    """ 
        For a given gas with a given temporal resolution at a specific year, get all the data and save locally
    """

    dict_EMEP = get_Dict_EMEP()
    if not EMEP_gas in dict_EMEP['ListGases'][resolution]:
        return [None, None]

    if not year in dict_EMEP['datasets'][resolution].keys():
        return [None, None]

    namespace = dict_EMEP['datasets'][resolution][year]["Geoserver"]
    gas_namespace = namespace + ':' + EMEP_gas
    limit_time = get_Limits_of_Time(gas_namespace)

    dataEMEP_path, filename = save_file_locally(gas_namespace, limit_time, dir_path)

    return [dataEMEP_path, filename]


def get_Limits_of_Time(gas):
    """
        Get the limits time of the coverage
    """

    params = init_Params("WCS", "2.0.0", "DescribeCoverage")
    params["coverageId"] = gas

    response = request_Data_External_Source('get', gs_url, params=params, user=user, pwd=pwd, timer=False, authentication=True)
    if response is None:
        return ""
    
    content = xmltodict.parse(response.content)

    begin_time = content["wcs:CoverageDescriptions"]["wcs:CoverageDescription"]["gml:boundedBy"]["gml:EnvelopeWithTimePeriod"]["gml:beginPosition"]
    end_time = content["wcs:CoverageDescriptions"]["wcs:CoverageDescription"]["gml:boundedBy"]["gml:EnvelopeWithTimePeriod"]["gml:endPosition"]

    if end_time == begin_time:
        return ""
    
    return '"%s","%s"'%(begin_time, end_time)