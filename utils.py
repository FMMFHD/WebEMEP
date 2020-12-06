import json 

from django.http import HttpResponse, HttpResponseRedirect

from General_modules.module_GeoServer_access import get_url_user_pwd_geoserver, updateStyles
from General_modules import global_settings

from WebEMEP.GeoserverProxy import Geo_GetMap, Geo_GetFeatureInfo, Geo_GetCapabilities, Geo_GetLegendGraphic
from WebEMEP.GeoserverProxy import get_Dict_EMEP
from WebEMEP.EmepProxy import Emep_GetCapabilities, Emep_GetFeatureInfo, Emep_GetMap, Emep_GetLegendGraphic
from WebEMEP.helpers import convert_dict_lower_keys


def proxy_Geoserver(rec_params, resolution):
    """
        Forward the services to the GeoServer
    """

    if rec_params['request'] == 'GetMap':
        [content_type, content] = Geo_GetMap(rec_params, resolution)

    elif rec_params['request'] == 'GetCapabilities':
        [content_type, content] = Geo_GetCapabilities(rec_params, resolution)
    
    elif rec_params['request'] == 'GetFeatureInfo':
        [content_type, content] = Geo_GetFeatureInfo(rec_params, resolution, True)
    
    elif rec_params['request'] == 'GetLegendGraphic':
        # [content_type, content] = Emep_GetLegendGraphic(rec_params, resolution)
        [content_type, content] = Geo_GetLegendGraphic(rec_params, resolution)

    return [content_type, content]


def proxy_EMEP(rec_params, resolution):
    """
        Forward the services to the EMEP Site
    """
    
    if rec_params['request'] == 'GetMap':
        [content_type, content] = Emep_GetMap(rec_params, resolution)

    elif rec_params['request'] == 'GetCapabilities':
        [content_type, content] = Emep_GetCapabilities(rec_params, resolution)
    
    elif rec_params['request'] == 'GetFeatureInfo':
        [content_type, content] = Emep_GetFeatureInfo(rec_params, resolution)

    elif rec_params['request'] == 'GetLegendGraphic':
        [content_type, content] = Emep_GetLegendGraphic(rec_params, resolution)

    return [content_type, content]


def proxy_General(request, rec_params, service, resolution):
    """ Proxy General is where it decides to which service it is going to ask for the gas Layer"""
    if service == 'GEOSERVER':
        [content_type, content] = proxy_Geoserver(rec_params, resolution)
        if content_type is None or content is None:
            rec_params = convert_dict_lower_keys(request.GET)
            [content_type, content] = proxy_EMEP(rec_params, resolution)

    elif service == 'EMEP':
        [content_type, content] = proxy_EMEP(rec_params, resolution)

    response = HttpResponse(
        content,
        content_type=content_type,
        status=200)

    response.__setitem__("Access-Control-Allow-Origin", "*")

    return response


def list_gases(resolution):
    """Give the basic information to query the proxy. It gives the list of gases available for a specific resolution """
    dict_EMEP = get_Dict_EMEP()
    out = {}
    out['success'] = True
    out['listGases'] = dict_EMEP['ListGases'][resolution]

    return HttpResponse(
        json.dumps(out),
        content_type='application/json',
        status=200)


def Update_styles_GeoServer():
    dict_EMEP = get_Dict_EMEP()
    gs_url, gs_rest_url, user, pwd = get_url_user_pwd_geoserver()
    for resolution in dict_EMEP['resolutions']:

        ##############################################################################################################################################
        # Não está a fazer atualizar the resolucao horária e diária !!!!!!!!!!!!!!!!!!!
        if resolution == 'hour' or resolution == 'day': # or resolution == 'month':
            continue
        
        ##################################################################################################################################################

        years = dict_EMEP['datasets'][resolution].keys()

        for year in years:
            updateStyles(resolution + '-' + year, global_settings.STYLE_NAME_GENERAL, gs_rest_url, user, pwd, global_settings.PATH_EMEP_STYLE)


def list_resolution():
    """
        List the resolutions
    """
    dict_EMEP = get_Dict_EMEP()
    if global_settings.PROXY_DEFAULT == 'GEOSERVER':
        listResolution = ['year', 'month']
    else:
        listResolution = dict_EMEP['resolutions']

    limitBounds = dict_EMEP['LimitsBounds']

    return [limitBounds, listResolution]

