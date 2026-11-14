"""Read-only adapter for a previously frozen V3 detector; no OCR/GT coupling."""
import hashlib
import json
from pathlib import Path
import torch
from train_detector_v3 import specification


class SymbolReader:
    def __init__(self, run, name='tiny'):
        run = Path(run)
        frozen = json.loads((run/'evaluation/frozen_thresholds.json').read_text())
        path = run/name/'best.pt'
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        if self.sha256 != frozen['checkpoints'][name]:
            raise ValueError('Detector checksum mismatch')
        lineage = hashlib.sha256((run/'data_protocol.json').read_bytes()).hexdigest()
        if lineage != frozen['data_protocol_sha256']:
            raise ValueError('Detector lineage mismatch')
        checkpoint = torch.load(path, map_location='cpu', weights_only=True)
        spec = specification(name)
        if (checkpoint['architecture'] != spec[7] or checkpoint['input_size'] != list(spec[1:3])
                or checkpoint['data_protocol_sha256'] != lineage):
            raise ValueError('Detector architecture / lineage mismatch')
        torch.set_num_threads(2)
        self.model = spec[0]()
        self.model.load_state_dict(checkpoint['model_state'])
        self.model.eval()
        self.tensor, self.decode = spec[6], spec[5]
        self.threshold = frozen['thresholds'][name]
        self.metadata = dict(model=name, architecture=spec[7], checkpoint_sha256=self.sha256,
                             threshold=self.threshold, retrained_on='V2 train only; V2 val threshold')

    def read(self, image):
        with torch.inference_mode():
            return self.decode(self.model(self.tensor(image)[None]), [image.size], self.threshold)[0]
