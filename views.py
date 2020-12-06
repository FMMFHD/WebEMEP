import json
import urllib

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect

from General_modules import global_settings

from WebEMEP.utils import list_gases, proxy_General
from WebEMEP.helpers import convert_dict_lower_keys
from WebEMEP.GeoserverProxy import Geo_General


def proxy(request, information):
    out = {'success': False}

    if request.method == 'GET':
        rec_params = convert_dict_lower_keys(request.GET)

        if information == 'list_gases':
            return list_gases(rec_params['resolution'])

        if information == 'geoserver_General':
            [content_type, content] = Geo_General(rec_params)
            return HttpResponse(
                content,
                content_type=content_type,
                status=200)

        return proxy_General(request, rec_params, global_settings.PROXY_DEFAULT, information)
    
    return HttpResponse(
        json.dumps(out),
        content_type='application/json',
        status=200)
