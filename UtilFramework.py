# Conjunto de métodos que serán utilizados por varios proyectos 
# Incrementador general de procesamiento que indica cuando van mas 10 o multiplos de 10
def incrementarNumeroContadorProcesamiento(cont):
    if cont>0 and cont % 10 == 0:
            print("archivos procesados:",cont)                       
    cont += 1
    return cont
