import pandas as pd
import simplejson as json

# 1. Cargar el JSON que generaste
with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\viajes.json', 'r') as f:
    datos = json.load(f)

df = pd.DataFrame(datos)

# 2. Agrupar fotos por ubicación exacta
# Esto crea una lista de nombres de archivos para cada coordenada
df['lat']=df['lat'].round(4)
df['lon']=df['lon'].round(4)
df_agrupado = df.groupby(['lat', 'lon' ]).agg({
    'archivo': lambda x: list(x),
    'fecha': 'min'  # Tomamos la fecha de la primera foto del grupo
}).reset_index()

# 3. Guardar el JSON final optimizado para el mapa
resultado_final = df_agrupado.to_dict(orient='records')
with open('C:\\z\\desarrollo\\varios\\python\\practica\\juegos\\fotoMapa\\fotosFinal.json', 'w') as f:
    json.dump(resultado_final, f, indent=4, ignore_nan=True)

print(f"Proceso terminado. De {len(df)} fotos, creamos {len(df_agrupado)} puntos en el mapa.")