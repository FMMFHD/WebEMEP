import json
import urllib
import requests
from requests.auth import HTTPBasicAuth
import base64
# parse() xml->dict |||| unparse() dict->xml
import xmltodict 

from General_modules import global_settings
from WebEMEP.GeoserverProxy import createTimeDimension, get_Dict_EMEP

headers_xml_accept = {'accept': 'application/xml'}
headers_image_accept = {'accept': 'image/png'}


def request_data(url, params, headers):
    return requests.get(url + '?' + urllib.parse.urlencode(params, doseq=True), 
        headers=headers)


def checkLayer(layer, resolution, default_year):
    """Verify the name of the layer and its time dimension"""
    if "Dimension" in layer.keys():
        dict_EMEP = get_Dict_EMEP()
        listDates = dict_EMEP['ListDates'][resolution]
        for year in dict_EMEP['datasets'][resolution]:
            if year != default_year:
                layer['Dimension']['#text'] += ',' + createTimeDimension(year, listDates)
    # layer['EX_GeographicBoundingBox'] = EX_Geographic_dict
    # layer['BoundingBox'] = Bounding_dict


def Content_Capabilities(xmlcontent, resolution, default_year):
    """ Check the content of the response of the GetCapabilities
        Changes on each Layer:
            - EX_GeographicBoundingBox values
            - BoundingBox values
            - Adding the time dimensions respecting the resolution
    """
    content = xmltodict.parse(xmlcontent)
    General_layer = content['WMS_Capabilities']['Capability']['Layer']

    if 'Layer' in General_layer.keys():
        if 'Layer' in General_layer['Layer'].keys():
            Layers = General_layer['Layer']['Layer']
            if isinstance(Layers, list):
                for layer in Layers:
                    checkLayer(layer, resolution, default_year)
            else:
                checkLayer(Layers, resolution, default_year)
    return xmltodict.unparse(content)


def Emep_GetCapabilities(rec_params, resolution):
    """Corresponds to the WMS service: Get Capabilities"""
    dict_EMEP = get_Dict_EMEP()
    emep_wms_url = global_settings.EMEP_URL_BASE + dict_EMEP['services']['wms']

    default_year = list(dict_EMEP['datasets'][resolution].keys())[0]
    url_data = dict_EMEP['datasets'][resolution][default_year]['EMEPSite']
    
    resp = request_data(emep_wms_url + url_data, rec_params, headers_xml_accept)
    content = Content_Capabilities(resp.content, resolution, default_year)
    return [resp.headers['Content-Type'], content]


def redirect(rec_params, resolution):
    """
        Change the parameters that are not common between the information that came from the view and the information that has to send to the rest EMEP site to get the same thing
    """
    dict_EMEP = get_Dict_EMEP()
    if 'time' in rec_params.keys():
        return rec_params['time'].split('-')[0]
    else:
        return list(dict_EMEP['datasets'][resolution].keys())[0]


def Emep_GetMap(rec_params, resolution):
    """Corresponds to the WMS service: Get Map"""
    dict_EMEP = get_Dict_EMEP()
    year = redirect(rec_params, resolution)
    emep_wms_url = global_settings.EMEP_URL_BASE + dict_EMEP['services']['wms']

    url_data = dict_EMEP['datasets'][resolution][year]['EMEPSite']
    resp = request_data(emep_wms_url + url_data, rec_params, headers_image_accept)
    return [resp.headers['Content-Type'], resp.content]


#  (Equal to Emep_GetMap but the header of thge request data is diff)
def Emep_GetFeatureInfo(rec_params, resolution):
    """Corresponds to the WMS service: Get GetFeatureInfo"""
    dict_EMEP = get_Dict_EMEP()
    emep_wms_url = global_settings.EMEP_URL_BASE + dict_EMEP['services']['wms']
    
    year = redirect(rec_params, resolution)
    url_data = dict_EMEP['datasets'][resolution][year]['EMEPSite']
    resp = request_data(emep_wms_url + url_data, rec_params, headers_xml_accept)
    content = convertCommonFormat(resp.content)
    return ["application/json", content]


def convertCommonFormat(xmlcontent):
    """
        Convert xml to json
    """
    content = xmltodict.parse(xmlcontent)
    return json.dumps(content)


def Emep_GetLegendGraphic(rec_params, resolution):
    """
        For a specific layer it is possible to obtain the legend of the images obtain through the WMS service
    """
    dict_EMEP = get_Dict_EMEP()
    emep_wms_url = global_settings.EMEP_URL_BASE + dict_EMEP['services']['wms']
    default_year = list(dict_EMEP['datasets'][resolution].keys())[0]
    url_data = dict_EMEP['datasets'][resolution][default_year]['EMEPSite']
    resp = request_data(emep_wms_url + url_data, rec_params, headers_image_accept)
    return [resp.headers['Content-Type'], base64.b64encode(resp.content)]