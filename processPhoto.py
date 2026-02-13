import pandas as pd
import simplejson as json

# 1. Cargar el JSON generado
with open('data/viajes.json', 'r') as f:
    datos = json.load(f)

df = pd.DataFrame(datos)

# 2. Agrupar fotos por ubicación exacta
# Esto crea una lista de nombres de archivos para cada coordenada
df['lat']=df['lat'].round(4)
df['lon']=df['lon'].round(4)
df_agrupado = df.groupby(['lat', 'lon' ]).apply(
    lambda x: pd.Series({
        # Creamos la lista de objetos {nombre, fecha}
        'archivo': [
            {"nombre": arc, "fecha": fec} 
            for arc, fec in zip(x['archivo'], x['fecha'])
        ],
        # Mantenemos la fecha mínima para referencia del grupo si lo necesitas
        'fecha_min': x['fecha'].min()
    }),
    include_groups=False
).reset_index()

# 3. Guardar el JSON final optimizado para el mapa
resultado_final = df_agrupado.to_dict(orient='records')
with open('data/fotosFinal.json', 'w') as f:
    json.dump(resultado_final, f, indent=4, ignore_nan=True)

print(f"Proceso terminado. De {len(df)} fotos, creamos {len(df_agrupado)} puntos en el mapa.")