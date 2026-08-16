"""
编译链 —— DNA 的万能翻译层
DNA 为万能语言，可翻译为所有语言（编译链双向的）。
DNA 有固定坐标且多模态所以可以翻译为所有语言。
"""
from typing import Any
from .dna import DNA, DNAType, StrandType
from .magnetic import MagneticEngine
from .smart_tagger import SmartTagger


class CompileChain:
    """
    编译链 —— 双向翻译
    入向：任意输入 → DNA 格式
    出向：DNA → 任意目标格式
    """

    def __init__(self, magnetic: MagneticEngine):
        self.magnetic = magnetic
        self.tagger = SmartTagger()

    def compile(self, raw_data: Any, source: str = "", tags: list[str] = None) -> DNA:
        """入向编译：把任意输入翻译成DNA"""
        # 判断输入类型并提取
        if isinstance(raw_data, str):
            return self._compile_text(raw_data, source, tags)
        elif isinstance(raw_data, dict):
            return self._compile_dict(raw_data, source, tags)
        elif isinstance(raw_data, list):
            return self._compile_list(raw_data, source, tags)
        else:
            return self._compile_text(str(raw_data), source, tags)

    def decompile(self, dna: DNA, target_format: str = "text") -> str:
        """出向编译：把DNA翻译为目标格式"""
        dna.access()
        if target_format == "text":
            return self._to_text(dna)
        elif target_format == "summary":
            return self._to_summary(dna)
        elif target_format == "code":
            return self._to_code(dna)
        return self._to_text(dna)

    def compile_file(self, filepath: str) -> list[DNA]:
        """编译文件：读取文件内容翻译为多个DNA"""
        import pandas as pd
        from pathlib import Path

        path = Path(filepath)
        if not path.exists():
            return []

        dnas = []
        filename = path.name

        # Excel 文件
        if path.suffix in ('.xlsx', '.xls', '.xlsm'):
            try:
                xl = pd.ExcelFile(filepath)
                for sheet in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=sheet)
                    # 每一行作为一个DNA
                    for idx, row in df.iterrows():
                        content = row.dropna().to_dict()
                        if content:
                            dna = self.compile(
                                content,
                                source=f"{filename}::{sheet}",
                                tags=[filename, sheet, str(idx)]
                            )
                            dnas.append(dna)
            except Exception as e:
                dna = self.compile(
                    {"error": str(e), "file": filename},
                    source=filename,
                    tags=[filename, "error"]
                )
                dnas.append(dna)

        # 图片文件 —— OCR 提取文字
        elif path.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'):
            try:
                dnas = self._compile_image(filepath, filename)
            except Exception as e:
                dnas.append(self.compile(
                    {"error": str(e), "file": filename, "type": "image"},
                    source=filename,
                    tags=[filename, "image", "ocr_error"]
                ))

        # 音频文件 —— 语音转文字
        elif path.suffix.lower() in ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma'):
            try:
                dnas = self._compile_audio(filepath, filename)
            except Exception as e:
                dnas.append(self.compile(
                    {"error": str(e), "file": filename, "type": "audio"},
                    source=filename,
                    tags=[filename, "audio", "asr_error"]
                ))

        # 视频文件 —— 提取音频转文字 + 关键帧OCR
        elif path.suffix.lower() in ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'):
            try:
                dnas = self._compile_video(filepath, filename)
            except Exception as e:
                dnas.append(self.compile(
                    {"error": str(e), "file": filename, "type": "video"},
                    source=filename,
                    tags=[filename, "video", "extract_error"]
                ))

        # 文本文件
        elif path.suffix in ('.txt', '.md', '.json', '.csv', '.tex', '.py', '.cff', '.yml', '.yaml', '.html', '.htm', '.js', '.css'):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 先创建全文汇总DNA
            dnas.append(self.compile(
                {"full_text": content, "source_file": filename, "char_count": len(content)},
                source=filename,
                tags=[filename, "全文", "full_text"]
            ))

            # 按段落拆分：空行分隔优先
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            if len(paragraphs) < 3:
                paragraphs = [l.strip() for l in content.split('\n') if l.strip()]

            for i, para in enumerate(paragraphs):
                if len(para) > 20:  # 跳过太短的片段
                    dna = self.compile(
                        para,
                        source=filename,
                        tags=[filename, f"para_{i}"]
                    )
                    dnas.append(dna)

        return dnas

    def _compile_text(self, text: str, source: str, tags: list[str] = None) -> DNA:
        vec = self.magnetic.generate_vector(text)
        # 使用智能标签
        smart_tags = self.tagger.extract_tags(text, tags)
        return DNA(
            dna_type=DNAType.DATA,
            strand=StrandType.FORWARD,
            content={"text": text},
            magnetic_vector=vec,
            source=source,
            tags=smart_tags,
            modality="text"
        )

    def _compile_dict(self, data: dict, source: str, tags: list[str] = None) -> DNA:
        # 字典类型用所有值的拼接生成向量
        text_repr = " ".join(str(v) for v in data.values())
        vec = self.magnetic.generate_vector(text_repr)
        # 使用智能标签
        smart_tags = self.tagger.extract_tags(text_repr, tags)
        return DNA(
            dna_type=DNAType.DATA,
            strand=StrandType.FORWARD,
            content=data,
            magnetic_vector=vec,
            source=source,
            tags=smart_tags,
            modality="text"
        )

    def _compile_list(self, data: list, source: str, tags: list[str] = None) -> DNA:
        text_repr = " ".join(str(v) for v in data)
        vec = self.magnetic.generate_vector(text_repr)
        return DNA(
            dna_type=DNAType.DATA,
            strand=StrandType.FORWARD,
            content={"list": data},
            magnetic_vector=vec,
            source=source,
            tags=tags or [],
            modality="text"
        )

    def _compile_image(self, filepath: str, filename: str) -> list[DNA]:
        """OCR 编译图片为 DNA"""
        import numpy as np
        from PIL import Image

        # 用 PIL 加载图片（避免中文路径问题），再转 numpy 给 EasyOCR
        img = Image.open(filepath)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img_array = np.array(img)

        import easyocr
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
        results = reader.readtext(img_array)

        if not results:
            return []

        all_text = " ".join(text for _, text, _ in results)
        lines = [t for _, t, _ in results if t.strip()]

        dnas = []
        # 创建一条汇总DNA（整图文字）
        dnas.append(self.compile(
            {"image_text": all_text, "source_image": filename},
            source=filename,
            tags=[filename, "image_ocr", "full"]
        ))
        # 每条识别文本创建一条DNA
        for i, line in enumerate(lines):
            dnas.append(self.compile(
                line,
                source=filename,
                tags=[filename, "image_ocr", f"line_{i}"]
            ))

        return dnas

    def _compile_audio(self, filepath: str, filename: str) -> list[DNA]:
        """语音转文字编译音频为 DNA"""
        from faster_whisper import WhisperModel

        print(f"  [音频转录] {filename} ...")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(filepath, language="zh")

        dnas = []
        all_text_parts = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                all_text_parts.append(text)
                dnas.append(self.compile(
                    text,
                    source=filename,
                    tags=[filename, "audio_transcript", f"t{seg.start:.0f}s"]
                ))

        # 汇总DNA
        if all_text_parts:
            full_text = " ".join(all_text_parts)
            dnas.insert(0, self.compile(
                {"audio_transcript": full_text, "source_file": filename,
                 "duration_s": info.duration, "language": info.language},
                source=filename,
                tags=[filename, "audio_transcript", "full"]
            ))

        print(f"  [音频转录] 完成, {len(dnas)} 条DNA")
        return dnas

    def _compile_video(self, filepath: str, filename: str) -> list[DNA]:
        """视频编译：提取音频转文字"""
        import av
        import tempfile
        import numpy as np
        from PIL import Image

        dnas = []

        # 1. 提取音频并转文字
        try:
            container = av.open(filepath)
            audio_stream = container.streams.audio[0] if container.streams.audio else None
            if audio_stream:
                print(f"  [视频音频提取] {filename} ...")
                # 导出音频到临时文件
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    tmp_path = tmp.name

                # 用 av 提取音频
                out_container = av.open(tmp_path, 'w')
                out_stream = out_container.add_stream('pcm_s16le', rate=audio_stream.rate)
                out_stream.channels = audio_stream.channels

                for frame in container.decode(audio_stream):
                    for packet in out_stream.encode(frame):
                        out_container.mux(packet)
                for packet in out_stream.encode(None):
                    out_container.mux(packet)
                out_container.close()
                container.close()

                # 转录音频
                audio_dnas = self._compile_audio(tmp_path, f"{filename}[音频]")
                dnas.extend(audio_dnas)
                import os
                os.unlink(tmp_path)
            else:
                container.close()
        except Exception as e:
            dnas.append(self.compile(
                {"error": f"音频提取失败: {e}", "file": filename},
                source=filename,
                tags=[filename, "video", "audio_extract_error"]
            ))

        # 2. 提取关键帧做 OCR
        try:
            container = av.open(filepath)
            video_stream = container.streams.video[0] if container.streams.video else None
            if video_stream:
                print(f"  [视频关键帧] {filename} ...")
                duration = float(video_stream.duration * video_stream.time_base) if video_stream.duration else 60
                # 每10%取一帧
                frame_count = 0
                for i in range(10):
                    t = duration * (i + 1) / 11
                    container.seek(int(t * 1000000))
                    for frame in container.decode(video_stream):
                        img = frame.to_image()
                        # OCR 这一帧
                        img_array = np.array(img.convert('RGB'))
                        try:
                            import easyocr
                            reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
                            results = reader.readtext(img_array)
                            frame_text = " ".join(t for _, t, _ in results)
                            if frame_text.strip():
                                dnas.append(self.compile(
                                    {"frame_text": frame_text, "time_s": t, "source_video": filename},
                                    source=filename,
                                    tags=[filename, "video_frame", f"t{t:.0f}s"]
                                ))
                                frame_count += 1
                        except Exception:
                            pass
                        break  # 只取第一帧
                container.close()
                if frame_count > 0:
                    print(f"  [视频关键帧] {frame_count} 帧识别出文字")
        except Exception:
            pass

        return dnas

    def _to_text(self, dna: DNA) -> str:
        return str(dna.content)

    def _to_summary(self, dna: DNA) -> str:
        c = dna.content
        lines = [f"[DNA:{dna.id[:8]}] type={dna.dna_type.value} life={dna.lifetime:.0f}"]
        for k, v in c.items():
            lines.append(f"  {k}: {str(v)[:200]}")
        return '\n'.join(lines)

    def _to_code(self, dna: DNA) -> str:
        return repr(dna.content)
