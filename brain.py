import pandas as pd
import io
import simplejson as json
import UtilFramework as utilFramework
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from pillow_heif import register_heif_opener
import os

# Registro para que Pillow entienda archivos HEIC
register_heif_opener()

SCOPES = ['https://www.googleapis.com/auth/drive']

creds = Credentials.from_authorized_user_file('token.json', SCOPES)

# Si el token venció, refrescarlo
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
# creds = service_account.Credentials.from_service_account_file(
#         SERVICE_ACCOUNT_FILE, scopes=SCOPES)
# Me conecto 
service = build('drive', 'v3', credentials=creds)

# service = apiConnectGoogle.obtener_servicio()

# folderId = obtener_id_carpeta('thumbnails')
folderDestinoId= '1zjWfDZ_tyx5nA7ghmRziOFobPG7BadAh'
# principal raiz
folderOrigenId='1IdVes6eq_fxRwaEqOfBlvoqxKJ2BnCDs'
#prueba otro directorio
# folderOrigenId='1ZLHpkHlhH254GsAq1_5AcZfKR2zilp7X'
                
def obtener_exif(ruta_imagen,origen,img):
    """
    Metodo para obtener información GPS desde un archivo imagen que se obtiene
    se busca el tag: GPSInfo y la fecha del archivo en: tagId: 36867 o 0x8769
    """
    if(origen=="local"):
        imagen = Image.open(ruta_imagen)
        exif_data = imagen.getexif()
    else:
         imagen=Image.open(io.BytesIO(img))
         exif_data = imagen.getexif()
    # no lo puede encontrar 
    if not exif_data:
        return None
    
    info_exif = {}
    # Recorremos las etiquetas estándar
    for tag_id, valor in exif_data.items():
        nombre_tag = TAGS.get(tag_id, tag_id)
        
        # Si encontramos la etiqueta GPS (ID 34853)
        if nombre_tag == "GPSInfo" or tag_id == 34853:
            gps_info = {}
            # Obtenemos el diccionario específico de GPS
            # En versiones nuevas de Pillow, se usa get_ifd
            try:
                ifd = exif_data.get_ifd(0x8825) # 0x8825 es el offset para GPS
                for t in ifd:
                    sub_tag = GPSTAGS.get(t, t)
                    gps_info[sub_tag] = ifd[t]
                info_exif["GPSInfo"] = gps_info
            except Exception:
                # Si falla get_ifd, intentamos el acceso tradicional
                for t in valor:
                    sub_tag = GPSTAGS.get(t, t)
                    gps_info[sub_tag] = valor[t]
                info_exif["GPSInfo"] = gps_info
        else:
            info_exif[nombre_tag] = valor
        
        fecha = exif_data.get(36867)
        if not fecha:
                    try:
                        for key in exif_data.get_ifd(0x8769): # Exif IFD
                            if key == 36867:
                                fecha = exif_data.get_ifd(0x8769)[key]
                    except:
                        fecha = "Desconocida"
        info_exif["fecha"]=fecha


    return info_exif

def convertirAGrados(valor):
    """
       Convierte a Grados Los datos GPS vienen en formato (grados, minutos, segundos)
    """    
    d = float(valor[0])
    m = float(valor[1])
    s = float(valor[2])
    return d + (m / 60.0) + (s / 3600.0)
# Aquí irían los de Drive (usando la API)

def getBytesDrive(fileId):
    try:
        request = service.files().get_media(fileId=fileId)
        return request.execute()
    except Exception as e:
        print(f"Error al descargar {fileId}: {e}")
        return None

def procesarCarpetaRecursivo(directorio,directorioRaiz,origen,tipo='viajePersonal'):   
    """
    Metodo para recorrer recursivamente una carpeta hasta llegar a las imagenes y 
    leer su información y generar un json con la misma.
    """
    contadorArchivosProcesados = 1
    if origen=="local":                        
            for archivo in os.listdir(directorio):                
                if archivo.lower().endswith(('.heic', '.jpg', '.jpeg', '.png')):
                    ruta_completa = os.path.join(directorio, archivo)                               
                    exif = obtener_exif(ruta_completa,origen,None)
                    
                    if exif and "GPSInfo" in exif:
                        gps = exif["GPSInfo"]
                        # Extraer Latitud y Longitud
                        lat = convertirAGrados(gps["GPSLatitude"])
                        if gps["GPSLatitudeRef"] != "N": lat = -lat
                        
                        lon = convertirAGrados(gps["GPSLongitude"])
                        if gps["GPSLongitudeRef"] != "E": lon = -lon
                        
                        #buscar fecha en otros campos
                        fecha = exif["fecha"]
                        contadorArchivosProcesados=utilFramework.incrementarNumeroContadorProcesamiento(contadorArchivosProcesados)
                        lista_puntos.append({
                            "archivo": archivo,
                            "lat": lat,
                            "lon": lon,
                            # "fecha": exif.get("DateTimeOriginal", "Desconocida")
                            "fecha": fecha
                        })
                    else:
                            lista_sin_puntos.append({
                                                            "id":item['id'],
                                                             "archivo": item['name']                                                    
                                                         })
    else:
        #  drive
        results = service.files().list(
                q=f"'{directorio}' in parents and trashed = false",
                pageSize=1000,
                fields="files(id, name, mimeType, webContentLink)"        
            ).execute()
        items = results.get('files', [])        
        # print(f"ℹ️ total de archivos a procesar:{len(items)} ")
        for item in items:
                if(item['mimeType']=='application/vnd.google-apps.folder'):
                        #abrir archivos dentro de la carpeta      
                        print("Carpeta:",item['name'])                  
                        procesarCarpetaRecursivo(item['id'],item['name'], "drive")
                else:                
                        
                        if item['name'].lower().endswith(('.heic', '.jpg', '.jpeg' , '.png')):                                        
                                fileId = item['id']
                                # Usamos el formato thumbnail que es el más compatible
                                contenidoBytesImagenDrive=getBytesDrive(fileId)
                                exif = obtener_exif(None,origen,contenidoBytesImagenDrive)                                
                                nombreJpgDrive = os.path.splitext(item['name'])[0] + ".jpg"            
                                if exif and "GPSInfo" in exif:                        
                                    gps = exif["GPSInfo"]
                                    # Extraer Latitud y Longitud
                                    lat = convertirAGrados(gps["GPSLatitude"])
                                    if gps["GPSLatitudeRef"] != "N": lat = -lat
                                    
                                    lon = convertirAGrados(gps["GPSLongitude"])
                                    if gps["GPSLongitudeRef"] != "E": lon = -lon
                                    
                                    #buscar fecha en otros campos
                                    fecha = exif["fecha"]
                                    contadorArchivosProcesados=utilFramework.incrementarNumeroContadorProcesamiento(contadorArchivosProcesados)               
                                    lista_puntos.append({
                                        "id":item['id'],
                                        "archivo": item['name'],
                                        "lat": lat,
                                        "lon": lon,   
                                        "viaje": directorioRaiz,                             
                                        "tipo": tipo,
                                        "fecha": fecha
                                    })    
                                else:
                                     lista_sin_puntos.append({                                                          
                                                            "archivo": directorio+item['name']                                                    
                                                        })
    return lista_puntos

# Ejemplo de ejecución
# resultados = procesarCarpeta(folderOrigenId,'drive')
lista_puntos = []
lista_sin_puntos = []
resultados = procesarCarpetaRecursivo(folderOrigenId,'', 'drive')

with open('data/viajes.json', 'w') as f:
    json.dump(resultados, f, indent=4)
print(f" Sin GpsInfo: {lista_sin_puntos}")
print ("proceso finalizado")