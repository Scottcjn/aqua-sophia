"""
AquaSophia — Camera Module
Captures images from USB webcam for Gemma 4 multimodal crop analysis.
Gemma sees the image + sensor data and can spot visual issues
(yellowing leaves, algae, wilting, root discoloration).
"""

import base64
import io
import logging
import os
import time
from pathlib import Path

log = logging.getLogger("aqua.camera")

# Image capture directory
CAPTURE_DIR = Path("captures")
CAPTURE_DIR.mkdir(exist_ok=True)


class CropCamera:
    """USB webcam capture for crop health monitoring."""

    def __init__(self, device: int = 0, resolution: tuple = (640, 480)):
        """
        Args:
            device: Camera index (0 = default USB webcam)
            resolution: (width, height) — keep small for Gemma context
        """
        self.device = device
        self.resolution = resolution
        self._cap = None

    def _ensure_open(self):
        if self._cap is None or not self._cap.isOpened():
            try:
                import cv2
                self._cap = cv2.VideoCapture(self.device)
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                if not self._cap.isOpened():
                    raise RuntimeError(f"Cannot open camera device {self.device}")
                log.info(f"Camera opened: device {self.device} @ {self.resolution}")
            except ImportError:
                raise ImportError("pip install opencv-python — needed for camera")

    def capture(self, save: bool = True) -> dict:
        """
        Capture a frame from the webcam.

        Returns:
            {
                "image_b64": "base64-encoded JPEG",
                "path": "/path/to/saved/image.jpg" (if save=True),
                "timestamp": float,
                "width": int,
                "height": int,
            }
        """
        import cv2

        self._ensure_open()

        # Grab a few frames to flush buffer (webcams buffer old frames)
        for _ in range(3):
            self._cap.read()

        ret, frame = self._cap.read()
        if not ret or frame is None:
            log.error("Camera capture failed")
            return None

        ts = time.time()
        h, w = frame.shape[:2]

        # Encode as JPEG
        _, jpeg_buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        jpeg_bytes = jpeg_buf.tobytes()
        b64 = base64.b64encode(jpeg_bytes).decode("ascii")

        result = {
            "image_b64": b64,
            "path": None,
            "timestamp": ts,
            "width": w,
            "height": h,
            "size_kb": len(jpeg_bytes) / 1024,
        }

        # Save to disk
        if save:
            fname = time.strftime("%Y%m%d_%H%M%S", time.localtime(ts)) + ".jpg"
            fpath = CAPTURE_DIR / fname
            with open(fpath, "wb") as f:
                f.write(jpeg_bytes)
            result["path"] = str(fpath)
            log.info(f"Captured {w}x{h} → {fpath} ({result['size_kb']:.0f} KB)")

        return result

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class StubCamera:
    """Fake camera for testing without hardware."""

    def capture(self, save: bool = True) -> dict:
        # 1x1 green pixel JPEG as base64 placeholder
        b64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAFRABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8ASwA//9k="
        return {
            "image_b64": b64,
            "path": None,
            "timestamp": time.time(),
            "width": 1,
            "height": 1,
            "size_kb": 0.1,
        }

    def release(self):
        pass


def create_camera(mode: str = "auto") -> CropCamera | StubCamera:
    """Create camera based on availability."""
    if mode == "stub":
        log.info("Using stub camera (no hardware)")
        return StubCamera()

    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.release()
            log.info("USB webcam detected")
            return CropCamera()
        else:
            log.warning("No webcam found, using stub camera")
            return StubCamera()
    except ImportError:
        log.warning("opencv-python not installed, using stub camera")
        return StubCamera()
