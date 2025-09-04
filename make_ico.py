from PIL import Image
src = r"assets/tucumind.png"
dst = r"assets/tucumind.ico"
img = Image.open(src).convert("RGBA")
w, h = img.size
if w != h:
    s = max(w, h)
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    canvas.paste(img, ((s - w)//2, (s - h)//2))
    img = canvas
img.save(dst, sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("ICO creado:", dst)
