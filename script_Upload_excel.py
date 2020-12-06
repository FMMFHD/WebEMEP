from GeoExcel.module_excel import copy_excel_database
import General_modules.global_settings as global_settings


db_user = global_settings.POSTGRESQL_USERNAME
db_password = global_settings.POSTGRESQL_PASSWORD
db_host = global_settings.POSTGRESQL_HOST
db_port = global_settings.POSTGRESQL_PORT
path = global_settings.EXTERNAL_PATH
Database = global_settings.DB_NAME_EMEP_APA


def EMEP_APA_Excel(path):
    """ 
        Copy the excel that has EMEP and APA gas information to database
    """

    tableName = "EMEP_APA_INFO"
    tableCharacteristics = """ "Nome" VARCHAR(255), "Units" VARCHAR(255), "ID_APA" VARCHAR(255), "ID_EMEP" VARCHAR(255), "Formula" VARCHAR(255), "Formula_codificada" VARCHAR(255)"""
    copy_excel_database('', path, Database, tableName, tableCharacteristics, create_sql_EMEP_APA_Excel, db_user, db_password, db_host, db_port, "Processed")

def create_sql_EMEP_APA_Excel(tableName, dataframe, fileName, information):
    keys = '"Nome", "Units", "ID_APA", "ID_EMEP", "Formula", "Formula_codificada"'
    sql = ""
    for index, row in dataframe.iterrows():
        value = "'%s', '%s', '%s', '%s'"%(row['Nome'], row['Units'], row['ID_APA'], str(row['ID_EMEP']).replace(" ", ""))
        value += ", '%s', '%s'"%(row['Formula'], row['Formula_codificada'])
        sql += '''INSERT INTO "%s"(%s) VALUES (%s); '''%(tableName, keys, value)
    
    value = "'Classification of Total deposition of nitrogen', 'nan', 'nan', 'TDEP_N_critical_load', 'nan', 'nan' "
    sql += '''INSERT INTO "%s"(%s) VALUES (%s); '''%(tableName, keys, value)
    return sql



if __name__ == "__main__":
    choice = ''

    while choice.lower() != 'no' and  choice.lower() != 'yes':
        choice = input("Do you want to upload the information of gases : \n Yes \n No \n Choose: ")

    if choice.lower() == 'yes':
        EMEP_APA_Excel(path + "my_geonode/Upload_GeoServer_Init/Excel_files/tabela-poluentes-APA-EMEP-unidadades.xlsx")
    