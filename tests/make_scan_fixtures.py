"""Fake camera videos for the scanner tests (y4m files, ignored by git). Needs Pillow, NumPy and OpenCV.
  scan_good.y4m  1280x720, the dm barcode of fixture_dm_barcode.jpg large and sharp (a good scan)
  scan_hard.y4m  640x480, the same barcode only about 2 pixels per bar width, with shaking and sensor noise: this is what made ZXing
                 read 6072101076189 / 8070167076189 instead of the real 4070765076189
  scan_qr.y4m    640x480, only a QR code (dm prints one next to the barcode): the app must not take it for a barcode
  scan_blank.y4m 640x480, nothing to read (the voting test feeds scripted readings instead)
The barcode photo is a crop of a real dmBio package (Udon tészta, 200 g, 4070765076189)."""
import random
import cv2
import numpy as np
from PIL import Image

CODE = '4070765076189'
src = Image.open('fixture_dm_barcode.jpg').convert('RGB')
BARS = (75, 38, 420, 285)   # x0, y0, x1, y1 of the bars inside the crop; used to size the barcode
BG = (122, 58, 140)         # package purple


def y4m(path, frames, w, h, fps=10):
    with open(path, 'wb') as f:
        f.write(f'YUV4MPEG2 W{w} H{h} F{fps}:1 Ip A1:1 C420jpeg\n'.encode())
        for im in frames:
            yuv = im.convert('YCbCr')
            f.write(b'FRAME\n' + yuv.getchannel(0).tobytes() + yuv.getchannel(1).resize((w // 2, h // 2)).tobytes() + yuv.getchannel(2).resize((w // 2, h // 2)).tobytes())


def scene(w, h, bar_px, seed, shake=0, zoom=0.0, noise=0.0):
    """barcode photo scaled so that the bars are bar_px wide, in the middle of a w x h picture"""
    rnd = random.Random(seed)
    scale = bar_px / (BARS[2] - BARS[0]) * (1 + (rnd.random() - .5) * 2 * zoom)
    im = src.resize((round(src.width * scale), round(src.height * scale)), Image.LANCZOS)
    canvas = Image.new('RGB', (w, h), BG)
    canvas.paste(im, ((w - im.width) // 2 + round((rnd.random() - .5) * 2 * shake), (h - im.height) // 2 + round((rnd.random() - .5) * 2 * shake)))
    if noise:
        a = np.asarray(canvas, dtype=np.float32)
        a += np.random.RandomState(seed).normal(0, noise, a.shape) + (rnd.random() - .5) * 10
        canvas = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return canvas


y4m('scan_good.y4m', [scene(1280, 720, 600, i) for i in range(20)], 1280, 720)
y4m('scan_hard.y4m', [scene(640, 480, 135, i, shake=6, zoom=0.03, noise=3) for i in range(30)], 640, 480)
qr = cv2.QRCodeEncoder.create().encode('https://dm.de/genussreise')
qr = cv2.resize(qr, (300, 300), interpolation=cv2.INTER_NEAREST)
qr = cv2.copyMakeBorder(qr, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
qi = Image.fromarray(qr).convert('RGB').resize((640, 480))
y4m('scan_qr.y4m', [qi] * 10, 640, 480)
y4m('scan_blank.y4m', [Image.new('RGB', (640, 480), BG)] * 10, 640, 480)
print('ok')
