import cv2
import numpy as np
import sys

# Estabilizacion con el DOMINIO DE LA FRECUENCIA (clase del 18/09, semana 3)
# Diapositivas "Dominio de la frecuencia": 34 (impulso desplazado), 40 (propiedad de
# desplazamiento) y 53 (reconstruccion con magnitud y fase).
#
# Lo que vimos: si una imagen se DESPLAZA, la magnitud de su transformada de
# Fourier no cambia; solo cambia la FASE (se le suma un termino lineal).
# Entonces, comparando la fase de dos frames podemos saber cuanto se movio:
#
#   F1 = FFT(referencia),  F2 = FFT(frame actual)
#   R  = F2 * conj(F1) / |F2 * conj(F1)|     <- nos quedamos solo con la diferencia de fase
#   r  = FFT inversa de R                    <- sale un PICO en la posicion (dx, dy)
#
# Esto se llama "correlacion de fase". Despues movemos el frame al reves con warpAffine.
# La FFT trabaja con UN solo canal (lo que subrayo el profe), por eso usamos la imagen en gris.

entrada = sys.argv[1] if len(sys.argv) > 1 else 'video_original.mp4'
salida = sys.argv[2] if len(sys.argv) > 2 else 'video_estable.mp4'
ANCHO, ALTO = 540, 960
DURACION = 599

video = cv2.VideoCapture(entrada)
fps = video.get(cv2.CAP_PROP_FPS)
total = int(DURACION * fps)

check, ref = video.read()
ref = cv2.resize(ref, (ANCHO, ALTO))

# solo usamos la parte de abajo (piso, gradas, tachos): arriba los arboles se mueven con el viento
Y0 = int(ALTO * 0.45)
# ventana de Hanning: baja los bordes a cero para que el corte de la imagen no meta frecuencias falsas
ventana = np.outer(np.hanning(ALTO - Y0), np.hanning(ANCHO))


def fft_de(img):
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[Y0:].astype(np.float64)
    gris = gris - gris.mean()
    return np.fft.fft2(gris * ventana)


F1 = fft_de(ref)

out = cv2.VideoWriter(salida, cv2.VideoWriter_fourcc(*'mp4v'), fps, (ANCHO, ALTO))
out.write(ref)
movimiento = []
dx_ant, dy_ant = 0.0, 0.0
descartados = 0

for i in range(1, total):
    check, img = video.read()
    if not check:
        break
    img = cv2.resize(img, (ANCHO, ALTO))
    F2 = fft_de(img)

    R = F2 * np.conj(F1)
    R = R / (np.abs(R) + 1e-9)             # solo la fase
    r = np.abs(np.fft.ifft2(R))            # vuelve al espacio: un pico
    py, px = np.unravel_index(np.argmax(r), r.shape)
    # afinar el pico: promedio ponderado de sus vecinos 3x3 -> desplazamiento con decimales
    filas = [(py + k) % r.shape[0] for k in (-1, 0, 1)]
    cols = [(px + k) % r.shape[1] for k in (-1, 0, 1)]
    vecinos = r[np.ix_(filas, cols)]
    ajuste_y = (vecinos.sum(axis=1) * np.array([-1, 0, 1])).sum() / vecinos.sum()
    ajuste_x = (vecinos.sum(axis=0) * np.array([-1, 0, 1])).sum() / vecinos.sum()
    # la FFT es circular: un pico cerca del final significa desplazamiento negativo
    dy = (py if py < r.shape[0] / 2 else py - r.shape[0]) + ajuste_y
    dx = (px if px < r.shape[1] / 2 else px - r.shape[1]) + ajuste_x

    # control: la mano no mueve la camara 15 px en 1/30 s (alguien tapo la camara)
    if abs(dx - dx_ant) > 15 or abs(dy - dy_ant) > 15:
        dx, dy = dx_ant, dy_ant
        descartados += 1
    dx_ant, dy_ant = dx, dy

    # mover el frame al reves (traslacion pura con warpAffine, como en el notebook de repaso)
    m = np.float64([[1, 0, -dx], [0, 1, -dy]])
    estable = cv2.warpAffine(img, m, (ANCHO, ALTO))
    out.write(estable)
    movimiento.append([dx, dy])
    if i % 1000 == 0:
        print(f'{i}/{total}  dx={dx:.1f} dy={dy:.1f}')

out.release()
movimiento = np.array(movimiento)
np.save('movimiento.npy', movimiento)
print('desplazamiento maximo corregido (px):', np.abs(movimiento).max(axis=0))
print('frames descartados:', descartados)
print('listo:', salida)
