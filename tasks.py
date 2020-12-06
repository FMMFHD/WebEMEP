from celery import task 
from celery import shared_task
from my_geonode.celeryapp import app as celery_app
from celery.schedules import crontab
import os
from datetime import datetime

from General_modules.module_logs import log_task_file
from General_modules import global_settings

from WebEMEP.UploadEMEPdata import EMEP_Create_dict, UploadEMEPDatasets, UploadEMEPDatasets_RecentYear
import WebEMEP.utils as utils
from WebEMEP.GeoserverProxy import get_Dict_EMEP 


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    #################################################### EXAMPLES #######################################################################################
    # Executes on 30/03 às 18h48 UTC todos os anos                                                                                                      #
    # sender.add_periodic_task(crontab(minute=48, hour=18, day_of_month='30',month_of_year='3'),  send_import_summary.s('Dayh'), name='EMEPask')        #
    # Executes every 60 seconds                                                                                                                         #
    # sender.add_periodic_task(60,  send_import_summary.s('0'), name='EMEP Task')                                                                       #
    #####################################################################################################################################################
    sender.add_periodic_task(crontab(minute=14, hour=18, day_of_month='23',month_of_year='8'),  Upload_EMEP_DATA.s(), name='EMEP')

    sender.add_periodic_task(crontab(minute=12, hour=16, day_of_month='9',month_of_year='4'),  Update_styles_GeoServer.s(), name='EMEP_update_styles')


@celery_app.task
def Upload_EMEP_DATA():
    log_task_file("Start the task Upload_EMEP_DATA")
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    if int(month) < 9:
        year = str(int(year)-1)
    dict_EMEP = EMEP_Create_dict(year, str(int(year)-1))
    UploadEMEPDatasets(dict_EMEP)
    #UploadEMEPDatasets(Dict_EMEP())


@celery_app.task
def Update_styles_GeoServer():
    utils.Update_styles_GeoServer()