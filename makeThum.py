import os
import io
from PIL import Image
import apiConnectGoogle as apiConnectGoogle
import UtilFramework as utilFramework
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from pillow_heif import register_heif_opener

register_heif_opener()

SERVICE_ACCOUNT_FILE = 'config/claveServicio.json'

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


#metodo para generar thumbnail
def createThumbnails(imgBytesOrigen):
    img_input = io.BytesIO(imgBytesOrigen)
    with Image.open(img_input) as img:               
        # w_percent = (img.width / float(img.size[0]))
        # h_size = int((float(img.size[1]) * float(w_percent)))        
        # Redimensionar
        img_thumb_with= int(img.width*0.1)
        img_thumb_height=int(img.height*0.1)
        img_thumb = img.resize((img_thumb_with, img_thumb_height), Image.Resampling.LANCZOS)
        if img_thumb.mode in ("RGBA", "P"):
            img_thumb = img_thumb.convert("RGB")
        # Guardar el resultado en un nuevo "archivo" en memoria (formato JPEG)
        img_output = io.BytesIO()
        img_thumb.save(img_output, format="JPEG", quality=100)
        
        return img_output.getvalue()

#Recorrer el directorio y cargarlo en un directorio en particular
def processDirectory(directorioOrigen,directorioDestino,origen,destino):
    # crear directorio destino en caso de que no exista
    contadorArchivosProcesados=1
    if origen=="local":
        if not os.path.exists(directorioDestino):
            os.makedirs(directorioDestino)            
        for archivo in os.listdir(directorioOrigen):
            rutaCompletaArchivo = os.path.join(directorioOrigen, archivo)
            if archivo.lower().endswith(('.heic', '.jpg', '.jpeg')):
                contenidoBytesImagen=getBytesLocal(rutaCompletaArchivo)                        
                nombre_jpg = os.path.splitext(archivo)[0] + ".jpg"            
                thumbNew=createThumbnails(contenidoBytesImagen)
                rutaArchivoThumb = os.path.join(directorioDestino, nombre_jpg)
                saveBytesLocal(thumbNew,rutaArchivoThumb)     
                contadorArchivosProcesados=utilFramework.incrementarNumeroContadorProcesamiento(contadorArchivosProcesados)           
    else:
        #leer unidad desde origen Drive
        # print("directorio origen:",directorioOrigen)
        results = service.files().list(
                q=f"'{directorioOrigen}' in parents and trashed = false",
                pageSize=1000,
                fields="files(id, name, webContentLink)"        
            ).execute()
        # print(results)    
        items = results.get('files', [])        
        for item in items:
                #  print(item['name'])
                 if item['name'].lower().endswith(('.heic', '.jpg', '.jpeg')):        
                       fileId = item['id']
                       # Usamos el formato thumbnail que es el más compatible
                       contenidoBytesImagenDrive=getBytesDrive(fileId)
                       nombreJpgDrive = os.path.splitext(item['name'])[0] + ".jpg"            
                       thumbNewDrive=createThumbnails(contenidoBytesImagenDrive)                
                       saveBytesDrive(thumbNewDrive,nombreJpgDrive,directorioDestino)      
                       contadorArchivosProcesados=utilFramework.incrementarNumeroContadorProcesamiento(contadorArchivosProcesados)           
    print(f"¡Miniaturas {contadorArchivosProcesados}  creadas con éxito!:")

def getBytesLocal(ruta):
    with open(ruta, 'rb') as f:
        return f.read()

def saveBytesLocal(contenido, ruta_destino):
    with open(ruta_destino, 'wb') as f:
        f.write(contenido)

# Aquí irían los de Drive (usando la API)
def getBytesDrive(fileId):
    try:
        request = service.files().get_media(fileId=fileId)
        return request.execute()
    except Exception as e:
        print(f"Error al descargar {fileId}: {e}")
        return None

def getIdFileDrive(nombreArchivo,folderId):    
    query = f"name = \"{nombreArchivo}\" and '{folderId}' in parents and trashed = false"
    resultados = service.files().list(q=query, fields="files(id, name)").execute()
    items = resultados.get('files', [])
    if not items:
        return None
    else:
        # Tomamos el ID del primer resultado encontrado
        return items[0]['id']
        
def deleteFileDrive(nombreArchivo,folderId):
    idFileDrive=getIdFileDrive(nombreArchivo,folderId)
    if idFileDrive is not None:
        try:
            service.files().delete(fileId=idFileDrive).execute()
        except Exception as e:
            print(f"No se pudo eliminar el archivo previo {nombreArchivo}: {e}")

def saveBytesDrive(contenidoBytes, nombre, folderId):
    try:
        # eliminar archivo anterior
        deleteFileDrive(nombre,folderId)
        
        file_metadata = {
            'name': nombre,
            'parents': [folderId]
        }
        # Creamos un flujo de bytes para la subida        
        media = MediaIoBaseUpload(io.BytesIO(contenidoBytes), 
                                  mimetype='image/jpeg', 
                                  resumable=True)
        
        file = service.files().create(body=file_metadata, 
                                    media_body=media, 
                                    fields='id').execute()
        return file.get('id')
    except Exception as e:
        print(f"Error al subir {nombre}: {e}")
        return None

# crear_thumbnails('img/villaPehuenia/') 
# processDirectory('img/villaPehuenia/','img/thumbnails',"local","local")
processDirectory(folderOrigenId,folderDestinoId,"drive","drive")