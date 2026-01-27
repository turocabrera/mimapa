import folium
from folium.plugins import MarkerCluster
from folium.plugins import BeautifyIcon
from branca.element import Element
import pandas as pd
import simplejson as json
import base64
from io import BytesIO
import os

with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\fotosFinal.json', 'r') as f:
    datos = json.load(f)
df = pd.DataFrame(datos)
#en este archivo cargaba las estaciones de servicio pero ahora no solo seran estaciones de servicio
#proximamente cambiaré el nombre del archivo
with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\estacionesServicio.json', 'r') as est:
    estDatos = json.load(est)
dfEstacionesServicio = pd.DataFrame(estDatos)
#cargo las configuraciones de iconos para los itemos que no son fotos
with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\estilosConfig.json', 'r') as estiloConfigRead:
    estiloConfigDatos = json.load(estiloConfigRead)

#cargo provincias visitadas. salta jujuy y neuquen
capaProvincias = folium.FeatureGroup(name="Límites Provinciales")
folium.GeoJson('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\provincias.json',name='provincias',style_function=lambda x: {'fillColor': '#3186cc','color': 'blue','weight': 2,'fillOpacity': 0.4}).add_to(capaProvincias)



#arreglar la parte cronologica de las fotos
df['fecha_dt'] = pd.to_datetime(df['fecha'], format='%Y:%m:%d %H:%M:%S', errors='coerce')

#creo el mapa centrado en el promedio de tus coordenadas (mean) y lo pongo como zoom_star=4
#para que se vea todo el mapa de argentina
mapa = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=4,max_zoom=19)

# Capa de mapa satelital
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satélite',
    max_zoom=19,       # Le decimos a Folium que intente estirar la imagen hasta este nivel
    max_native_zoom=17 # Este es el zoom real que tiene Esri. Al pasar de aquí, Folium 'pixela' la imagen en lugar de cambiar de mapa
).add_to(mapa)

# Capa de Etiquetas (Nombres de ciudades y número de rutas)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Etiquetas',
    overlay=True, # IMPORTANTE: Se pone encima de la otra
    control=True,
    max_zoom=19
).add_to(mapa)

#para mostrar las rutas
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Solo Carreteras',
    overlay=True,  # Esto permite que se vea lo que hay debajo
    control=True,
    max_zoom=19
).add_to(mapa)

#cargo capa de provincias
capaProvincias.add_to(mapa)


layerGasolineras = folium.FeatureGroup(name='referencias útiles')

for index, fila in dfEstacionesServicio.iterrows():
    # Creamos un texto para el popup que incluya las funciones
    # Unimos la lista de funciones con saltos de línea HTML <br>
    servicios = "<br>".join([f"• {f}" for f in fila['funciones']])

    contenido_popup = f"""
    <strong>{fila['nombre']}</strong><br>
    <strong>Servicios:</strong><br>
    {servicios}
    """
    
    estilo = estiloConfigDatos.get(fila['tipo'], estiloConfigDatos['default'])
    #genero icon especifico de folium
    iconEstilo = BeautifyIcon(
        icon=estilo['icon'],
        icon_shape='circle',      # Forma circular
        border_color='white',     # EL BORDE BLANCO
        background_color=estilo['color'], # El fondo con tu color del JSON
        text_color='white',       # Color del icono
        border_width=3,           # Grosor del borde
        inner_icon_style='margin-top:0;'
    )
    folium.Marker(
        location=[fila['lat'], fila['lon']],
        popup=folium.Popup(contenido_popup, max_width=200),
        tooltip=fila['nombre'],
        icon=iconEstilo
        # icon=folium.Icon(  color=estilo['color'],icon=estilo['icon'], prefix='fa')        
    ).add_to(layerGasolineras)

layerGasolineras.add_to(mapa)

# 2. Crear un cluster para los marcadores

marker_cluster = MarkerCluster(name="Fotos").add_to(mapa)


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
    
mapId = mapa.get_name()
layerGasolineriaId = layerGasolineras.get_name()
layerProvinciaId = capaProvincias.get_name()
#script para mostrar o no estaciones de servicio
script_zoom = Element(f"""
    <script>
        var checkExist = setInterval(function() {{
           // Verificamos si tanto el objeto del mapa como la capa ya existen
           if (typeof {mapId} !== 'undefined' && typeof {layerGasolineriaId} !== 'undefined' && typeof {layerProvinciaId} !== 'undefined') {{
              var mapa_objeto = {mapId};
              var capa_objeto = {layerGasolineriaId};
              var capa_provincias = {layerProvinciaId};
              function actualizar() {{                  
                  var z = mapa_objeto.getZoom();                    
                  if (z < 10) {{                  
                      if (mapa_objeto.hasLayer(capa_objeto)) {{
                          mapa_objeto.removeLayer(capa_objeto);
                          mapa_objeto.addLayer(capa_provincias);
                      }}
                  }} else {{
                      if (!mapa_objeto.hasLayer(capa_objeto)) {{
                          mapa_objeto.removeLayer(capa_provincias);
                          mapa_objeto.addLayer(capa_objeto);
                      }}
                  }}
              }}

              mapa_objeto.on('zoomend', actualizar);
              actualizar(); // Ejecución inicial
              
              clearInterval(checkExist); // Detenemos el buscador una vez que ya configuramos todo
           }}
        }}, 100); // Revisar cada 100ms
    </script>
""")
mapa.get_root().html.add_child(script_zoom)

mapa.get_root().header.add_child(
    folium.Element('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">')
)

# Guardar el mapa en un archivo HTML
folium.LayerControl().add_to(mapa)
mapa.save("C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\index.html")
print("Mapa generado como 'index.html'. Ábrelo en tu navegador.")