import cv2
import pickle
import numpy as np
import matplotlib.pyplot as plt

# ¿Por donde camina la gente?
# Sumamos la imagen dilatada (mismo procesamiento del profe) de todos los frames.
# - Lo que esta quieto (tachos, jardinera, gradas) sale blanco en casi todos los frames.
# - El piso vacio sale negro casi siempre.
# - Por donde pasa gente, el piso sale blanco "a veces".
# Asi que la fraccion de frames en que cada pixel fue blanco nos dice por donde camina la gente.

video = cv2.VideoCapture('video_estable.mp4')
kernel = np.ones((5, 5), np.int8)
suma = None
n = 0
while True:
    check, img = video.read()
    if not check:
        break
    imgBN = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgTH = cv2.adaptiveThreshold(imgBN, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)
    imgMedian = cv2.medianBlur(imgTH, 5)
    imgDil = cv2.dilate(imgMedian, kernel)
    if suma is None:
        suma = np.zeros(imgDil.shape, np.float64)
    suma += imgDil > 0
    n += 1

frecuencia = suma / n                      # entre 0 y 1
np.save('frecuencia.npy', frecuencia)

# solo nos interesa el piso (debajo de la jardinera y antes de las gradas)
Y0, Y1 = 588, 770
piso = frecuencia[Y0:Y1].copy()
piso[piso > 0.08] = 0                      # lo que esta blanco muy seguido es fondo quieto (manchas, bordes)
piso[:, :15] = 0                           # bordes negros que deja la estabilizacion
piso[:, 495:] = 0
piso = cv2.GaussianBlur(piso, (31, 31), 0) # suavizar, como en el notebook de thresholding

with open('regiones.pkl', 'rb') as file:
    zonaA, zonaB = pickle.load(file)[0]
ref = cv2.cvtColor(cv2.imread('referencia.png'), cv2.COLOR_BGR2RGB)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={'width_ratios': [3, 1]})
ax1.imshow(ref[500:800])
im = ax1.imshow(piso * 100, cmap='hot', alpha=0.65, extent=(0, ref.shape[1], Y1 - 500, Y0 - 500), vmin=0, vmax=2.5)
for (x, y, w, h), nombre in ((zonaA, 'A'), (zonaB, 'B')):
    ax1.add_patch(plt.Rectangle((x, y - 500), w, h, fill=False, color='cyan', lw=2))
    ax1.text(x + 12, y - 508, nombre, color='cyan', fontsize=14)
ax1.set_xlim(0, ref.shape[1])
ax1.set_ylim(300, 0)
ax1.set_title('Por donde camina la gente (10 min)', pad=22)
ax1.axis('off')
fig.colorbar(im, ax=ax1, label='% del tiempo con alguien encima', fraction=0.03)

# perfil: promedio de cada fila del piso = que tan lejos de la camara camina la gente
perfil = piso.mean(axis=1) * 100
ax2.barh(np.arange(Y0, Y1), perfil, height=1, color='#e0592a')
ax2.invert_yaxis()
ax2.set_xlabel('% del tiempo ocupado')
ax2.set_ylabel('fila de la imagen (y)')
ax2.set_title('jardinera arriba,\ngradas abajo')
plt.tight_layout()
plt.savefig('resultados/mapa_calor.png', dpi=150)
print('fila mas transitada: y =', Y0 + int(np.argmax(perfil)))
print('ocupacion junto a la jardinera (y<630): %.2f %%' % perfil[:630 - Y0].mean())
print('ocupacion cerca de la camara (y>700): %.2f %%' % perfil[700 - Y0:].mean())
