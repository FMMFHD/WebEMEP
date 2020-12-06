from General_modules.module_date import create_date_array

def convert_dict_lower_keys(dictionary):
    """Convert all keys to lowercase"""
    result = {}
    for key in dictionary:
        lista = dictionary.getlist(key)
        if len(lista) < 2:
            lista = lista[0]
        result[key.lower()] = lista
    return result


def get_list_dates_array_format(resolution, dict_emep, year):
    """
        Consult the list of possible dates save on the dict EMEP and generate a list of dates on a array format [year, month, day, hour]\n
        ATTENTION: The list of dates may not br in any order.\n
        The year resolution is in decrescent order, but the month resolution has the years in decrescent order but the months are not in any order
    """
    list_dates = []
    
    for date in dict_emep['ListDates'][resolution]['General']:
        list_dates.append(create_date_array(resolution, date, year))

    if int(year) % 4 == 0:
        array_dates = dict_emep['ListDates'][resolution]['Leap']
    else:
        array_dates = dict_emep['ListDates'][resolution]['NoLeap']

    for date in array_dates:
        list_dates.append(create_date_array(resolution, date, year))
    return list_dates