import tkinter as tk
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from PIL import Image, ImageTk
import json
import io

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

folderDestinoId= '1zjWfDZ_tyx5nA7ghmRziOFobPG7BadAh'
folderOrigenId='1IdVes6eq_fxRwaEqOfBlvoqxKJ2BnCDs'

class VisorViajes:
    def __init__(self, ruta_json):
        with open(ruta_json, 'r') as f:
            self.puntos = json.load(f)
        print(f"tamaño:{len(self.puntos)}")
        self.idx_punto = 0   # Índice del grupo (coordenada)
        self.idx_foto = 0    # Índice de la foto dentro de ese grupo
        
        self.root = tk.Tk()
        self.root.title("Curador de Fotos de Viajes")
        
        # Etiqueta de Ubicación (Lat/Lon)
        self.lbl_coord = tk.Label(self.root, text="", font=("Arial", 10, "italic"))
        self.lbl_coord.pack()

        # Etiqueta de Info de la Foto
        self.lbl_foto = tk.Label(self.root, text="", font=("Arial", 12, "bold"))
        self.lbl_foto.pack(pady=5)

        # Contenedor de Imagen (Cambiamos Canvas por un Label que soporte imagen)
        self.panel_imagen = tk.Label(self.root, text="Cargando...", bg="lightgray", width=500, height=400)
        self.panel_imagen.pack(padx=20, pady=20)

        # # Contenedor de Imagen
        # self.canvas = tk.Label(self.root, text="[ AQUÍ VA LA FOTO ]", bg="lightgray", width=50, height=20)
        # self.canvas.pack(padx=20, pady=20)

        # Controles de Navegación
        frame_nav = tk.Frame(self.root)
        frame_nav.pack(pady=10)
        
        tk.Button(frame_nav, text="<< Ubicación", command=self.prev_punto).grid(row=0, column=0, padx=10)
        tk.Button(frame_nav, text="< Foto", command=self.prev_foto).grid(row=0, column=1)
        tk.Button(frame_nav, text="Foto >", command=self.next_foto).grid(row=0, column=2)
        tk.Button(frame_nav, text="Ubicación >>", command=self.next_punto).grid(row=0, column=3, padx=10)

        self.actualizar_vista()
        self.root.mainloop()

    def actualizar_vista(self):
        punto = self.puntos[self.idx_punto]
        foto = punto['archivo'][self.idx_foto]
        
        self.lbl_coord.config(text=f"Coordenadas: {punto['lat']}, {punto['lon']}")
        
        self.lbl_foto.config(text=f"{foto['viaje']} \n Archivo: {foto['nombre']} ({self.idx_foto + 1}/{len(punto['archivo'])})")
        try:
            # 1. Obtenemos los bytes de la imagen (usando tu función de Drive)
            # Nota: Si es HEIC, Drive suele devolver un JPEG si pides el thumbnail,
            # lo cual nos ahorra problemas de compatibilidad.
            print(f"foto a mostrar:{foto['nombre']}")
            # fileId=self.getIdFileDrive(foto['nombre'],folderOrigenId)
            #  # Asegúrate de que el JSON tenga el 'id' de Drive
            # if(fileId!=None):
            image_bytes = self.getBytesDrive(foto['id'])
            img_data = Image.open(io.BytesIO(image_bytes))            
            # 2. Redimensionar para que quepa en la ventana sin deformar
            img_data.thumbnail((500, 400))                 
            # 3. Convertir a formato Tkinter
            img_tk = ImageTk.PhotoImage(img_data)            
            # 4. Actualizar el panel
            self.panel_imagen.config(image=img_tk, text="")
            self.panel_imagen.image = img_tk # Referencia necesaria para que no se borre
            
        except Exception as e:
            self.panel_imagen.config(image='', text=f"Error al cargar imagen:\n{e}")
        

    def next_foto(self):
        fotos_en_punto = self.puntos[self.idx_punto]['archivo']
        if self.idx_foto < len(fotos_en_punto) - 1:
            self.idx_foto += 1
            self.actualizar_vista()

    def prev_foto(self):
        if self.idx_foto > 0:
            self.idx_foto -= 1
            self.actualizar_vista()

    def next_punto(self):
        if self.idx_punto < len(self.puntos) - 1:
            self.idx_punto += 1
            self.idx_foto = 0 # Reiniciamos al primer archivo del nuevo punto
            self.actualizar_vista()

    def prev_punto(self):
        if self.idx_punto > 0:
            self.idx_punto -= 1
            self.idx_foto = 0
            self.actualizar_vista()

    def getIdFileDrive(self,nombreArchivo,folderId):    
        query = f"name = \"{nombreArchivo}\" and '{folderId}' in parents and trashed = false"
        resultados = service.files().list(q=query, fields="files(id, name, webContentLink)").execute()
        items = resultados.get('files', [])
        print(len(f"tamaño:{items}"))
        if not items:
            return None
        else:
            # Tomamos el ID del primer resultado encontrado
            print(items[0])
            return items[0]['id']
        
    def getBytesDrive(self,fileId):
        try:
            request = service.files().get_media(fileId=fileId)
            return request.execute()
        except Exception as e:
            print(f"Error al descargar {fileId}: {e}")
            return None

# Ejecución
VisorViajes('data/fotosFinal.json')