import folium

from folium.plugins import MarkerCluster
#componente para poner mas lindos los iconos
from folium.plugins import BeautifyIcon
#componente de busqueda
from folium.plugins import Search
#para poder escribir codigos javascript
from branca.element import Element
import pandas as pd
import simplejson as json
import base64
from io import BytesIO
import os
import apiConnectGoogle as apiConnectGoogle
from google.oauth2 import service_account
from googleapiclient.discovery import build



def obtener_id_carpeta(nombre_carpeta):
    query = f"name = '{nombre_carpeta}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    resultados = service.files().list(q=query, fields="files(id, name)").execute()
    items = resultados.get('files', [])
    return items[0]['id'] if items else None

#definir letra para el proyecto 
fuente_apple = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'

# with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\data\\fotosFinal.json', 'r') as f:
with open('data/fotosFinal.json', 'r') as f:
    datos = json.load(f)
df = pd.DataFrame(datos)
#en este archivo cargaba las estaciones de servicio pero ahora no solo seran estaciones de servicio
#proximamente cambiaré el nombre del archivo
with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\data\\estacionesServicio.json', 'r') as est:
    estDatos = json.load(est)
dfEstacionesServicio = pd.DataFrame(estDatos)
#cargo las configuraciones de iconos para los itemos que no son fotos
with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\data\\estilosConfig.json', 'r') as estiloConfigRead:
    estiloConfigDatos = json.load(estiloConfigRead)

#cargo provincias visitadas. salta jujuy y neuquen
capaProvincias = folium.FeatureGroup(name="Límites Provinciales")
folium.GeoJson('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\data\\provincias.json',name='provincias',style_function=lambda x: {'fillColor': '#3186cc','color': 'blue','weight': 2,'fillOpacity': 0.4}).add_to(capaProvincias)

with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\data\\rutas.json', 'r') as rutas:
    rutaDatos = json.load(rutas)


# conectar a googleDrive para buscar las fotos
SERVICE_ACCOUNT_FILE = 'config/claveServicio.json'

# Definimos los alcances (scopes)
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Autenticación directa sin navegador
creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

# service = apiConnectGoogle.obtener_servicio()
# 1zjWfDZ_tyx5nA7ghmRziOFobPG7BadAh este valor lo saco de la url de google-drive en la carpeta
# folderId = obtener_id_carpeta('thumbnails')
folderId= '1zjWfDZ_tyx5nA7ghmRziOFobPG7BadAh'
if folderId:
    results = service.files().list(
        q=f"'{folderId}' in parents and trashed = false",
        pageSize=1000,
        fields="files(id, name, webContentLink)"        
    ).execute()
    
    items = results.get('files', [])

    fotos_drive = {}    
    for item in items:
        file_id = item['id']
        # Usamos el formato thumbnail que es el más compatible
        link = f"https://drive.google.com/thumbnail?sz=w500&id={item['id']}" 
        fotos_drive[item['name']] = link    
else:
    print("No se encontró la carpeta 'thumbs'.")



#arreglar la parte cronologica de las fotos
df['fecha_dt'] = pd.to_datetime(df['fecha_min'], format='%Y:%m:%d %H:%M:%S', errors='coerce')

#creo el mapa centrado en el promedio de tus coordenadas (mean) y lo pongo como zoom_star=4
#para que se vea todo el mapa de argentina
# pongo el control_zoom=False, para poder moverlo luego y que quede el search por un lado y el zoom por otro lado
mapa = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=4,max_zoom=19,zoom_control=True,control_scale=True)


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

layerRutas = folium.FeatureGroup(name='rutas recorridas')

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

# # Trae las fotos desde Drive
# df['url_mapa'] = df['nombre_foto'].map(fotos_drive)

# 3. Agregar cada foto al mapa Versión archivo en base 64
# for index, row in df.iterrows():
    
#     lista_fotos = row['archivo']

#     html_fotos = ""
#     for foto in lista_fotos:
#         nombre_thumb = os.path.splitext(foto)[0] + ".jpg"
#         ruta_full_disco = os.path.join("C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\img\\thumbnails", nombre_thumb)
        
#         if os.path.exists(ruta_full_disco):
#             # LEER LA IMAGEN Y CONVERTIRLA A BASE64
#             with open(ruta_full_disco, "rb") as img_file:
#                 encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
            
