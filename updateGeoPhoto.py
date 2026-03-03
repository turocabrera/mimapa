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
import piexif
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

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
# 1zjWfDZ_tyx5nA7ghmRziOFobPG7BadAh este valor lo saco de la url de google-drive en la carpeta
# folderId = obtener_id_carpeta('thumbnails')
folderDestinoId= '1zjWfDZ_tyx5nA7ghmRziOFobPG7BadAh'
folderOrigenId='1IdVes6eq_fxRwaEqOfBlvoqxKJ2BnCDs'

def updateGpsPush(file_id, latitud, longitud):
    # 1. Descargar la imagen a memoria (RAM)
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    while not done:
        _, done = downloader.next_chunk()
    
    # 2. Preparar los metadatos EXIF
    def to_exif_format(val, refs):
        ref = refs[0] if val < 0 else refs[1]
        abs_val = abs(val)
        deg = int(abs_val)
        min = int((abs_val - deg) * 60)
        sec = int((abs_val - deg - min/60) * 3600 * 100)
        return [(deg, 1), (min, 1), (sec, 100)], ref

    lat_tuple, lat_ref = to_exif_format(latitud, ("S", "N"))
    lon_tuple, lon_ref = to_exif_format(longitud, ("W", "E"))

    # Cargar EXIF actual o crear uno nuevo si no tiene
    fh.seek(0)
    img_bytes = fh.read()
    try:
        exif_dict = piexif.load(img_bytes)
    except:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}

    # Insertar los nuevos valores GPS
    exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = lat_tuple
    exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_ref
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = lon_tuple
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_ref

    # Convertir dict a bytes y pegarlos en la imagen
    exif_bytes = piexif.dump(exif_dict)
    output_buffer = io.BytesIO()
    piexif.insert(exif_bytes, img_bytes, output_buffer)
    output_buffer.seek(0)

    # 3. ACTUALIZAR el archivo en Drive (mismo ID, nuevo contenido)
    media = MediaIoBaseUpload(output_buffer, mimetype='image/jpeg', resumable=True)
    updated_file = service.files().update(
        fileId=file_id,
        media_body=media,
        fields='id, name'
    ).execute()

    print(f"✅ ¡Listo! Archivo '{updated_file.get('name')}' actualizado con coordenadas: {latitud}, {longitud}")

# --- Ejemplo de uso ---
# file_id_ejemplo = "EL_ID_QUE_TRAJISTE_CON_LIST"
# inyectar_gps_y_subir(service, file_id_ejemplo, -24.7821, -65.4232)

def obtener_exif(ruta_imagen,origen,img):
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
        print(f"' nombre tag '{nombre_tag}' .'")
        # Si encontramos la etiqueta GPS (ID 34853)
        if nombre_tag == "GPSInfo" or tag_id == 34853:
            gps_info = {}
            # Obtenemos el diccionario específico de GPS
            # En versiones nuevas de Pillow, se usa get_ifd
            try:
                ifd = exif_data.get_ifd(0x8825) # 0x8825 es el offset para GPS
                for t in ifd:
                    sub_tag = GPSTAGS.get(t, t)
                    print(f"' nombre subtag'{sub_tag}' .' '{ifd[t]}'")
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

def convertir_a_grados(valor):
    # Los datos GPS vienen en formato (grados, minutos, segundos)
    d = float(valor[0])
    m = float(valor[1])
    s = float(valor[2])
    return d + (m / 60.0) + (s / 3600.0)

def getBytesDrive(fileId):
    try:
        request = service.files().get_media(fileId=fileId)
        return request.execute()
    except Exception as e:
        print(f"Error al descargar {fileId}: {e}")
        return None
    
def procesarArchivosUpdateGeo(directorio,origen,cadenaBuscar):
    lista_puntos = []
    if origen=='drive':
        print('Drive')
         #  drive
        results = service.files().list(
                q=f"'{directorio}' in parents and name contains '{cadenaBuscar}' and trashed = false",
                pageSize=1000,
                fields="files(id, name, webContentLink)"       
            ).execute()
        # print(results)    
        items = results.get('files', [])  
        for item in items:
                #  print(item['name'])
                 if item['name'].lower().endswith(('.heic', '.jpg', '.jpeg' , '.png')):        
                        fileId = item['id']
                        print(item['name'])
                        # Usamos el formato thumbnail que es el más compatible
                        updateGpsPush(fileId,-40.15151864735295, -71.3998008496004)
                        # updateGpsPush(fileId,-40.05922815136061, -71.32536831856793)
                        # updateGpsPush(fileId, -40.05284105761339, -71.3322896811943)
                        # updateGpsPush(fileId, -40.067478478648816, -71.31500711488071)
                        contenidoBytesImagenDrive=getBytesDrive(fileId)
                        exif = obtener_exif(None,origen,contenidoBytesImagenDrive)
                        nombreJpgDrive = os.path.splitext(item['name'])[0] + ".jpg"            

                        if exif and "GPSInfo" in exif:
                            gps = exif["GPSInfo"]
                            # Extraer Latitud y Longitud
                            lat = convertir_a_grados(gps["GPSLatitude"])
                            if gps["GPSLatitudeRef"] != "N": lat = -lat
                            
                            lon = convertir_a_grados(gps["GPSLongitude"])
                            if gps["GPSLongitudeRef"] != "E": lon = -lon
                            
                            #buscar fecha en otros campos
                            fecha = exif["fecha"]
                            # contadorArchivosProcesados=utilFramework.incrementarNumeroContadorProcesamiento(contadorArchivosProcesados)               
                            lista_puntos.append({
                                "archivo": item['name'],
                                "lat": lat,
                                "lon": lon,
                                # "fecha": exif.get("DateTimeOriginal", "Desconocida")
                                "fecha": fecha
                            })
    else:
        print('local')
    return 0


resultados = procesarArchivosUpdateGeo(folderOrigenId,'drive','dji_mimo_20260223_135804_20260223135805_1772061938838_photo')
                                    #    'dji_mimo_20260225_110054_20260225110055_1772061932293_photo')
                                    #    'dji_mimo_20260225_114734_20260225114735_1772061931180_photo')
                                    #    'dji_mimo_20260225_180806_20260225180806_1772061930479_photo')
                                    #    'dji_mimo_20260225_183358_20260225183358_1772061930446_photo')
if resultados==0:
     print("Actualización correcta")

     