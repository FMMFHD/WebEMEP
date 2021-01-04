# WebEMEP

The objectives of the WebEMEP component are to store all the available model predictions from the EMEP server in a local database. Besides storage, it offers access mechanisms and data management for a framework where web applications with geospatial data are developed. However, there are some issues concerning the data that contains the EMEP model results. The data stored in the EMEP server is accessed by HTTP through a catalogue. To collect the data it is necessary to consult the catalogue and parser it. 

WebEMEP architecture is illustrated in figure \ref{fig:WebEMEP_diagram}. The backend part is responsible for extracting and management of the data. There is no user interface because all the mechanisms are automatic, including the mechanism to download the data.

![WebEMEP Diagram](https://github.com/FMMFHD/WebEMEP/blob/main/img_readme/WebEMEP_diagram.png)

The WebEMEP component is responsible for retrieving data from the EMEP site and to make the information available on the platform. The Norwegian Meteorological Institute provides a catalogue that contains all the available services and data sets, and their URL paths. Therefore, the first step is to download the catalogue. The next step is to download and store the data, using the catalogue. The data provided by EMEP represents all of Europe, but there is only interest in a portion of that data. So the downloaded data has to be cut by using a polygon feature delimiting the relevant spatial domain, which can be altered. After the cut, the data is uploaded to the GeoServer, using the GeoServer API.

The Norwegian Meteorological Institute updates their catalogue yearly, normally at the same time of the year. Thus, the best way to guarantee the use of model predictions made with the most recent EMEP model version is to use a scheduler which updates all available data on a day set by the programmer. The scheduler is created using the Celery, a Python Library that manages task queues. This scheduler is a periodic Task manager, that kicks off tasks at regular intervals. The tasks are then executed by available worker nodes in the cluster. The programmer can choose the date and the frequency of the task, that is responsible to replace all the data that is available on the EMEP server.

The data management uses a dictionary that contains information of the catalogue that helps to track the data stored on the GeoServer. In addition, the management of this data is made through the available OGC standards and/or through the user interface made available by GeoServer.

For security reasons, the GeoServer cannot be accessed directly from the outside. Therefore, a proxy that gives indirect access to the GeoServer is used, that changes the URL and adjusts the query string of the request to match the OGC standards of the GeoServer. This proxy is responsible to forward the requests to the GeoServer or to the EMEP website, when the GeoServer is down. 

The GeoServer cannot be accessed directly from the outside. Therefore, it used a proxy that gives indirect access to the GeoServer. The API has only one available interface that uses the proxy to redirect to the GeoServer, changing the URL and adjusting the query string of the request to match the OGC standards of the GeoServer. This interface is used to get data from the GeoServer.
