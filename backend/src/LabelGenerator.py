import base64
from datetime import datetime
import os

from blabel import LabelWriter


class LabelGenerator:
    def __init__(self, template_path, stylesheets, title='Title', text='text'):
        self.label_writer = LabelWriter(template_path, default_stylesheets=(stylesheets,))
        self.title = title
        self.text = text
        os.makedirs(os.path.join("results", "labels"), exist_ok=True)

    def generate_label(self, group_code, seq) -> str:
        current_day = datetime.today().strftime('%d%m%Y')
        filename = f"{seq:04d}_{current_day}.pdf"
        filename = os.path.join("results","labels", filename)
        records = [
            dict(code=base64.b64decode(group_code).decode('utf-8'), code_text=base64.b64decode(group_code).decode('utf-8'), seq=str(seq), title=self.title, text=self.text)
        ]
        self.label_writer.write_labels(records, target=filename)
        return filename