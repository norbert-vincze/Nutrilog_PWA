from PIL import Image, ImageDraw
L=['0001101','0011001','0010011','0111101','0100011','0110001','0101111','0111011','0110111','0001011']
G=['0100111','0110011','0011011','0100001','0011101','0111001','0000101','0010001','0001001','0010111']
R=['1110010','1100110','1101100','1000010','1011100','1001110','1010000','1000100','1001000','1110100']
PAR=['LLLLLL','LLGLGG','LLGGLG','LLGGGL','LGLLGG','LGGLLG','LGGGLL','LGLGLG','LGLGGL','LGGLGL']
code='5901234123457'
d=[int(x) for x in code]
chk=(10-(sum(d[i]*(1 if i%2==0 else 3) for i in range(12))%10))%10
assert chk==d[12], chk
bits='101'
for i,ch in enumerate(d[1:7]):
    bits+= (L if PAR[d[0]][i]=='L' else G)[ch]
bits+='01010'
for ch in d[7:]:
    bits+=R[ch]
bits+='101'
W,H=640,480; mod=4; qz=12
bw=len(bits)*mod
im=Image.new('RGB',(W,H),'white'); dr=ImageDraw.Draw(im)
x0=(W-bw)//2
for i,b in enumerate(bits):
    if b=='1': dr.rectangle([x0+i*mod,150,x0+(i+1)*mod-1,330],fill='black')
im.save('bar.png')
# y4m (I420)
yuv=im.convert('YCbCr')
Y=yuv.getchannel(0).tobytes()
Cb=yuv.getchannel(1).resize((W//2,H//2)).tobytes()
Cr=yuv.getchannel(2).resize((W//2,H//2)).tobytes()
with open('bar.y4m','wb') as f:
    f.write(f'YUV4MPEG2 W{W} H{H} F10:1 Ip A1:1 C420jpeg\n'.encode())
    for _ in range(30):
        f.write(b'FRAME\n'+Y+Cb+Cr)
print('ok',bits.__len__())
