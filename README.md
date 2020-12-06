# WebEMEP

  Module that get the data from the EMEP database and saved it on the local database. It makes the connection between the stored EMEP data and the apps.

  Output of the data for EMEP graphics = 
  
  {

    "resolution": Temporal resolution,

    "emep_gas": id of the gas in the EMEP database,

    "<county> or <region>": County/Region Name,

    "station_name": Station Name
    
    "data": {

      "APA_GAS_NAME": Name of the gas according with the APA database,

      "dates": Array of dates,

      "max_line": Array of max values,

      "min_line": Array of min values,

      "weight_mean_line": Array of weight mean values,

    }
  }
