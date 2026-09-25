import cv2
import numpy as np
import sys

# Estabilizacion de video (opcional de la PC1, 2 puntos)
#
# Problema: grabamos con el celular en la mano, la imagen se mueve unos pixeles
# todo el tiempo. El script del profe cuenta pixeles dentro de rectangulos FIJOS,
# asi que si la camara se mueve el rectangulo ya no cae sobre el mismo pedazo de piso.
#
# Solucion: alinear cada frame contra un frame de referencia (el primero).
# 1. En la referencia buscamos esquinas faciles de seguir     -> goodFeaturesToTrack
#    (solo en la parte de abajo: piso, gradas, tachos. Arriba estan los arboles
#     y las hojas se mueven con el viento, no sirven)
# 2. Buscamos esas mismas esquinas en el frame actual          -> calcOpticalFlowPyrLK
#    (flujo optico piramidal, le damos como pista donde estaban en el frame anterior)
# 3. Con los pares de puntos calculamos cuanto se movio la camara:
#    traslacion (dx, dy), rotacion y escala                     -> estimateAffinePartial2D
#    RANSAC descarta los puntos que caen sobre personas caminando
# 4. Aplicamos la transformacion inversa al frame               -> warpAffine
#    y queda "pegado" a la referencia

entrada = sys.argv[1] if len(sys.argv) > 1 else 'video_original.mp4'
salida = sys.argv[2] if len(sys.argv) > 2 else 'video_estable.mp4'
ANCHO, ALTO = 540, 960        # reducimos de 1080x1920 a la mitad (mas rapido)
DURACION = 599                # segundos (el enunciado pide maximo 10 min)

video = cv2.VideoCapture(entrada)
fps = video.get(cv2.CAP_PROP_FPS)
total = int(DURACION * fps)

check, ref = video.read()
ref = cv2.resize(ref, (ANCHO, ALTO))
refBN = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
cv2.imwrite('referencia.png', ref)

# mascara: solo buscamos esquinas de la mitad de la imagen para abajo
mascara = np.zeros_like(refBN)
mascara[int(ALTO * 0.45):, :] = 255
pts_ref = cv2.goodFeaturesToTrack(refBN, maxCorners=300, qualityLevel=0.01, minDistance=10, mask=mascara)

out = cv2.VideoWriter(salida, cv2.VideoWriter_fourcc(*'mp4v'), fps, (ANCHO, ALTO))
out.write(ref)

m_ant = np.float64([[1, 0, 0], [0, 1, 0]])
descartados = 0
seguidos = 0
pts_prev = pts_ref.copy()   # donde estaban los puntos en el frame anterior
movimiento = []             # (dx, dy, angulo, tapado) de cada frame respecto a la referencia

for i in range(1, total):
    check, img = video.read()
    if not check:
        break
    img = cv2.resize(img, (ANCHO, ALTO))
    imgBN = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    pts, status, err = cv2.calcOpticalFlowPyrLK(refBN, imgBN, pts_ref, pts_prev.copy(),
                                                winSize=(31, 31), maxLevel=4,
                                                flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
    ok = status.flatten() == 1
    m = None
    if ok.sum() > 20:
        # m lleva un punto de la referencia a donde esta ahora
        m, inliers = cv2.estimateAffinePartial2D(pts_ref[ok], pts[ok], method=cv2.RANSAC,
                                                 ransacReprojThreshold=2)
    # control: la mano no puede mover la camara 15 px o 2 grados en 1/30 de segundo.
    # Si pasa, es porque alguien tapo la camara (paso muy cerca) y la estimacion es basura.
    if m is not None:
        escala = np.sqrt(m[0, 0] ** 2 + m[1, 0] ** 2)
        salto = np.abs(m[:, 2] - m_ant[:, 2]).max()
        giro = abs(np.degrees(np.arctan2(m[1, 0], m[0, 0]) - np.arctan2(m_ant[1, 0], m_ant[0, 0])))
        confiable = inliers.sum() > 0.6 * ok.sum()
        # si llevamos mas de 1 s rechazando, aceptamos un salto grande solo si casi
        # todos los puntos estan de acuerdo (la camara si se movio mientras la tapaban)
        if seguidos > 30 and confiable and giro < 5 and abs(escala - 1) < 0.1:
            pass
        elif salto > 15 or giro > 2 or abs(escala - 1) > 0.1 or inliers.sum() < 15:
            m = None
    if m is not None:
        seguidos = 0
    tapado = m is None
    if m is None:
        # si no se pudo estimar, usamos el ultimo movimiento conocido
        m = m_ant
        descartados += 1
        seguidos += 1
    m_ant = m

    # proxima pista: donde predice m que esten los puntos
    pts_prev = cv2.transform(pts_ref, m)

    # invertimos m para regresar el frame a la posicion de la referencia
    m_inv = cv2.invertAffineTransform(m)
    estable = cv2.warpAffine(img, m_inv, (ANCHO, ALTO))
    out.write(estable)

    movimiento.append([m[0, 2], m[1, 2], np.degrees(np.arctan2(m[1, 0], m[0, 0])), tapado])
    if i % 1000 == 0:
        print(f'{i}/{total}  dx={m[0, 2]:.1f} dy={m[1, 2]:.1f}')

out.release()
movimiento = np.array(movimiento)
np.save('movimiento.npy', movimiento)
print('desplazamiento maximo corregido (px):', np.abs(movimiento[:, :2]).max(axis=0))
print('frames con estimacion descartada:', descartados)
print('listo:', salida)
