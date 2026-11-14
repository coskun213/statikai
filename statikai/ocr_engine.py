"""Independent, optional local OCR. Input is image pixels, never annotations."""
import hashlib
from importlib.metadata import version
from pathlib import Path
import numpy as np


class LocalOCR:
    def __init__(self, model_dir):
        try:
            from rapidocr import RapidOCR, OCRVersion, ModelType
        except ImportError as exc:
            raise RuntimeError('Install requirements-ocr.txt to enable local OCR') from exc
        self.model_dir = Path(model_dir).resolve()
        self.params = {
            'Global.model_root_dir': str(self.model_dir),
            'Global.log_level': 'warning', 'Global.use_cls': False,
            # Keep rejected low confidence text in the audit output as well.
            'Global.text_score': 0.0,
            'Det.ocr_version': OCRVersion.PPOCRV6, 'Det.model_type': ModelType.SMALL,
            'Rec.ocr_version': OCRVersion.PPOCRV6, 'Rec.model_type': ModelType.SMALL,
            'EngineConfig.onnxruntime.intra_op_num_threads': 2,
            'EngineConfig.onnxruntime.inter_op_num_threads': 1,
            'EngineConfig.onnxruntime.use_cuda': False,
        }
        self.engine = RapidOCR(params=self.params)

    def read(self, image):
        # Pass RGB PIL images as BGR arrays, not filenames or sidecar metadata.
        rgb = np.asarray(image.convert('RGB'))
        result = self.engine(rgb[:, :, ::-1].copy())
        if result.boxes is None or result.txts is None:
            return []
        output = []
        for quad, text, score in zip(result.boxes, result.txts, result.scores):
            q = np.asarray(quad, dtype=float)
            output.append(dict(raw_text=text, confidence=float(score), quad=q.tolist(),
                               bbox=[float(q[:, 0].min()), float(q[:, 1].min()),
                                     float(q[:, 0].max()), float(q[:, 1].max())]))
        return output

    def metadata(self):
        return dict(backend='RapidOCR / ONNX Runtime CPU', pretrained=True,
                    rapidocr_version=version('rapidocr'),
                    onnxruntime_version=version('onnxruntime'),
                    parameters={k: getattr(v, 'value', v) for k, v in self.params.items()},
                    confidence_note='recognizer score, not a calibrated probability',
                    models={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(self.model_dir.glob('*.onnx'))})
