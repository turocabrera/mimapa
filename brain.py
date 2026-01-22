import pandas as pd
import simplejson as json
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from pillow_heif import register_heif_opener
import os

# Registro para que Pillow entienda archivos HEIC
register_heif_opener()

def obtener_exif(ruta_imagen):
    imagen = Image.open(ruta_imagen)
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

def convertir_a_grados(valor):
    # Los datos GPS vienen en formato (grados, minutos, segundos)
    d = float(valor[0])
    m = float(valor[1])
    s = float(valor[2])
    return d + (m / 60.0) + (s / 3600.0)

def procesar_carpeta(directorio):
    lista_puntos = []
    
    for archivo in os.listdir(directorio):
        
        if archivo.lower().endswith(('.heic', '.jpg', '.jpeg', '.png')):
            ruta_completa = os.path.join(directorio, archivo)
            # print('rutaCompleta: ',ruta_completa)
            exif = obtener_exif(ruta_completa)
            
            if exif and "GPSInfo" in exif:
                gps = exif["GPSInfo"]
                # Extraer Latitud y Longitud
                lat = convertir_a_grados(gps["GPSLatitude"])
                if gps["GPSLatitudeRef"] != "N": lat = -lat
                
                lon = convertir_a_grados(gps["GPSLongitude"])
                if gps["GPSLongitudeRef"] != "E": lon = -lon
                
                #buscar fecha en otros campos
                fecha = exif["fecha"]
                
                lista_puntos.append({
                    "archivo": archivo,
                    "lat": lat,
                    "lon": lon,
                    # "fecha": exif.get("DateTimeOriginal", "Desconocida")
                    "fecha": fecha
                })
    
    return lista_puntos

# Ejemplo de ejecución
resultados = procesar_carpeta('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\img\\villaPehuenia\\')
with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\viajes.json', 'w') as f:
    json.dump(resultados, f, indent=4)