from __future__ import annotations
import os
import numpy as np

MODEL_PATH = os.environ.get("HAKILIX_MODEL_PATH", "/app/models/hakilix_risk_v1.onnx")
MODEL_VERSION = "hakilix_risk_v1"

class RiskModel:
    def __init__(self):
        self._sess = None
        self._in_name = None
        self._out_name = None
        try:
            import onnxruntime as ort
            if os.path.exists(MODEL_PATH):
                self._sess = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
                self._in_name = self._sess.get_inputs()[0].name
                self._out_name = self._sess.get_outputs()[0].name
        except Exception:
            self._sess = None

    @property
    def version(self) -> str:
        return MODEL_VERSION

    def predict(self, x: list[float]) -> list[float]:
        # Output: [falls, respiratory, dehydration, delirium_uti] 0..1
        if not self._sess:
            falls = min(1.0, 0.45*x[4] + 0.35*x[5] + 0.30*x[6])
            resp = min(1.0, 0.45*x[1] + 0.35*x[2] + 0.35*x[3])
            dehyd = min(1.0, 0.55*x[7] + 0.25*x[0])
            delir = min(1.0, 0.50*x[8] + 0.30*x[9] + 0.20*x[10])
            return [falls, resp, dehyd, delir]

        arr = np.asarray([x], dtype=np.float32)
        out = self._sess.run([self._out_name], {self._in_name: arr})[0]
        out = np.asarray(out).reshape(-1).tolist()
        return [float(max(0.0, min(1.0, v))) for v in out]