#             # El src ahora es el código de la imagen, no una ruta
#             html_fotos += f'<img src="data:image/jpeg;base64,{encoded_string}" width="150" style="margin-bottom:5px;"><br>'
#         else:
#             html_fotos += f'<p style="color:red;">No se halló: {nombre_thumb}</p>'


#     #     ruta_thumb = f"img/thumbnails/{nombre_thumb}"
#     #     # print(ruta_thumb)
#     #     html_fotos += f'<img src="{ruta_thumb}" width="150" style="margin-bottom:5px;"><br>'
#     #     # print(html_fotos)
#     html_final = f"""
#         <div style="max-height: 300px; overflow-y: auto; text-align: center;">
#             <h4>Fotos ({len(lista_fotos)})</h4>
#             {html_fotos}
#         </div>
#     """    
#     # print(html_final)
#     iframe = folium.IFrame(html_final, width=200, height=200)
#     popup = folium.Popup(iframe, max_width=200)
    
#     folium.Marker(
#         location=[row['lat'], row['lon']],
#         popup=popup
#     ).add_to(marker_cluster)    
    
    # ).add_to(marker_cluster)


# 3. Agregar cada foto al mapa (Versión Google Drive)
for index, row in df.iterrows():
    
    lista_fotos = row['archivo']
    html_fotos = ""
    
    for foto in lista_fotos:
        # Buscamos el nombre del thumb (ej: foto1.jpg)
        nombre_thumb = os.path.splitext(foto["nombre"])[0] + ".jpg"
        
        # En lugar de buscar en C:\juegos\..., buscamos en nuestro diccionario de Drive
        url_drive = fotos_drive.get(nombre_thumb)
        
        if url_drive:
            # El src ahora es el link directo de Drive
            # html_fotos += f'<img src="{url_drive}" referrerpolicy="no-referrer" width="150" style="margin-bottom:5px; border-radius:5px;"><br>'
            html_fotos += f'''
            <div style="margin-bottom: 10px;width: 100%; border-radius: 12px;background-color: #fbfbfd; border: 1px solid #e1e1e3;overflow: hidden;color: #86868b">
                <img src="{url_drive}" referrerpolicy="no-referrer" width="150" style="width: 100%" >
                <p style="font-size: 10px; margin: 0; color: #666;">{foto["fecha"]}</p>
            </div>
            '''
        else:
            # Si no está en el diccionario de la carpeta de Drive
            html_fotos += f'<p style="color:red; font-size:10px;">No en Drive: {nombre_thumb}</p>'

    html_final = f"""
        <div style="max-height: 350px; 
            overflow-y: auto; 
            text-align: center; 
            font-family: {fuente_apple}; 
            padding: 10px; 
            background-color: white;">
            <h4 style="margin: 0 0 12px 0; 
               color: #1d1d1f; 
               font-size: 16px; 
               font-weight: 600; 
               letter-spacing: -0.5px;">Fotos ({len(lista_fotos)})</h4>
            {html_fotos}
        </div>
    """    
    
    iframe = folium.IFrame(html_final, width=220, height=250)
    popup = folium.Popup(iframe, max_width=250)
    
    # popup = folium.Popup(html_final, max_width=220)
    

    folium.Marker(
        location=[row['lat'], row['lon']],
        popup=popup,
        icon=folium.Icon(color='blue', icon='camera') # Agregué un icono de cámara
    ).add_to(marker_cluster)



#agregar buscador
estDatosGeojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [punto['lon'], punto['lat']] 
            },
            "properties": {
                "nombre": punto['nombre'],
                "tipo": punto['tipo'],
                "funciones": ", ".join(punto['funciones']) # Convertimos la lista a texto para el buscador
            }
        } for punto in estDatos
    ]
}

origenBusquedaEstDatos = folium.GeoJson(
    estDatosGeojson,
    name="capaInvisibleParaBusquedas",
    # tooltip=folium.GeoJsonTooltip(fields=['nombre', 'tipo']),
    style_function=lambda x: {'fillOpacity': 0, 'opacity': 0, 'weight': 0},
    marker=folium.CircleMarker(radius=1, color='transparent'), 
    control=False
).add_to(mapa)

folium.GeoJson(
    rutaDatos,
    name='Rutas de Viaje',
    style_function=lambda feature: {
        'fillColor': feature['properties']['color'],
        'color': feature['properties']['color'],
        'weight': feature['properties']['grosor'],
        'opacity': 0.6,
    },
    tooltip=folium.GeoJsonTooltip(fields=['nombre', 'fecha','distancia'], aliases=['Ruta:', 'Fecha:','Distancia:'])
).add_to(layerRutas)

