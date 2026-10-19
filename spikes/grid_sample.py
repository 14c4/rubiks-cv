import cv2
import numpy as np

# Guide grid: 3x3 cells, each CELL x CELL pixels, top-left corner at (GRID_X, GRID_Y).
# 640x480 frame -> 240x240 grid sits roughly in the middle.
GRID_X, GRID_Y = 200, 120
CELL = 80
# Sample only the inside of each cell. The sticker edges, the black plastic between
# stickers, and the drawn lines would all pollute the average.
MARGIN = 20


def cell_boxes():
    """Yield (row, col, x1, y1, x2, y2) for the sampling area of each of the 9 cells."""
    for row in range(3):
        for col in range(3):
            x1 = GRID_X + col * CELL + MARGIN
            y1 = GRID_Y + row * CELL + MARGIN
            x2 = GRID_X + (col + 1) * CELL - MARGIN
            y2 = GRID_Y + (row + 1) * CELL - MARGIN
            yield row, col, x1, y1, x2, y2


def sample_cells(frame):
    """Return a (3, 3, 3) array: mean B, G, R of each cell's sampling area."""
    means = np.zeros((3, 3, 3))
    for row, col, x1, y1, x2, y2 in cell_boxes():
        patch = frame[y1:y2, x1:x2]  # numpy: rows (y) first, then columns (x)
        means[row, col] = patch.mean(axis=(0, 1))
    return means


def convert_means(means):
    """Convert (3, 3, 3) BGR means to 8-bit HSV and Lab with the same shape.

    cv2.cvtColor treats a (3, 3, 3) uint8 array as a tiny 3x3 image, so one call converts all
    nine cells. We average in BGR first and convert afterwards: hue is an angle, so averaging
    hue values directly would be wrong near the red wrap-around.
    """
    bgr8 = np.round(means).astype(np.uint8)
    hsv = cv2.cvtColor(bgr8, cv2.COLOR_BGR2HSV)  # H 0-179 (degrees / 2), S 0-255, V 0-255
    lab = cv2.cvtColor(bgr8, cv2.COLOR_BGR2LAB)  # L 0-255 (scaled), a and b centered on 128
    return bgr8, hsv, lab


def draw_guide(frame):
    """Return a copy of frame with the grid drawn on it. The original stays untouched."""
    shown = frame.copy()
    # outer border of the whole grid
    cv2.rectangle(shown, (GRID_X, GRID_Y), (GRID_X + 3 * CELL, GRID_Y + 3 * CELL), (0, 255, 0), 2)
    # the small box inside each cell is the area that actually gets averaged
    for _, _, x1, y1, x2, y2 in cell_boxes():
        cv2.rectangle(shown, (x1, y1), (x2, y2), (0, 255, 0), 1)
    return shown


def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("error: camera not open")
        return

    print("space = sample the 9 cells and print them, q = quit")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("error: could not read a frame")
            break

        cv2.imshow("camera", draw_guide(frame))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord(" "):
            # sample from `frame`, not from the drawn copy, so the green lines are not included
            bgr, hsv, lab = convert_means(sample_cells(frame))
            print("--- cell (row,col)   BGR   |   HSV (H 0-179)   |   Lab (a,b centered on 128) ---")
            for row in range(3):
                for col in range(3):
                    print(f"({row},{col})  {bgr[row, col]}  |  {hsv[row, col]}  |  {lab[row, col]}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
