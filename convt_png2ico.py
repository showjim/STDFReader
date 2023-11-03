from PIL import Image

logo = Image.open(".\img\icon3.png")

logo.save(".\img\icon3.ico", format='ICO')#, sizes=[(128,128)])