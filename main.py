import cv2
import pickle
import numpy as np
import sys

# Conteo de personas que cruzan la vereda (PC1 - CC431)
# Basado en main.py del profe (deteccion de espacios de estacionamiento):
#   escala de grises -> umbral adaptativo -> mediana -> dilatacion -> countNonZero
#
# Lo nuevo: en vez de ver si UN rectangulo esta ocupado, usamos DOS rectangulos
# sobre la vereda (zona A a la izquierda, zona B a la derecha).
# Cada vez que alguien pisa una zona, el conteo de pixeles blancos sube y baja:
# eso es un "pulso". Una persona que cruza deja un pulso en A y otro en B.
#   pulso en A y DESPUES pulso en B  -> camina hacia la DERECHA
#   pulso en B y DESPUES pulso en A  -> camina hacia la IZQUIERDA
# Si un pulso no tiene pareja en la otra zona (alguien que se paro, se dio la
# vuelta o solo piso una zona) no se cuenta.

video_path = sys.argv[1] if len(sys.argv) > 1 else 'video_estable.mp4'
salida = sys.argv[2] if len(sys.argv) > 2 else 'video_resultado.mp4'
MOSTRAR = '--mostrar' in sys.argv     # ver la ventana en vivo (como el profe)

with open('regiones.pkl', 'rb') as file:
    zonaA, zonaB = pickle.load(file)[0]

# umbral de cada zona: pixeles blancos con la zona VACIA + margen (lo calcula medir.py)
# Es el "if count < 900" del profe, pero medido en vez de puesto a ojo.
with open('umbrales.pkl', 'rb') as file:
    datos = pickle.load(file)
fondo = datos['fondo']
umbral = datos['umbral']

FRAMES_ON = 2        # frames seguidos sobre el umbral para decir "hay alguien"
FRAMES_OFF = 3       # frames seguidos bajo el umbral para decir "ya se fue"
MAX_SEG = 3.0        # un cruce de A a B no demora mas de 3 segundos
MASA_GRUPO = 35000   # si las dos zonas se llenan tanto, son 2 personas juntas

video = cv2.VideoCapture(video_path)
fps = video.get(cv2.CAP_PROP_FPS)
w = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
out = cv2.VideoWriter(salida, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
kernel = np.ones((5, 5), np.int8)

zonas = [zonaA, zonaB]
ocupada = [False, False]
racha = [0, 0]
masa = [0, 0]            # suma de pixeles (sobre el fondo) durante el pulso
suma_t = [0, 0]          # para sacar el instante central del pulso
pendientes = [[], []]    # pulsos terminados que todavia no tienen pareja: (t, masa)

izquierda = 0
derecha = 0
eventos = []             # (segundo, direccion, personas)
aviso = None             # flecha que se dibuja unos frames cuando se cuenta a alguien
frame = 0

while True:
    check, img = video.read()
    if not check:
        break
    frame += 1
    t = frame / fps

    # ---- mismo procesamiento que el profe ----
    imgBN = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgTH = cv2.adaptiveThreshold(imgBN, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)
    imgMedian = cv2.medianBlur(imgTH, 5)
    imgDil = cv2.dilate(imgMedian, kernel)

    for z in range(2):
        x, y, zw, zh = zonas[z]
        espacio = imgDil[y:y+zh, x:x+zw]
        count = cv2.countNonZero(espacio)
        hay_alguien = count > umbral[z]

        # si la zona esta ocupada, vamos acumulando el pulso
        if ocupada[z]:
            exceso = max(count - fondo[z], 0)
            masa[z] += exceso
            suma_t[z] += exceso * t

        # histeresis: el estado cambia solo si se mantiene varios frames
        if hay_alguien != ocupada[z]:
            racha[z] += 1
            if racha[z] >= (FRAMES_ON if hay_alguien else FRAMES_OFF):
                ocupada[z] = hay_alguien
                racha[z] = 0
                if hay_alguien:
                    # empieza un pulso
                    masa[z] = 0
                    suma_t[z] = 0
                else:
                    # termina un pulso: su instante central
                    t_centro = suma_t[z] / masa[z] if masa[z] > 0 else t
                    otra = 1 - z
                    # buscar en la otra zona el pulso sin pareja mas cercano en el tiempo
                    mejor = None
                    for p in pendientes[otra]:
                        dt = abs(t_centro - p[0])
                        if 0.1 < dt < MAX_SEG and (mejor is None or dt < abs(t_centro - mejor[0])):
                            mejor = p
                    if mejor is None:
                        pendientes[z].append((t_centro, masa[z]))
                    else:
                        pendientes[otra].remove(mejor)
                        # el pulso de A y el de B
                        tA, mA = (t_centro, masa[z]) if z == 0 else mejor
                        tB, mB = (t_centro, masa[z]) if z == 1 else mejor
                        personas = 2 if min(mA, mB) > MASA_GRUPO else 1
                        if tA < tB:
                            derecha += personas
                            eventos.append((t, 'derecha', personas))
                            aviso = ('->', personas, frame)
                        else:
                            izquierda += personas
                            eventos.append((t, 'izquierda', personas))
                            aviso = ('<-', personas, frame)
        else:
            racha[z] = 0

        color = (0, 0, 255) if ocupada[z] else (0, 255, 0)
        cv2.rectangle(img, (x, y), (x+zw, y+zh), color, 2)
        cv2.putText(img, 'AB'[z] + ' ' + str(count), (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    # los pulsos sin pareja se olvidan despues de MAX_SEG
    for z in range(2):
        pendientes[z] = [p for p in pendientes[z] if t - p[0] < MAX_SEG + 1]

    # ---- panel con los contadores ----
    cv2.rectangle(img, (0, 0), (w, 95), (0, 0, 0), -1)
    minuto = int(t) // 60
    seg = int(t) % 60
    cv2.putText(img, f'<- izquierda: {izquierda}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    cv2.putText(img, f'-> derecha: {derecha}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.putText(img, f'total: {izquierda + derecha}   t={minuto:02d}:{seg:02d}', (10, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    if aviso is not None and frame - aviso[2] < fps:
        texto = aviso[0] + ' +' + str(aviso[1])
        cv2.putText(img, texto, (zonaA[0] + 20, zonaA[1] + zonaA[3] + 45), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3)
    out.write(img)

    if MOSTRAR:
        cv2.imshow('video', img)
        # cv2.imshow('video Dilatada', imgDil)
        if cv2.waitKey(1) == 27:
            break

out.release()
with open('eventos.pkl', 'wb') as file:
    pickle.dump(eventos, file)
print('hacia la izquierda:', izquierda)
print('hacia la derecha:', derecha)
print('total:', izquierda + derecha, 'en', round(t / 60, 2), 'min')
