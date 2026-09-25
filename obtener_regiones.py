import cv2             # <--- opencv
import pickle
import sys

# Igual que obtener_espacios.py del profe, pero en vez de marcar 69 espacios de
# estacionamiento marcamos DOS rectangulos sobre la vereda, a la altura de los pies:
#   zona A (a la izquierda)  y  zona B (a la derecha)
# Si alguien pisa primero A y luego B -> camina hacia la DERECHA.
# Si pisa primero B y luego A          -> camina hacia la IZQUIERDA.
# Nosotros usamos A = (130, 583, 45, 147) y B = (290, 583, 45, 147) sobre el video
# estabilizado de 540x960.

video = sys.argv[1] if len(sys.argv) > 1 else 'video_estable.mp4'
carriles = int(sys.argv[2]) if len(sys.argv) > 2 else 1

# tomamos el primer frame del video estabilizado como referencia
cap = cv2.VideoCapture(video)
check, img = cap.read()
cv2.imwrite('referencia.png', img)

regiones = []   # lista de (zonaA, zonaB), cada zona es (x, y, w, h)

for c in range(carriles):
    print(f'carril {c+1}: marca la zona A (afuera) y luego la zona B (adentro)')
    zonaA = cv2.selectROI('zona A', img, False)
    cv2.destroyWindow('zona A')
    zonaB = cv2.selectROI('zona B', img, False)
    cv2.destroyWindow('zona B')
    regiones.append((zonaA, zonaB))

    for (x, y, w, h), (x2, y2, w2, h2) in regiones:
        # referencial: ver los rectangulos agregados
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        cv2.rectangle(img, (x2, y2), (x2+w2, y2+h2), (0, 0, 255), 2)

with open('regiones.pkl', 'wb') as file:
    # guardar el archivo
    pickle.dump(regiones, file)