layerRutas.add_to(mapa)

# Configurar el Buscador
servicios_search = Search(
    layer=origenBusquedaEstDatos,
    geom_type='Point',
    placeholder='Buscar lugar...',
    collapsed=False,
    search_label='nombre', # El campo del JSON por el que querés buscar
    weight=3,
    zoom=19
).add_to(mapa)


mapId = mapa.get_name()
layerGasolineriaId = layerGasolineras.get_name()
layerProvinciaId = capaProvincias.get_name()
layerRutasId = layerRutas.get_name()
#script para mostrar o no estaciones de servicio
script_zoom = Element(f"""
    <script>
        var checkExist = setInterval(function() {{
           // Verificamos si tanto el objeto del mapa como la capa ya existen
           if (typeof {mapId} !== 'undefined' && typeof {layerGasolineriaId} !== 'undefined' && typeof {layerProvinciaId} !== 'undefined' && typeof {layerRutasId} !== 'undefined' ) {{
              var mapa_objeto = {mapId};
              var capa_objeto = {layerGasolineriaId};
              var capa_provincias = {layerProvinciaId};              
              var capa_rutas = {layerRutasId};
              function actualizar() {{                  
                  var z = mapa_objeto.getZoom();                                      
                  if (z < 8) {{                  
                      if (mapa_objeto.hasLayer(capa_objeto)) {{
                          mapa_objeto.removeLayer(capa_objeto);                          
                          mapa_objeto.removeLayer(capa_rutas);                          
                          mapa_objeto.addLayer(capa_provincias);
                      }}
                  }} else {{
                      if (!mapa_objeto.hasLayer(capa_objeto)) {{
                          mapa_objeto.removeLayer(capa_provincias);
                          mapa_objeto.addLayer(capa_objeto);                          
                          mapa_objeto.addLayer(capa_rutas);                          
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

search_id = servicios_search.get_name()
script_forzar_zoom_search = Element(f"""
<script>
    var monitorBuscador = setInterval(function() {{
        var inputBusqueda = document.querySelector('.search-input');
        if (inputBusqueda && typeof {mapId} !== 'undefined') {{
            
            var mapa = {mapId};

            function forzarVuelo() {{
                // Le damos un mini respiro para que Folium encuentre el punto
                setTimeout(function() {{
                    // Buscamos el círculo azul que Folium dibuja al encontrar algo
                    var circuloSeleccion = document.querySelector('.leaflet-marker-icon, .leaflet-control-search-location');
                    
                    // Si Folium encontró algo, el mapa tendrá una capa nueva temporal
                    mapa.eachLayer(function(l) {{
                        if (l.options && l.options.fillColor === '#2196f3') {{ // Color por defecto del buscador
                            mapa.flyTo(l.getLatLng(), 19, {{animate: true, duration: 2}});
                        }}
                    }});
                }}, 300);
            }}

            // Escuchar el Enter en el teclado
            inputBusqueda.addEventListener('keyup', function(e) {{
                if (e.key === 'Enter') {{
                    console.log("Enter detectado, forzando vuelo...");
                    forzarVuelo();
                }}
            }});

            // Escuchar el click en la lista de sugerencias
            document.addEventListener('click', function(e) {{
                if (e.target.classList.contains('search-tip')) {{
                    console.log("Sugerencia clickeada, forzando vuelo...");
                    forzarVuelo();
                }}
            }});

            clearInterval(monitorBuscador);
        }}
    }}, 500);
</script>
""")


estiloCssBuscador = """
<style>
.leaflet-control-search {
    position: fixed !important;
    top: 10px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 1000 !important;
    margin: 0 !important;
}
/* Movemos los botones de zoom originales a la derecha para que no molesten */
.leaflet-top.leaflet-left {
    top: 10px !important; /* Los baja un poco */
    left:10px !important;
}
</style>
"""


mapa.get_root().header.add_child(folium.Element(estiloCssBuscador))
mapa.get_root().html.add_child(script_zoom)
mapa.get_root().html.add_child(script_forzar_zoom_search)

mapa.get_root().header.add_child(
    folium.Element('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">')
)

# Guardar el mapa en un archivo HTML
folium.LayerControl().add_to(mapa)
mapa.save("C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\index.html")
print("Mapa generado como 'index.html'. Ábrelo en tu navegador.")