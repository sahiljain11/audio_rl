import cv2
import os

def write_annotation(path: str, word: str) -> None:

    img = cv2.imread(path)

    font = cv2.FONT_HERSHEY_SIMPLEX
    org = (20, 20)
    black = (0, 0, 0)
    white = (255, 255, 255)
    fontScale = 1

    img = cv2.putText(img, word, org, font, fontScale, black, 2, cv2.LINE_AA)
    img = cv2.putText(img, word, org, font, fontScale, white, 1, cv2.LINE_AA)

    os.remove(path)
    cv2.imwrite(path, img)

    return