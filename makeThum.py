import os
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def crear_thumbnails(directorio_fotos, destino="C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\img\\thumbnails"):
    if not os.path.exists(destino):
        os.makedirs(destino)
    
    for archivo in os.listdir(directorio_fotos):
        if archivo.lower().endswith(('.heic', '.jpg', '.jpeg')):
            img = Image.open(os.path.join(directorio_fotos, archivo))
            #deberia configurar w y h para que sea correcto el tamaño
            # print(img.width,"x",img.height)            
            # print(img.width*0.1,"x",img.height*.1)
            # Achicamos la imagen para que el mapa no sea lento
            img.thumbnail((img.width*0.06, img.height*0.06)) 
            # img.thumbnail((200, 200)) 
            # La guardamos como JPG
            nombre_jpg = os.path.splitext(archivo)[0] + ".jpg"
            img.save(os.path.join(destino, nombre_jpg), "JPEG")
    print("¡Miniaturas creadas con éxito!")

# Ejecutar: Cambia 'C:\\mis_fotos' por tu carpeta real
crear_thumbnails('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\img\\villaPehuenia\\')