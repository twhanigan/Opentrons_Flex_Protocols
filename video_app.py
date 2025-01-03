from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from v4l2py import Device
from starlette.responses import HTMLResponse
import uvicorn

#This is a working applicationt to stream the opentrons flex camera using v4l2py

device_path = "/dev/video2"
device_id = int(device_path.replace("/dev/video", ""))
app = FastAPI()

def gen_frames():
    with Device.from_id(device_id) as cam:
        for frame in cam:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame.data + b"\r\n"

@app.get("/", response_class=HTMLResponse)
async def index():
    return '<html><img src="/stream" /></html>'

@app.get("/stream")
async def stream():
    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

if __name__ == "__main__":
    uvicorn.run(
        "video_app:app",  # Replace 'app:app' with your module and FastAPI instance
        host="0.0.0.0",  # Listen on all available network interfaces
        port=8000,       # Port to serve the application
        reload=True      # Auto-reload on code changes (useful in development)
    )

#to watch the stream go to http://127.0.0.1:8000/