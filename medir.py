import cv2
import pickle
import numpy as np
import sys

# Paso 1: medir. Recorre todo el video y guarda, para cada frame, cuantos pixeles
# blancos hay en cada zona (lo mismo que hace el profe con cada espacio del
# estacionamiento). Asi despues podemos elegir el umbral mirando los datos.

video_path = sys.argv[1] if len(sys.argv) > 1 else 'video_estable.mp4'

with open('regiones.pkl', 'rb') as file:
    regiones = pickle.load(file)

zonas = []
for zonaA, zonaB in regiones:
    zonas.append(zonaA)
    zonas.append(zonaB)

video = cv2.VideoCapture(video_path)
kernel = np.ones((5, 5), np.int8)
conteos = []

while True:
    check, img = video.read()
    if not check:
        break
    # mismo procesamiento que main.py del profe
    imgBN = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgTH = cv2.adaptiveThreshold(imgBN, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)
    imgMedian = cv2.medianBlur(imgTH, 5)
    imgDil = cv2.dilate(imgMedian, kernel)

    fila = []
    for x, y, w, h in zonas:
        fila.append(cv2.countNonZero(imgDil[y:y+h, x:x+w]))
    conteos.append(fila)

conteos = np.array(conteos)
np.save('conteos.npy', conteos)
print('frames:', len(conteos))
print('mediana por zona (fondo vacio):', np.median(conteos, axis=0))

# umbral de cada zona = fondo (mediana, porque la mayor parte del tiempo la zona esta
# vacia) + un margen de 200 pixeles. Es el "if count < 900" del profe, pero calculado.
MARGEN = 200
fondo = np.median(conteos, axis=0)
datos = {'fondo': fondo.tolist(), 'umbral': (fondo + MARGEN).tolist()}
with open('umbrales.pkl', 'wb') as file:
    pickle.dump(datos, file)
print('umbrales:', datos['umbral'])
