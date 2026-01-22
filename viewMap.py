import folium
from folium.plugins import MarkerCluster
import pandas as pd
import simplejson as json
import base64
from io import BytesIO
import os

with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\fotosFinal.json', 'r') as f:
    datos = json.load(f)

df = pd.DataFrame(datos)

#arreglar la parte cronologica de las fotos
df['fecha_dt'] = pd.to_datetime(df['fecha'], format='%Y:%m:%d %H:%M:%S', errors='coerce')

# 3. Ordenar cronológicamente
# df = df.sort_values(by='fecha_dt')

# 1. Crear el mapa centrado en el promedio de tus coordenadas
mapa = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=4,max_zoom=19
                #   ,
                #   tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                #   attr='Esri World Imagery'
                  )

folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satélite',
    max_zoom=19,       # Le decimos a Folium que intente estirar la imagen hasta este nivel
    max_native_zoom=17 # Este es el zoom real que tiene Esri. Al pasar de aquí, Folium 'pixela' la imagen en lugar de cambiar de mapa
).add_to(mapa)

# 2. Capa de Etiquetas (Nombres de ciudades y rutas)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Etiquetas',
    overlay=True, # IMPORTANTE: Se pone encima de la otra
    control=True,
    max_zoom=19
).add_to(mapa)

# coordenadas_recorrido = df[['lat', 'lon']].values.tolist()
# 2. Crear un cluster para los marcadores
marker_cluster = MarkerCluster().add_to(mapa)

# folium.PolyLine(
#     locations=coordenadas_recorrido,
#     color="#FF5733",  # Color naranja/rojizo
#     weight=4,        # Grosor de la línea
#     opacity=0.8,
#     tooltip="Trayecto del viaje"
# ).add_to(mapa)

# 3. Agregar cada foto al mapa
for index, row in df.iterrows():
    
    lista_fotos = row['archivo']

    html_fotos = ""
    for foto in lista_fotos:
        nombre_thumb = os.path.splitext(foto)[0] + ".jpg"
        ruta_full_disco = os.path.join("C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\img\\thumbnails", nombre_thumb)
        
        if os.path.exists(ruta_full_disco):
            # LEER LA IMAGEN Y CONVERTIRLA A BASE64
            with open(ruta_full_disco, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
            
            # El src ahora es el código de la imagen, no una ruta
            html_fotos += f'<img src="data:image/jpeg;base64,{encoded_string}" width="150" style="margin-bottom:5px;"><br>'
        else:
            html_fotos += f'<p style="color:red;">No se halló: {nombre_thumb}</p>'


    #     ruta_thumb = f"img/thumbnails/{nombre_thumb}"
    #     # print(ruta_thumb)
    #     html_fotos += f'<img src="{ruta_thumb}" width="150" style="margin-bottom:5px;"><br>'
    #     # print(html_fotos)
    html_final = f"""
        <div style="max-height: 300px; overflow-y: auto; text-align: center;">
            <h4>Fotos ({len(lista_fotos)})</h4>
            {html_fotos}
        </div>
    """    
    # print(html_final)
    iframe = folium.IFrame(html_final, width=200, height=200)
    popup = folium.Popup(iframe, max_width=200)
    
    folium.Marker(
        location=[row['lat'], row['lon']],
        popup=popup
    ).add_to(marker_cluster)    
    
    # ).add_to(marker_cluster)

# Guardar el mapa en un archivo HTML
mapa.save("C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\mi_mapa_fotos.html")
print("Mapa generado como 'mi_mapa_fotos.html'. Ábrelo en tu navegador.")