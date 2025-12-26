from __future__ import annotations

import os
from pathlib import Path

MODEL_PATH = Path(os.environ.get("HAKILIX_MODEL_PATH", "/app/models/hakilix_risk_v1.onnx"))

def build_model(path: Path):
    import numpy as np
    import onnx
    from onnx import helper, TensorProto, numpy_helper

    # Simple MLP: y = sigmoid(x @ W + b) -> 4 outputs
    W = np.array([
        # falls
        [0.0, 0.0, 0.0, 0.0,  1.8, 1.4, 1.2, 0.0, 0.0, 0.0, 0.0],
        # respiratory
        [0.0, 1.6, 1.2, 1.1,  0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        # dehydration
        [0.7, 0.0, 0.0, 0.0,  0.0, 0.0, 0.0, 1.7, 0.0, 0.0, 0.0],
        # delirium/uti
        [0.0, 0.0, 0.0, 0.0,  0.0, 0.0, 0.0, 0.0, 1.5, 1.0, 0.8],
    ], dtype=np.float32).T  # (11,4)

    b = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)

    inp = helper.make_tensor_value_info("x", TensorProto.FLOAT, ["N", 11])
    out = helper.make_tensor_value_info("y", TensorProto.FLOAT, ["N", 4])

    W_init = numpy_helper.from_array(W, name="W")
    b_init = numpy_helper.from_array(b, name="b")

    mm = helper.make_node("MatMul", ["x", "W"], ["z"])
    add = helper.make_node("Add", ["z", "b"], ["z2"])
    sig = helper.make_node("Sigmoid", ["z2"], ["y"])

    graph = helper.make_graph([mm, add, sig], "hakilix_risk_v1", [inp], [out], [W_init, b_init])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    onnx.checker.check_model(model)

    path.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, str(path))

def main():
    # If file missing or tiny placeholder, generate a valid ONNX file
    try:
        if (not MODEL_PATH.exists()) or MODEL_PATH.stat().st_size < 1024:
            build_model(MODEL_PATH)
            print("Generated ONNX model at", MODEL_PATH)
    except Exception as e:
        print("Model bootstrap failed; inference will run with fallback only:", e)

if __name__ == "__main__":
    main()
