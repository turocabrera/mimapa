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
# folderOrigenId='1IdVes6eq_fxRwaEqOfBlvoqxKJ2BnCDs'
folderOrigenId='1am6ryYKZn3bnw8I1eaYRIc8bfHie-8Ka'

                

def updateGpsPush(file_id, latitud, longitud,isHeic):
    # Descarga    
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    while not done:
        _, done = downloader.next_chunk()

    # Cargar EXIF actual o crear uno nuevo si no tiene
    fh.seek(0)
    img_bytes = fh.read()

    # Metadatos EXIF
    def to_exif_format(val, refs):
        ref = refs[0] if val < 0 else refs[1]
        abs_val = abs(val)
        deg = int(abs_val)
        min = int((abs_val - deg) * 60)
        sec = int((abs_val - deg - min/60) * 3600 * 100)
        return [(deg, 1), (min, 1), (sec, 100)], ref

    lat_tuple, lat_ref = to_exif_format(latitud, ("S", "N"))
    lon_tuple, lon_ref = to_exif_format(longitud, ("W", "E"))

    if isHeic:
        img = Image.open(io.BytesIO(img_bytes))
        raw_exif = img.info.get("exif", b"")
        try:
            exif_dict = piexif.load(raw_exif) if raw_exif else {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
    else:
        try:
            exif_dict = piexif.load(img_bytes)
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}

    
    #crea el bloque si no lo tiene
    if "GPS" not in exif_dict:
        exif_dict["GPS"] = {}

    # Insertar los nuevos valores GPS
    exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = lat_tuple
    exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_ref
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = lon_tuple
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_ref

    # Convertir dict a bytes y pegarlos en la imagen
    exif_bytes = piexif.dump(exif_dict)
    output_buffer = io.BytesIO()
    # piexif.insert(exif_bytes, img_bytes, output_buffer)

    if isHeic:        
        img = Image.open(io.BytesIO(img_bytes))
        img.save(output_buffer, format="HEIF", exif=exif_bytes)
        target_mime = 'image/heic'
    else:        
        piexif.insert(exif_bytes, img_bytes, output_buffer)
        target_mime = 'image/jpeg'

    output_buffer.seek(0)
    # media = MediaIoBaseUpload(output_buffer, mimetype='image/jpeg', resumable=True)
    media = MediaIoBaseUpload(output_buffer, mimetype=target_mime, resumable=True)
    updated_file = service.files().update(
        fileId=file_id,
        media_body=media,
        fields='id, name'
    ).execute()

    print(f"✅ ¡Listo! Archivo '{updated_file.get('name')}' actualizado con coordenadas: {latitud}, {longitud}")


def convertir_a_grados(valor):
    # Los datos GPS vienen en formato (grados, minutos, segundos)
    d = float(valor[0])
    m = float(valor[1])
    s = float(valor[2])
    return d + (m / 60.0) + (s / 3600.0)

def procesarArchivosUpdateGeo(directorio,origen,cadenaBuscar):
    lista_puntos = []
    if origen=='drive':        
        results = service.files().list(
                q=f"'{directorio}' in parents and name contains '{cadenaBuscar}' and trashed = false",
                pageSize=1000,
                fields="files(id, name, mimeType, webContentLink)"       
            ).execute()
        # print(results)    
        items = results.get('files', [])  
        for item in items:                
                 if item['name'].lower().endswith(('.heic', '.jpg', '.jpeg' , '.png')):        
                        fileId = item['id']
                        print(item['name'])                        
                        isHeic=item['name'].lower().endswith('.heic')or item['mimeType']=='image/heic'
                        updateGpsPush(fileId,-24.781245101615603, -65.40315227590362,isHeic)                            
    else:
        print('local')
    return 0

def leerCarpetaEHijos(directorio,directorioRaiz,cadenaBuscar):
    results = service.files().list(
                q=f"'{directorio}' in parents and name contains '{cadenaBuscar}' and trashed = false",
                pageSize=1000,
                fields="files(id, name, mimeType,webContentLink)"       
                # fields="files(*)"       
                ).execute()    
    items = results.get('files', [])  
    for item in items:    
                if(item['mimeType']=='application/vnd.google-apps.folder'):
                        #abrir archivos dentro de la carpeta                        
                        leerCarpetaEHijos(item['id'],item['name'], "")
                        
                else:                    
                    if item['name'].lower().endswith(('.heic', '.jpg', '.jpeg' , '.png')):                                                                        
                                print(f"' Archivo: {directorioRaiz}-{item['name']} ")                                    
    return 0

resultados = procesarArchivosUpdateGeo('1am6ryYKZn3bnw8I1eaYRIc8bfHie-8Ka','drive','IMG_3286')
# resultados = leerCarpetaEHijos(folderOrigenId,'','202')
# resultados = procesarArchivosUpdateGeo(folderOrigenId,'drive','dji_mimo_20260223_135804_20260223135805_1772061938838_photo')
                                    #    'dji_mimo_20260225_110054_20260225110055_1772061932293_photo')
                                    #    'dji_mimo_20260225_114734_20260225114735_1772061931180_photo')
                                    #    'dji_mimo_20260225_180806_20260225180806_1772061930479_photo')
                                    #    'dji_mimo_20260225_183358_20260225183358_1772061930446_photo')
# if resultados==0:
#      print("Actualización correcta")

     