import cv2

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("error: camera not open")

print("backend:", cap.getBackendName())
print("size:", cap.get(cv2.CAP_PROP_FRAME_WIDTH), "x", cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print("fps reported:", cap.get(cv2.CAP_PROP_FPS))

while True: 
    ok, frame = cap.read()
    if not ok:
        print('error: camera not working lol')
        break
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    cv2.rectangle(frame, (200, 120), (440, 360), (0, 255, 0), 2)
    cv2.imshow("camera", frame)

patch = frame[120:200, 200:280]
print(patch.shape)
print(patch.mean(axis=(0,1)))

cap.release()
cv2.destroyAllWindows()