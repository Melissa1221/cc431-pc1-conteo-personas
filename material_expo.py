import cv2
import pickle
import numpy as np
import matplotlib.pyplot as plt

# Material de apoyo para la exposicion:
# 1. grafico de cuanto se movio la camara (sale de estabilizar.py)
# 2. video lado a lado: original vs estabilizado, acelerado x20
# 3. video del procesamiento paso a paso (como los imshow comentados del profe)

ANCHO, ALTO = 540, 960
with open('regiones.pkl', 'rb') as file:
    zonaA, zonaB = pickle.load(file)[0]

# ---------- 1. movimiento de la camara ----------
mov = np.load('movimiento.npy')
fps = 29.945
t = np.arange(len(mov)) / fps / 60
plt.figure(figsize=(9, 4))
plt.plot(t, mov[:, 0], label='horizontal (dx)')
plt.plot(t, mov[:, 1], label='vertical (dy)')
plt.xlabel('minuto del video')
plt.ylabel('desplazamiento de la camara (px)')
plt.title('Cuanto se movio el celular respecto al primer frame')
plt.axhline(0, color='k', lw=0.5)
plt.legend()
plt.tight_layout()
plt.savefig('movimiento_camara.png', dpi=150)
print('max |dx|, |dy| =', np.abs(mov[:, :2]).max(axis=0))


def dibujar_zonas(img):
    for x, y, w, h in (zonaA, zonaB):
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 255), 2)
    # linea fija en el borde de la jardinera: en el video estable no se mueve
    cv2.line(img, (0, 580), (ANCHO, 580), (0, 0, 255), 1)


# ---------- 2. original vs estable (timelapse x20) ----------
orig = cv2.VideoCapture('video_original.mp4')
est = cv2.VideoCapture('video_estable.mp4')
out = cv2.VideoWriter('comparacion_estabilizacion.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, (ANCHO * 2, ALTO))
i = 0
while True:
    ok1, a = orig.read()
    ok2, b = est.read()
    if not ok1 or not ok2:
        break
    if i % 20 == 0:
        a = cv2.resize(a, (ANCHO, ALTO))
        dibujar_zonas(a)
        dibujar_zonas(b)
        cv2.putText(a, 'ORIGINAL', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        cv2.putText(b, 'ESTABILIZADO', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
        cv2.putText(a, f'x20  t={i / fps / 60:.1f} min', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        out.write(np.hstack([a, b]))
    i += 1
out.release()

# ---------- 3. procesamiento paso a paso (seg 405 a 420) ----------
est = cv2.VideoCapture('video_estable.mp4')
est.set(cv2.CAP_PROP_POS_FRAMES, int(405 * fps))
kernel = np.ones((5, 5), np.int8)
out = cv2.VideoWriter('procesamiento_paso_a_paso.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps, (ANCHO * 2, 440 * 2))
for k in range(int(15 * fps)):
    ok, img = est.read()
    if not ok:
        break
    imgBN = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgTH = cv2.adaptiveThreshold(imgBN, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)
    imgMedian = cv2.medianBlur(imgTH, 5)
    imgDil = cv2.dilate(imgMedian, kernel)
    paneles = []
    for p, nombre in ((img, '1. original'), (imgTH, '2. umbral adaptativo'),
                      (imgMedian, '3. filtro de mediana'), (imgDil, '4. dilatacion')):
        if len(p.shape) == 2:
            p = cv2.cvtColor(p, cv2.COLOR_GRAY2BGR)
        p = p[340:780].copy()
        for x, y, w, h in (zonaA, zonaB):
            cv2.rectangle(p, (x, y - 340), (x+w, y - 340 + h), (0, 255, 255), 2)
        cv2.putText(p, nombre, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        paneles.append(p)
    out.write(np.vstack([np.hstack(paneles[:2]), np.hstack(paneles[2:])]))
out.release()
print('listo: movimiento_camara.png, comparacion_estabilizacion.mp4, procesamiento_paso_a_paso.mp4')
