"""Local Whisper transcription of a standard ComfyUI AUDIO selection."""
import json
from pathlib import Path

import folder_paths
from comfy_api.latest import io

DEFAULT_MODEL = 'whisper-large-v3-turbo'


def installed_models():
    """List local Whisper folders without importing/loading Transformers."""
    names = set()
    for root in folder_paths.get_folder_paths('audio_encoders'):
        directory = Path(root)
        if not directory.is_dir():
            continue
        for child in directory.iterdir():
            if not child.is_dir() or not (child / 'model.safetensors').is_file():
                continue
            try:
                config = json.loads((child / 'config.json').read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if config.get('model_type') == 'whisper':
                names.add(child.name)
    return sorted(names) or [DEFAULT_MODEL]


def model_directory(model_name=DEFAULT_MODEL):
    if not model_name or model_name != model_name.rstrip(' .') or Path(model_name).name != model_name or '/' in model_name or '\\' in model_name:
        raise ValueError('Choose a local Whisper model from the model dropdown.')
    roots = folder_paths.get_folder_paths('audio_encoders')
    for root in roots:
        directory = Path(root) / model_name
        if (directory / 'model.safetensors').is_file() and (directory / 'config.json').is_file():
            return directory
    raise FileNotFoundError(f'Local Whisper model not found: models/audio_encoders/{model_name}. This node does not download files during a render.')


class ApexAudioLyrics(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        models = installed_models()
        return io.Schema(
            node_id='ApexAudioLyrics', display_name='Apex Audio Lyrics', category='Apex Artist/Audio',
            description='Transcribe the supplied song selection locally with Whisper. Automatic lyrics are a draft; review unclear lines before using them for a story.',
            inputs=[
                io.Audio.Input('audio', tooltip='The selected song AUDIO. Trim the song upstream with Apex Audio.'),
                io.String.Input('language', display_name='Language', default='auto', tooltip='auto detects the language; enter English, Hindi, a language name or its Whisper code.'),
                io.Combo.Input('device', display_name='Device', options=['auto', 'cpu'], default='auto',
                               tooltip='auto uses ComfyUI\'s processing device. cpu keeps Whisper off the GPU.'),
                # Keep the original three widget positions for older saved workflows.
                io.String.Input('corrected_lyrics', display_name='Corrected lyrics', optional=True, multiline=True, default='',
                                tooltip='Optional reviewed lyrics. Nonempty text overrides transcription and skips loading Whisper.'),
                io.Combo.Input('model_name', display_name='Whisper model', optional=True, options=models, default=DEFAULT_MODEL if DEFAULT_MODEL in models else models[0],
                               tooltip='Installed Whisper folders under models/audio_encoders. No download occurs during execution.'),
                io.Int.Input('beam_size', display_name='Beam size', optional=True, default=5, min=1, max=10, step=1,
                             tooltip='1 is fastest. Larger values compare more candidate transcriptions and take longer; default 5.'),
                io.Boolean.Input('condition_on_previous_text', display_name='Previous segment text', optional=True, default=False,
                                 tooltip='Use preceding transcription as context for the next long-audio segment. Off reduces repetition or carryover; default off.'),
                io.String.Input('initial_prompt', display_name='Vocabulary hint', optional=True, default='', multiline=False,
                                tooltip='Optional names or unusual vocabulary to help recognition. This is a hint, not replacement lyrics.'),
            ],
            outputs=[io.String.Output(display_name='lyrics', tooltip='Editable draft transcription for downstream text or C-roll planning.'),
                     io.String.Output(display_name='segments_json', tooltip='Approximate segment times in seconds relative to the supplied AUDIO selection.')],
        )

    @classmethod
    def execute(cls, audio, language='auto', device='auto', corrected_lyrics='', model_name=DEFAULT_MODEL,
                beam_size=5, condition_on_previous_text=False, initial_prompt=''):
        if corrected_lyrics.strip():
            return io.NodeOutput(corrected_lyrics.strip(), json.dumps({'source':'user_corrected','segments':[]}))
        import torch
        import comfy.audio
        import comfy.model_management as mm
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

        if device not in ('auto', 'cpu'):
            raise ValueError('Device must be auto or cpu.')
        if isinstance(beam_size, bool) or not isinstance(beam_size, int) or beam_size < 1:
            raise ValueError('Beam size must be a positive integer.')
        waveform = audio['waveform']
        if waveform.ndim != 3 or waveform.shape[0] != 1 or waveform.shape[-1] == 0:
            raise ValueError('Apex Audio Lyrics expects one nonempty AUDIO selection.')
        rate = int(audio['sample_rate'])
        if rate <= 0:
            raise ValueError('Invalid audio sample rate.')
        mono = waveform[0].detach().float().cpu().mean(dim=0,keepdim=True)
        if rate != 16000:
            mono = comfy.audio.resample(mono,rate,16000)
        samples = mono.squeeze(0).contiguous().numpy()
        duration = len(samples)/16000
        target = torch.device('cpu') if device=='cpu' else mm.get_torch_device()
        dtype = torch.float16 if target.type=='cuda' else torch.float32
        directory = model_directory(model_name)
        model = None
        try:
            # Ask ComfyUI for only the memory this short-lived model needs.
            # It is offloaded again before the video samplers execute.
            if target.type!='cpu':
                mm.free_memory(3*1024**3,target)
            processor = AutoProcessor.from_pretrained(directory,local_files_only=True)
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                directory,dtype=dtype,low_cpu_mem_usage=True,use_safetensors=True,
                local_files_only=True,attn_implementation='sdpa')
            model.to(target).eval()
            transcriber = pipeline('automatic-speech-recognition',model=model,
                tokenizer=processor.tokenizer,feature_extractor=processor.feature_extractor,
                dtype=dtype,device=target)
            options={'task':'transcribe','num_beams':beam_size,'do_sample':False,
                     'condition_on_prev_tokens':bool(condition_on_previous_text)}
            if language.strip().lower() not in ('','auto'):
                options['language']=language.strip().lower()
            if initial_prompt.strip():
                options['prompt_ids']=processor.get_prompt_ids(initial_prompt.strip(),return_tensors='pt').to(target)
            result = transcriber({'raw':samples,'sampling_rate':16000},
                batch_size=1,return_timestamps=True,generate_kwargs=options)
            text=result.get('text','').strip()
            segments=[]
            for chunk in result.get('chunks',[]):
                start,end=chunk.get('timestamp',(None,None))
                segments.append({'start':None if start is None else max(0,min(duration,float(start))),
                    'end':None if end is None else max(0,min(duration,float(end))),
                    'text':chunk.get('text','').strip()})
            document={'source':'local_whisper','model':model_name,
                'duration_seconds':duration,'language':language,'draft':True,'segments':segments,
                'settings':{'beam_size':beam_size,'condition_on_previous_text':bool(condition_on_previous_text),
                            'initial_prompt':initial_prompt.strip(),'device':str(target)}}
            return io.NodeOutput(text,json.dumps(document,ensure_ascii=False,indent=2))
        finally:
            if model is not None:
                model.to('cpu')
